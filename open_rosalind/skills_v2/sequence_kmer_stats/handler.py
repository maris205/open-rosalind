"""Sequence k-mer statistics handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace, is_error, run_tool
from ..sequence import tools


def handler(payload: dict, trace: Any) -> dict:
    sequence = payload.get("sequence", "").strip()
    k = int(payload.get("k", 3) or 3)
    top_n = int(payload.get("top_n", 10) or 10)

    if not sequence:
        return {
            "annotation": {"kind": "sequence_kmer", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing sequence"],
            "kmer_stats": {"records": [], "n_records": 0, "k": k},
        }

    trace = ensure_trace(trace)
    result = run_tool(
        trace,
        "sequence.kmer_stats",
        tools.kmer_stats,
        sequence=sequence,
        k=k,
        top_n=top_n,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "sequence_kmer", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"k-mer statistics failed: {result['error']['message']}"],
            "kmer_stats": {"records": [], "n_records": 0, "k": k},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "sequence_kmer",
            "n_records": result.get("n_records", 0),
            "k": result.get("k", k),
            "n_distinct_kmers": top_record.get("n_distinct_kmers"),
        },
        "confidence": 0.85,
        "notes": [],
        "kmer_stats": result,
    }
