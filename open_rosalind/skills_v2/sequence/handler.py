"""Sequence basic analysis skill handler."""
from __future__ import annotations

from typing import Any

from . import tools as seq_tools


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
    from ...tools.registry import REGISTRY

    sequence = payload.get("sequence", "").strip()
    if not sequence:
        return {
            "annotation": {"kind": "sequence"},
            "confidence": 0.0,
            "notes": ["Empty sequence"],
            "sequence_stats": {},
        }

    notes = []

    # 1. Analyze sequence locally
    stats = seq_tools.analyze(sequence)

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
        probe = primary["sequence"][:probe_len]

        # Call uniprot.search via registry
        search_fn = REGISTRY.get("uniprot.search")
        if search_fn:
            try:
                result = search_fn.handler(query=probe, trace=trace)
                if result.get("hits"):
                    uniprot_hint = {
                        "hits": len(result["hits"]),
                        "top_match": result["hits"][0].get("accession"),
                        "probe_length": probe_len,
                    }
                    notes.append(f"UniProt probe: {len(result['hits'])} hits")
            except Exception as e:
                notes.append(f"UniProt probe failed: {e}")

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
