"""Protein molecular weight handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace, is_error, run_tool
from ..sequence import tools


def handler(payload: dict, trace: Any) -> dict:
    sequence = payload.get("sequence", "").strip()
    if not sequence:
        return {
            "annotation": {"kind": "protein_molecular_weight"},
            "confidence": 0.0,
            "notes": ["Missing sequence"],
            "molecular_weight": {},
        }

    trace = ensure_trace(trace)
    result = run_tool(trace, "protein.basic_stats", tools.protein_basic_stats, sequence=sequence)
    if is_error(result):
        return {
            "annotation": {"kind": "protein_molecular_weight"},
            "confidence": 0.0,
            "notes": [f"Protein molecular weight failed: {result['error']['message']}"],
            "molecular_weight": {},
        }

    records = result.get("records") or []
    if not records:
        return {
            "annotation": {"kind": "protein_molecular_weight"},
            "confidence": 0.0,
            "notes": ["No protein records found"],
            "molecular_weight": {},
        }

    top_record = records[0]
    return {
        "annotation": {
            "kind": "protein_molecular_weight",
            "length": top_record.get("length"),
            "approx_molecular_weight_da": top_record.get("approx_molecular_weight_da"),
        },
        "confidence": 0.85,
        "notes": [],
        "molecular_weight": {
            "n_records": result.get("n_records", 0),
            "records": [
                {
                    "header": record.get("header"),
                    "length": record.get("length"),
                    "approx_molecular_weight_da": record.get("approx_molecular_weight_da"),
                }
                for record in records
            ],
        },
    }
