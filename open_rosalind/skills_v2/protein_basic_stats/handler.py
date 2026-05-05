"""Protein basic statistics handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace, is_error, run_tool
from ..sequence import tools


def handler(payload: dict, trace: Any) -> dict:
    sequence = payload.get("sequence", "").strip()
    if not sequence:
        return {
            "annotation": {"kind": "protein_basic_stats", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing sequence"],
            "protein_stats": {"records": [], "n_records": 0},
        }

    trace = ensure_trace(trace)
    result = run_tool(trace, "protein.basic_stats", tools.protein_basic_stats, sequence=sequence)
    if is_error(result):
        return {
            "annotation": {"kind": "protein_basic_stats", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"Protein basic stats failed: {result['error']['message']}"],
            "protein_stats": {"records": [], "n_records": 0},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "protein_basic_stats",
            "n_records": result.get("n_records", 0),
            "length": top_record.get("length"),
            "approx_molecular_weight_da": top_record.get("approx_molecular_weight_da"),
        },
        "confidence": 0.85 if result.get("n_records", 0) > 0 else 0.0,
        "notes": [] if result.get("n_records", 0) > 0 else ["No protein records found"],
        "protein_stats": result,
    }
