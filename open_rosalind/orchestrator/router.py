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


SEQUENCE_RE = re.compile(r"^[ACGTUNacgtun\s]{20,}$")
PROTEIN_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWYBXZacdefghiklmnpqrstvwybxz\s\*]{20,}$")
ACCESSION_RE = re.compile(r"\b([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})\b")
LIT_RE = re.compile(r"\b(paper|papers|literature|pubmed|cite|citation|publication|publications|review|reviews|studies|study|research|article|articles)\b", re.I)
HGVS_RE = re.compile(r"\b(?:p\.)?([A-Z])(\d+)([A-Z\*])\b")
# 3-letter HGVS like p.Phe508del, p.Gly12Asp, p.Val600Glu, p.Glu6Val
HGVS_3LETTER_RE = re.compile(r"\b(?:p\.)?(Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val)(\d+)(Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|del|Ter|\*)?\b", re.I)
# Compact mutation notation that often appears bare in natural language: e.g. G12D, V600E, R175H, ΔF508 / dF508 / F508del
COMPACT_MUT_RE = re.compile(r"\b([A-Z])(\d{1,4})([A-Z\*])\b")
DELTA_DEL_RE = re.compile(r"(?:Δ|delta\s*|d|del\s*)([A-Z])(\d{1,4})\b|\b([A-Z])(\d{1,4})del\b", re.I)
MUT_KEYWORDS = re.compile(r"\b(mutation|mutant|variant|substitution|polymorphism|allele)\b", re.I)
WT_MT_BLOCK_RE = re.compile(
    r"(?ims)(?:^|[\s])(?:wt|wild[\-\s]*type)\s*[:=]\s*([A-Za-z\*\-\s]+?)\s+(?:mt|mut(?:ant)?)\s*[:=]\s*(.+?)\s*$"
)
# A gene/protein symbol heuristic: 2–8 uppercase alnum, not a stopword
GENE_SYMBOL_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,7})\b")


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

    # Embedded long sequence (even if surrounded by prose): "Characterize this protein: MKRIS..."
    # Extract any continuous letter-string ≥20 chars that looks like DNA/RNA/protein.
    embedded_seq = _extract_embedded_sequence(stripped)
    if embedded_seq:
        return Intent(skill="sequence_basic_analysis", payload={"sequence": embedded_seq})

    compact = re.sub(r"\s+", "", stripped)
    if len(compact) >= 40 and (SEQUENCE_RE.match(stripped) or PROTEIN_RE.match(stripped)):
        return Intent(skill="sequence_basic_analysis", payload={"sequence": stripped})

    m = ACCESSION_RE.search(stripped)
    if m and len(stripped) < 200:
        return Intent(
            skill="uniprot_lookup",
            payload={"query": stripped, "accession": m.group(1)},
        )

    # Natural-language mutation query: "Effect of KRAS G12D", "CFTR ΔF508",
    # "p.L858R in EGFR", etc. Route to mutation_effect with a gene_symbol +
    # mutation pair; the skill will fetch the WT sequence from UniProt.
    mut_match = _detect_nl_mutation(stripped)
    if mut_match and MUT_KEYWORDS.search(stripped.lower() + " mutation"):
        gene, mutation = mut_match
        return Intent(
            skill="mutation_effect",
            payload={"gene_symbol": gene, "mutation": mutation, "query": stripped},
        )

    if LIT_RE.search(stripped):
        return Intent(skill="literature_search", payload={"query": stripped})

    return Intent(skill="uniprot_lookup", payload={"query": stripped})


# ---------------------------------------------------------------------------
# NL mutation detection helpers
# ---------------------------------------------------------------------------
_AA3TO1 = {
    "ala": "A", "arg": "R", "asn": "N", "asp": "D", "cys": "C",
    "gln": "Q", "glu": "E", "gly": "G", "his": "H", "ile": "I",
    "leu": "L", "lys": "K", "met": "M", "phe": "F", "pro": "P",
    "ser": "S", "thr": "T", "trp": "W", "tyr": "Y", "val": "V",
}


def _detect_nl_mutation(text: str) -> tuple[str, str] | None:
    """Extract (gene_symbol, mutation_str) from natural-language mutation queries.

    Handles: G12D, p.V600E, ΔF508, F508del, p.Glu6Val, p.Phe508del, etc.
    """
    # Priority: 3-letter HGVS, then compact HGVS, then delta-del.
    gene = None
    mutation = None

    m = HGVS_3LETTER_RE.search(text)
    if m:
        ref, pos, alt = m.group(1), m.group(2), m.group(3) or ""
        ref1 = _AA3TO1.get(ref.lower(), ref[0].upper())
        if alt.lower() == "del":
            mutation = f"p.{ref1}{pos}del"
        elif alt and alt.lower() in _AA3TO1:
            alt1 = _AA3TO1[alt.lower()]
            mutation = f"p.{ref1}{pos}{alt1}"
        elif alt in ("*", "Ter"):
            mutation = f"p.{ref1}{pos}*"
    if not mutation:
        m = COMPACT_MUT_RE.search(text)
        if m:
            mutation = f"p.{m.group(1)}{m.group(2)}{m.group(3)}"
    if not mutation:
        m = DELTA_DEL_RE.search(text)
        if m:
            ref = m.group(1) or m.group(3)
            pos = m.group(2) or m.group(4)
            if ref and pos:
                mutation = f"p.{ref.upper()}{pos}del"

    if not mutation:
        return None

    # Extract gene symbol: first uppercase token that is not a stop-word
    # and not the mutation itself.
    for tok in GENE_SYMBOL_RE.findall(text):
        if tok.lower() in _NL_MUT_STOPWORDS:
            continue
        # Skip tokens that look like a mutation chunk (e.g. V600, G12)
        if re.fullmatch(r"[A-Z]\d+", tok):
            continue
        if mutation and tok in mutation:
            continue
        gene = tok
        break

    if gene and mutation:
        return gene, mutation
    return None


_NL_MUT_STOPWORDS = {"WT", "MT", "DNA", "RNA", "HGVS", "MUT", "AA", "NT",
                     "THE", "THIS", "THAT", "HOW", "WHAT", "EFFECT"}


def _parse_two_fasta(text: str) -> dict:
    blocks = re.split(r"\n(?=>)", text.strip())
    seqs = []
    for b in blocks[:2]:
        lines = b.splitlines()
        body = "".join(lines[1:]) if lines[0].startswith(">") else "".join(lines)
        seqs.append(re.sub(r"\s+", "", body))
    return {"wild_type": seqs[0], "mutant": seqs[1]}


def _extract_embedded_sequence(text: str) -> str | None:
    """Extract a biological sequence embedded in prose.

    Looks for continuous letter-strings ≥20 chars that match DNA/RNA/protein patterns.
    Returns the longest match, or None.
    """
    # Find all continuous letter-only strings (no spaces, no punctuation)
    candidates = re.findall(r"[A-Za-z]{20,}", text)
    best = None
    best_len = 0
    for c in candidates:
        # Check if it looks like a sequence (not prose)
        if SEQUENCE_RE.match(c) or PROTEIN_RE.match(c):
            if len(c) > best_len:
                best = c
                best_len = len(c)
    return best
