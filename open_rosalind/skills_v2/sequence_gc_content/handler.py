"""Sequence GC content handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace, is_error, run_tool
from ..sequence import tools


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    sequence = str(payload.get("sequence") or "").strip()
    if not sequence:
        return {
            "annotation": {"kind": "sequence_gc_content", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing sequence"],
            "gc_content": {"records": [], "n_records": 0},
        }

    trace = ensure_trace(trace)
    result = run_tool(trace, "sequence.gc_content", tools.gc_content, sequence=sequence)
    if is_error(result):
        return {
            "annotation": {"kind": "sequence_gc_content", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"GC content calculation failed: {result['error']['message']}"],
            "gc_content": {"records": [], "n_records": 0},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "sequence_gc_content",
            "n_records": result.get("n_records", 0),
            "primary_type": top_record.get("type"),
            "length": top_record.get("length"),
            "gc_percent": top_record.get("gc_percent"),
        },
        "confidence": 0.85 if result.get("n_records", 0) > 0 else 0.0,
        "notes": [],
        "gc_content": result,
    }
