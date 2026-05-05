"""Sequence type detection handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace, is_error, run_tool
from ..sequence import tools


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    sequence = str(payload.get("sequence") or "").strip()
    if not sequence:
        return {
            "annotation": {"kind": "sequence_type", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing sequence"],
            "sequence_type": {"records": [], "n_records": 0},
        }

    trace = ensure_trace(trace)
    result = run_tool(trace, "sequence.detect_type", tools.detect_type, sequence=sequence)
    if is_error(result):
        return {
            "annotation": {"kind": "sequence_type", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"Sequence type detection failed: {result['error']['message']}"],
            "sequence_type": {"records": [], "n_records": 0},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "sequence_type",
            "n_records": result.get("n_records", 0),
            "primary_type": top_record.get("type"),
            "length": top_record.get("length"),
        },
        "confidence": 0.85 if result.get("n_records", 0) > 0 else 0.0,
        "notes": [],
        "sequence_type": result,
    }
