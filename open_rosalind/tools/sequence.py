"""Local sequence statistics — no network required."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from Bio.Align import PairwiseAligner

from .base import ToolSpec

DNA_ALPHABET = set("ACGTN")
PROTEIN_ALPHABET = set("ACDEFGHIKLMNPQRSTVWY")


def _parse_fasta(text: str) -> list[tuple[str, str]]:
    records = []
    header, buf = None, []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(buf)))
            rest = line[1:].strip() or "seq"
            # Some clients (e.g. an HTML <option> in a <select>) collapse a
            # multi-line FASTA into a single line. Split the first whitespace
            # so "demo MVKV..." → header="demo", sequence="MVKV...".
            parts = rest.split(None, 1)
            header = parts[0] if parts else "seq"
            buf = [parts[1]] if len(parts) > 1 else []
        else:
            buf.append(line)
    if header is not None:
        records.append((header, "".join(buf)))
    if not records:
        records = [("seq", re.sub(r"\s+", "", text).upper())]
    return [(h, re.sub(r"\s+", "", s).upper()) for h, s in records]


def _classify(seq: str) -> str:
    if not seq:
        return "unknown"
    chars = set(seq)
    if chars <= DNA_ALPHABET | {"U"}:
        return "dna" if "U" not in chars else "rna"
    if chars <= PROTEIN_ALPHABET | {"X", "B", "Z", "*"}:
        return "protein"
    return "unknown"


def _gc(seq: str) -> float:
    s = seq.upper()
    n = len(s)
    if n == 0:
        return 0.0
    gc = sum(1 for c in s if c in "GC")
    return round(100 * gc / n, 2)


_COMPLEMENT = str.maketrans("ACGTUNacgtun", "TGCAANtgcaan")
_CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


def _reverse_complement(seq: str) -> str:
    return seq.translate(_COMPLEMENT)[::-1]


def _translate(seq: str) -> str:
    s = seq.upper().replace("U", "T")
    out = []
    for i in range(0, len(s) - 2, 3):
        out.append(_CODON_TABLE.get(s[i : i + 3], "X"))
    return "".join(out)


def analyze(sequence: str) -> dict[str, Any]:
    """Compute basic stats for one or more sequences (FASTA or raw)."""
    records = _parse_fasta(sequence)
    out = []
    for header, seq in records:
        kind = _classify(seq)
        rec = {
            "header": header,
            "length": len(seq),
            "type": kind,
            "composition": dict(Counter(seq).most_common(8)),
        }
        if kind in {"dna", "rna"}:
            rec["gc_percent"] = _gc(seq)
            rec["reverse_complement_preview"] = _reverse_complement(seq)[:60]
            translated = _translate(seq)
            rec["translation_preview"] = translated[:60]
            rec["translation_length"] = len(translated)
        if kind == "protein":
            rec["approx_molecular_weight_da"] = _approx_mw(seq)
        out.append(rec)
    return {"records": out, "total_records": len(out)}


_AA_MW = {
    "A": 89.09, "R": 174.20, "N": 132.12, "D": 133.10, "C": 121.16,
    "E": 147.13, "Q": 146.15, "G": 75.07, "H": 155.16, "I": 131.17,
    "L": 131.17, "K": 146.19, "M": 149.21, "F": 165.19, "P": 115.13,
    "S": 105.09, "T": 119.12, "W": 204.23, "Y": 181.19, "V": 117.15,
}


def _approx_mw(seq: str) -> float:
    total = sum(_AA_MW.get(a, 110.0) for a in seq) - 18.015 * max(len(seq) - 1, 0)
    return round(total, 2)


def align_pairwise(
    sequence_a: str,
    sequence_b: str,
    mode: str = "global",
    match_score: float = 1.0,
    mismatch_score: float = 0.0,
    open_gap_score: float = -1.0,
    extend_gap_score: float = -0.5,
) -> dict[str, Any]:
    """Align two sequences using BioPython's PairwiseAligner."""
    records_a = _parse_fasta(sequence_a)
    records_b = _parse_fasta(sequence_b)
    if not records_a or not records_b:
        return {"score": 0.0, "mode": mode, "alignment": None, "identity": 0.0}

    header_a, seq_a = records_a[0]
    header_b, seq_b = records_b[0]

    aligner = PairwiseAligner()
    aligner.mode = mode
    aligner.match_score = match_score
    aligner.mismatch_score = mismatch_score
    aligner.open_gap_score = open_gap_score
    aligner.extend_gap_score = extend_gap_score

    alignment = aligner.align(seq_a, seq_b)[0]
    formatted = str(alignment)
    lines = formatted.rstrip().splitlines()
    aligned_a = lines[0].split()[2] if len(lines) >= 1 and len(lines[0].split()) >= 3 else seq_a
    match_line = lines[1].split()[1] if len(lines) >= 2 and len(lines[1].split()) >= 2 else ""
    aligned_b = lines[2].split()[2] if len(lines) >= 3 and len(lines[2].split()) >= 3 else seq_b

    match_count = sum(1 for c in match_line if c == "|")
    comparable = max(len(match_line), 1)
    identity = round(match_count / comparable, 4)

    return {
        "mode": mode,
        "score": float(alignment.score),
        "sequence_a": {"header": header_a, "length": len(seq_a), "type": _classify(seq_a)},
        "sequence_b": {"header": header_b, "length": len(seq_b), "type": _classify(seq_b)},
        "alignment": {
            "sequence_a": aligned_a,
            "match_line": match_line,
            "sequence_b": aligned_b,
        },
        "identity": identity,
        "aligned_spans": {
            "sequence_a": alignment.aligned[0].tolist(),
            "sequence_b": alignment.aligned[1].tolist(),
        },
    }


ANALYZE_SPEC = ToolSpec(
    name="sequence.analyze",
    description="Local basic analysis of a biological sequence (FASTA or raw): detects type (DNA/RNA/protein), length, composition, GC% (nucleic acid) or approximate molecular weight (protein).",
    input_schema={
        "type": "object",
        "properties": {"sequence": {"type": "string"}},
        "required": ["sequence"],
    },
    output_schema={"type": "object"},
    handler=analyze,
)


ALIGN_PAIRWISE_SPEC = ToolSpec(
    name="sequence.align_pairwise",
    description="Local pairwise sequence alignment using BioPython PairwiseAligner. Returns score, identity, and a formatted alignment.",
    input_schema={
        "type": "object",
        "properties": {
            "sequence_a": {"type": "string"},
            "sequence_b": {"type": "string"},
            "mode": {"type": "string", "enum": ["global", "local"]},
            "match_score": {"type": "number"},
            "mismatch_score": {"type": "number"},
            "open_gap_score": {"type": "number"},
            "extend_gap_score": {"type": "number"}
        },
        "required": ["sequence_a", "sequence_b"],
    },
    output_schema={"type": "object"},
    handler=align_pairwise,
)
