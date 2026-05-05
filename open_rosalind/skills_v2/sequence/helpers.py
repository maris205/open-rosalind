"""Additional sequence skill helpers for MVP4."""
from __future__ import annotations

from collections import Counter
from typing import Any

from ...tools.sequence import (
    _approx_mw,
    _classify,
    _parse_fasta,
    _reverse_complement,
    _translate,
    align_pairwise as _align_pairwise_tool,
)


def detect_type(sequence: str) -> dict[str, Any]:
    records = _parse_fasta(sequence)
    out = []
    for header, seq in records:
        out.append({
            "header": header,
            "type": _classify(seq),
            "length": len(seq),
        })
    return {"records": out, "n_records": len(out)}


def gc_content(sequence: str) -> dict[str, Any]:
    from ...tools.sequence import _gc

    records = _parse_fasta(sequence)
    out = []
    for header, seq in records:
        kind = _classify(seq)
        out.append({
            "header": header,
            "type": kind,
            "length": len(seq),
            "gc_percent": _gc(seq) if kind in {"dna", "rna"} else None,
        })
    return {"records": out, "n_records": len(out)}


def translate(sequence: str) -> dict[str, Any]:
    records = _parse_fasta(sequence)
    out = []
    for header, seq in records:
        kind = _classify(seq)
        out.append({
            "header": header,
            "type": kind,
            "length": len(seq),
            "translation": _translate(seq) if kind in {"dna", "rna"} else None,
        })
    return {"records": out, "n_records": len(out)}


def reverse_complement(sequence: str) -> dict[str, Any]:
    records = _parse_fasta(sequence)
    out = []
    for header, seq in records:
        kind = _classify(seq)
        out.append({
            "header": header,
            "type": kind,
            "length": len(seq),
            "reverse_complement": _reverse_complement(seq) if kind in {"dna", "rna"} else None,
        })
    return {"records": out, "n_records": len(out)}


def kmer_stats(sequence: str, k: int = 3, top_n: int = 10) -> dict[str, Any]:
    records = _parse_fasta(sequence)
    out = []
    for header, seq in records:
        kmers = [seq[i : i + k] for i in range(0, max(len(seq) - k + 1, 0))]
        counts = Counter(kmers)
        out.append({
            "header": header,
            "k": k,
            "n_distinct_kmers": len(counts),
            "top_kmers": counts.most_common(top_n),
        })
    return {"records": out, "n_records": len(out), "k": k}


def protein_basic_stats(sequence: str) -> dict[str, Any]:
    records = _parse_fasta(sequence)
    out = []
    for header, seq in records:
        if _classify(seq) != "protein":
            continue
        comp = Counter(seq)
        out.append({
            "header": header,
            "length": len(seq),
            "approx_molecular_weight_da": _approx_mw(seq),
            "composition": dict(comp.most_common(20)),
        })
    return {"records": out, "n_records": len(out)}


def align_pairwise(sequence_a: str, sequence_b: str, mode: str = "global") -> dict[str, Any]:
    return _align_pairwise_tool(sequence_a=sequence_a, sequence_b=sequence_b, mode=mode)
