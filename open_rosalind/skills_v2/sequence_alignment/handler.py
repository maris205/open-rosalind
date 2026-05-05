"""Sequence pairwise alignment handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace, is_error, run_tool
from ..sequence import tools


def handler(payload: dict, trace: Any) -> dict:
    sequence_a = payload.get("sequence_a", "").strip()
    sequence_b = payload.get("sequence_b", "").strip()
    mode = payload.get("mode", "global")

    if not sequence_a or not sequence_b:
        return {
            "annotation": {"kind": "sequence_alignment"},
            "confidence": 0.0,
            "notes": ["Both sequence_a and sequence_b are required"],
            "alignment_result": {},
        }

    trace = ensure_trace(trace)
    result = run_tool(
        trace,
        "sequence.align_pairwise",
        tools.align_pairwise,
        sequence_a=sequence_a,
        sequence_b=sequence_b,
        mode=mode,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "sequence_alignment"},
            "confidence": 0.0,
            "notes": [f"Pairwise alignment failed: {result['error']['message']}"],
            "alignment_result": {},
        }

    return {
        "annotation": {
            "kind": "sequence_alignment",
            "mode": result["mode"],
            "identity": result["identity"],
            "score": result["score"],
            "sequence_a_type": result["sequence_a"]["type"],
            "sequence_b_type": result["sequence_b"]["type"],
        },
        "confidence": 0.85,
        "notes": [],
        "alignment_result": result,
    }
