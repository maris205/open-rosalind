"""LLM-assisted intent classifier.

The rule-based router (`router.py`) handles unambiguous cases — pure FASTA,
WT/MT blocks, bare UniProt accessions. It struggles when an English question
embeds a short sequence or a UniProt ID, e.g.::

    "Translate this DNA: ATGGCCAAATTAA"
    "How long is human insulin (P01308)?"
    "Compare wild-type GFP to the S65T mutant ..."

In those cases we hand the prompt to the LLM with a tiny constrained
classification schema and let it tell us which skill + payload to dispatch.

The classifier is best-effort: any backend error or schema violation falls
back to the rule-based router, so the agent never depends on the LLM being
healthy. The classifier never invents tools — it can only choose one of the
four registered skills.
"""
from __future__ import annotations

import json
import re
from typing import Any

from ..backends import Backend
from .router import Intent

CLASSIFY_SYSTEM = """You are an intent classifier for a bioinformatics agent.

Pick exactly one skill for the user's input from this fixed list:
- sequence_basic_analysis : compute basic stats on a DNA / RNA / protein
  sequence (length, GC content, translation, reverse complement, MW).
- uniprot_lookup          : look up a protein by UniProt accession or by a
  gene/protein name question.
- literature_search       : retrieve PubMed papers for a topic / question.
- mutation_effect         : analyze a wild-type vs mutant sequence pair, or
  apply an HGVS point mutation (e.g. p.R175H) to a wild-type sequence.

Return STRICT JSON only — no prose, no Markdown fences. Schema:

  {"skill": "<one of the four>", "payload": {...}}

Payload shape per skill:
  - sequence_basic_analysis: {"sequence": "<raw DNA/protein, no header lines>"}
  - uniprot_lookup:          {"query": "<keywords>", "accession": "<optional UniProt id>"}
  - literature_search:       {"query": "<keywords>"}
  - mutation_effect:         {"wild_type": "<seq>", "mutation": "<p.X#Y>"}
                          OR {"wild_type": "<seq>", "mutant": "<seq>"}

If the user's question contains an embedded raw sequence, EXTRACT just the
residue letters (no commentary, no header) into the payload field. If the
user asks for translation/GC/length/reverse-complement of a given sequence,
that is sequence_basic_analysis. If they ask "what is X" / "function of X",
that is uniprot_lookup.

Output only the JSON object."""


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_SEQUENCE_CHAR_RE = re.compile(r"\b[ACGTUacgtu]{8,}\b|\b[ACDEFGHIKLMNPQRSTVWY]{15,}\b")
_ENGLISH_TOKEN_RE = re.compile(r"\b[a-zA-Z]{2,}\b")
_ENGLISH_STOPWORDS = {
    "what", "which", "who", "where", "when", "how", "why", "is", "are",
    "the", "a", "an", "this", "that", "these", "those", "of", "to", "for",
    "in", "on", "at", "by", "with", "from", "about", "and", "or", "but",
    "find", "show", "list", "tell", "explain", "translate", "compare",
    "analyze", "look", "lookup", "search", "give", "me", "please",
    "can", "do", "does", "did", "should", "would", "could", "may",
    "long", "length", "function", "role", "located", "located",
}
_VALID_SKILLS = {
    "sequence_basic_analysis", "uniprot_lookup",
    "literature_search", "mutation_effect",
}


def has_embedded_sequence(text: str) -> bool:
    """Look for a sequence-shaped run that is NOT the entire input."""
    return bool(_SEQUENCE_CHAR_RE.search(text))


def looks_like_natural_language(text: str) -> bool:
    """≥2 English stopwords / question-words within the first ~100 chars."""
    head = text[:200].lower()
    tokens = _ENGLISH_TOKEN_RE.findall(head)
    n_stop = sum(1 for t in tokens if t in _ENGLISH_STOPWORDS)
    return n_stop >= 2


def needs_llm_classification(text: str) -> bool:
    """Triggers the LLM classifier path when rule-based routing is likely
    to mis-classify: an English question that embeds a sequence/ID."""
    if has_embedded_sequence(text) and looks_like_natural_language(text):
        return True
    return False


def llm_classify(text: str, backend: Backend) -> Intent | None:
    """Best-effort LLM intent classification. Returns None on any failure."""
    try:
        resp = backend.chat(
            [
                {"role": "system", "content": CLASSIFY_SYSTEM},
                {"role": "user", "content": f"USER INPUT:\n{text}"},
            ],
            temperature=0.0,
            max_tokens=400,
        )
        content = (resp.content or "").strip()
        if not content:
            return None
        m = _JSON_RE.search(content)
        if not m:
            return None
        obj = json.loads(m.group(0))
        skill = obj.get("skill")
        payload = obj.get("payload") or {}
        if skill not in _VALID_SKILLS or not isinstance(payload, dict):
            return None
        if not _payload_is_valid(skill, payload):
            return None
        return Intent(skill=skill, payload=payload)
    except (json.JSONDecodeError, ValueError, AttributeError, KeyError):
        return None
    except Exception:
        return None


def _payload_is_valid(skill: str, payload: dict) -> bool:
    if skill == "sequence_basic_analysis":
        seq = payload.get("sequence")
        return isinstance(seq, str) and len(re.sub(r"\s+", "", seq)) >= 3
    if skill == "uniprot_lookup":
        return bool(payload.get("query") or payload.get("accession"))
    if skill == "literature_search":
        return bool(payload.get("query"))
    if skill == "mutation_effect":
        if not payload.get("wild_type"):
            return False
        return bool(payload.get("mutation") or payload.get("mutant"))
    return False
