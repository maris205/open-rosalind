"""Sequence reverse complement handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace, is_error, run_tool
from ..sequence import tools


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    sequence = str(payload.get("sequence") or "").strip()
    if not sequence:
        return {
            "annotation": {"kind": "sequence_reverse_complement", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing sequence"],
            "reverse_complement": {"records": [], "n_records": 0},
        }

    trace = ensure_trace(trace)
    result = run_tool(trace, "sequence.reverse_complement", tools.reverse_complement, sequence=sequence)
    if is_error(result):
        return {
            "annotation": {"kind": "sequence_reverse_complement", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"Reverse-complement failed: {result['error']['message']}"],
            "reverse_complement": {"records": [], "n_records": 0},
        }

    top_record = (result.get("records") or [{}])[0]
    reverse_complement = top_record.get("reverse_complement")
    return {
        "annotation": {
            "kind": "sequence_reverse_complement",
            "n_records": result.get("n_records", 0),
            "primary_type": top_record.get("type"),
            "length": top_record.get("length"),
            "reverse_complement_preview": (
                reverse_complement[:60] if isinstance(reverse_complement, str) else None
            ),
        },
        "confidence": 0.85 if reverse_complement else 0.0,
        "notes": [] if reverse_complement else ["Input sequence was not classified as DNA or RNA"],
        "reverse_complement": result,
    }
