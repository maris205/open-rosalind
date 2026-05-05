"""Sequence translation handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace, is_error, run_tool
from ..sequence import tools


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    sequence = str(payload.get("sequence") or "").strip()
    if not sequence:
        return {
            "annotation": {"kind": "sequence_translation", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing sequence"],
            "translation": {"records": [], "n_records": 0},
        }

    trace = ensure_trace(trace)
    result = run_tool(trace, "sequence.translate", tools.translate, sequence=sequence)
    if is_error(result):
        return {
            "annotation": {"kind": "sequence_translation", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"Sequence translation failed: {result['error']['message']}"],
            "translation": {"records": [], "n_records": 0},
        }

    top_record = (result.get("records") or [{}])[0]
    translation = top_record.get("translation")
    return {
        "annotation": {
            "kind": "sequence_translation",
            "n_records": result.get("n_records", 0),
            "primary_type": top_record.get("type"),
            "length": top_record.get("length"),
            "translation_preview": translation[:60] if isinstance(translation, str) else None,
        },
        "confidence": 0.85 if translation else 0.0,
        "notes": [] if translation else ["Input sequence was not classified as DNA or RNA"],
        "translation": result,
    }
