"""Lightweight rule-based router.

For MVP1 we don't rely on the model's native function-calling (the free Gemma
endpoint is unreliable for that). Instead, we detect intent by simple rules:

- Raw biological sequence (FASTA or long ACGT/AA string) → sequence.analyze
- UniProt accession (e.g. P38398, Q9Y6K9) → uniprot.fetch
- "find papers / literature / pubmed" markers → pubmed.search
- Otherwise → uniprot.search (general protein/gene question)

This is intentionally simple. The agent can later be swapped for a planner
that uses the LLM to choose tools.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


SEQUENCE_RE = re.compile(r"^[ACGTUNacgtun\s]{40,}$")
PROTEIN_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWYBXZacdefghiklmnpqrstvwybxz\s\*]{30,}$")
ACCESSION_RE = re.compile(r"\b([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})\b")
LIT_RE = re.compile(r"\b(paper|papers|literature|pubmed|cite|citation|publication|review)\b", re.I)
HGVS_RE = re.compile(r"\b(?:p\.)?([A-Z])(\d+)([A-Z\*])\b")
MUT_KEYWORDS = re.compile(r"\b(mutation|mutant|variant|substitution)\b", re.I)
WT_MT_BLOCK_RE = re.compile(
    r"(?ims)(?:^|[\s])(?:wt|wild[\-\s]*type)\s*[:=]\s*([A-Za-z\*\-\s]+?)\s+(?:mt|mut(?:ant)?)\s*[:=]\s*(.+?)\s*$"
)


@dataclass
class Intent:
    skill: str
    payload: dict


def detect_intent(text: str) -> Intent:
    stripped = text.strip()

    # Multi-FASTA → 1st = WT, 2nd = mutant
    if stripped.count(">") >= 2 and stripped.startswith(">"):
        return Intent(skill="mutation_effect", payload=_parse_two_fasta(stripped))

    # WT: ...  MT: ...  block (also matches mutation as HGVS string)
    m = WT_MT_BLOCK_RE.search(stripped)
    if m:
        wt = re.sub(r"\s+", "", m.group(1))
        mt_raw = m.group(2).strip()
        if HGVS_RE.fullmatch(mt_raw.replace(" ", "")):
            return Intent(skill="mutation_effect", payload={"wild_type": wt, "mutation": mt_raw})
        mt = re.sub(r"\s+", "", mt_raw)
        return Intent(skill="mutation_effect", payload={"wild_type": wt, "mutant": mt})

    if stripped.startswith(">"):
        return Intent(skill="sequence_basic_analysis", payload={"sequence": stripped})

    compact = re.sub(r"\s+", "", stripped)
    if len(compact) >= 40 and (SEQUENCE_RE.match(stripped) or PROTEIN_RE.match(stripped)):
        return Intent(skill="sequence_basic_analysis", payload={"sequence": stripped})

    m = ACCESSION_RE.search(stripped)
    if m and len(stripped) < 200:
        return Intent(
            skill="uniprot_lookup",
            payload={"query": stripped, "accession": m.group(1)},
        )

    if LIT_RE.search(stripped):
        return Intent(skill="literature_search", payload={"query": stripped})

    return Intent(skill="uniprot_lookup", payload={"query": stripped})


def _parse_two_fasta(text: str) -> dict:
    blocks = re.split(r"\n(?=>)", text.strip())
    seqs = []
    for b in blocks[:2]:
        lines = b.splitlines()
        body = "".join(lines[1:]) if lines[0].startswith(">") else "".join(lines)
        seqs.append(re.sub(r"\s+", "", body))
    return {"wild_type": seqs[0], "mutant": seqs[1]}
