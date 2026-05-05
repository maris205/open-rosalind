"""Mutation classification handler."""
from __future__ import annotations

from typing import Any

from ..mutation import tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict, trace: Any) -> dict:
    wild_type = str(payload.get("wild_type") or payload.get("wt") or "").strip()
    mutant = str(payload.get("mutant") or payload.get("mt") or "").strip() or None
    mutation = str(payload.get("mutation") or "").strip() or None

    if not wild_type:
        return {
            "annotation": {"kind": "mutation_classification"},
            "confidence": 0.0,
            "notes": ["Missing wild-type sequence"],
            "classification": {},
        }

    if not mutant and not mutation:
        return {
            "annotation": {"kind": "mutation_classification"},
            "confidence": 0.0,
            "notes": ["Missing mutant sequence or HGVS mutation"],
            "classification": {},
        }

    trace = ensure_trace(trace)
    result = run_tool(
        trace,
        "mutation.diff",
        tools.diff,
        wild_type=wild_type,
        mutant=mutant,
        mutation=mutation,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "mutation_classification"},
            "confidence": 0.0,
            "notes": [f"Mutation classification failed: {result['error']['message']}"],
            "classification": {},
        }

    differences = result.get("differences", [])
    categories = []
    if any(diff.get("indel") or diff.get("category") == "indel" for diff in differences):
        categories.append("indel")
    if any(diff.get("mt") == "*" for diff in differences):
        categories.append("nonsense")
    if any(diff.get("category") == "missense" and diff.get("mt") != "*" for diff in differences):
        categories.append("missense")
    if not differences:
        categories.append("synonymous_or_no_change")

    return {
        "annotation": {
            "kind": "mutation_classification",
            "n_differences": result.get("n_differences", 0),
            "categories": categories,
            "overall_assessment": result.get("overall_assessment"),
        },
        "confidence": 0.8,
        "notes": [],
        "classification": {
            "n_differences": result.get("n_differences", 0),
            "categories": categories,
            "differences": differences,
            "overall_assessment": result.get("overall_assessment"),
            "disclaimer": result.get("disclaimer"),
        },
    }
