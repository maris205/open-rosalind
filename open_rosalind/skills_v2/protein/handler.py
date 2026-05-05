"""Protein annotation summary handler."""
from __future__ import annotations

from typing import Any

from . import tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict, trace: Any) -> dict:
    query = payload.get("query", "").strip()
    accession = payload.get("accession", "").strip()
    if not query and not accession:
        return {
            "annotation": {"kind": "protein"},
            "confidence": 0.0,
            "notes": ["Empty protein query"],
            "entry": {},
            "search": {},
        }

    trace = ensure_trace(trace)
    summary = run_tool(
        trace,
        "protein.annotation_summary",
        tools.annotation_summary,
        query=query,
        accession=accession or None,
    )
    if is_error(summary):
        return {
            "annotation": {"kind": "protein"},
            "confidence": 0.0,
            "notes": [f"Protein annotation failed: {summary['error']['message']}"],
            "entry": {},
            "search": {},
        }

    entry = summary.get("entry") or {}
    search = summary.get("search") or {}
    hits = search.get("hits") or []
    return {
        "annotation": {
            "kind": "protein",
            "accession": entry.get("accession"),
            "name": entry.get("name"),
            "organism": entry.get("organism"),
            "function": entry.get("function"),
            "length": entry.get("length"),
            "homology_hint": [
                {"accession": h.get("accession"), "organism": h.get("organism"), "name": h.get("name")}
                for h in hits[:3]
            ],
        },
        "confidence": 0.9 if accession else (0.75 if hits else 0.0),
        "notes": [],
        "entry": entry,
        "search": search,
    }
