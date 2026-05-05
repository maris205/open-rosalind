"""Sequence basic analysis skill handler."""
from __future__ import annotations

from typing import Any

from . import tools as seq_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict, trace: Any) -> dict:
    """
    Analyze DNA/RNA/protein sequences.

    Args:
        payload: {"sequence": str}
        trace: Trace logger

    Returns:
        {
            "annotation": {"kind": "sequence", ...},
            "confidence": float,
            "notes": list[str],
            "sequence_stats": {...},
            "uniprot_hint": {...}
        }
    """
    sequence = payload.get("sequence", "").strip()
    if not sequence:
        return {
            "annotation": {"kind": "sequence"},
            "confidence": 0.0,
            "notes": ["Empty sequence"],
            "sequence_stats": {},
        }

    notes = []
    trace = ensure_trace(trace)

    # 1. Analyze sequence locally
    stats = run_tool(trace, "sequence.analyze", seq_tools.analyze, sequence=sequence)

    if is_error(stats):
        return {
            "annotation": {"kind": "sequence"},
            "confidence": 0.0,
            "notes": [f"Sequence analysis failed: {stats['error']['message']}"],
            "sequence_stats": {},
        }

    if not stats.get("records"):
        return {
            "annotation": {"kind": "sequence"},
            "confidence": 0.0,
            "notes": ["No valid sequence found"],
            "sequence_stats": stats,
        }

    primary = stats["records"][0]

    # 2. Optional UniProt probe (protein ≥25aa)
    uniprot_hint = {}
    if primary["type"] == "protein" and primary["length"] >= 25:
        probe_len = min(30, primary["length"])
        probe = "".join(
            line.strip()
            for line in sequence.splitlines()
            if line.strip() and not line.strip().startswith(">")
        )[:probe_len]

        from ..uniprot import tools as up_tools
        result = run_tool(trace, "uniprot.search", up_tools.search, query=probe, max_results=3)
        if is_error(result):
            notes.append(f"UniProt probe failed: {result['error']['message']}")
        elif result.get("hits"):
            uniprot_hint = {
                "hits": len(result["hits"]),
                "top_match": result["hits"][0].get("accession"),
                "probe_length": probe_len,
            }
            notes.append(f"UniProt probe: {len(result['hits'])} hits")

    confidence = 0.85 if primary["type"] in ["dna", "rna"] else 0.7

    return {
        "annotation": {
            "kind": "sequence",
            "n_records": stats["n_records"],
            "primary_type": primary["type"],
            "length": primary["length"],
        },
        "confidence": confidence,
        "notes": notes,
        "sequence_stats": stats,
        "uniprot_hint": uniprot_hint,
    }
