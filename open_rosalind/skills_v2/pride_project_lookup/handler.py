"""PRIDE project lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import pride as pride_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    accession = str(payload.get("accession") or "").strip()
    query = str(payload.get("query") or payload.get("keyword") or "").strip()
    max_results = int(payload.get("max_results", 5) or 5)

    if not accession and not query:
        return {
            "annotation": {"kind": "pride_project", "source": "PRIDE", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing accession or query"],
            "search": {"count": 0, "records": []},
            "pride": {"found": False},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search_result = {"count": 0, "records": []}
    resolved_accession = accession

    if not resolved_accession:
        search_result = run_tool(
            trace,
            "pride.search_projects",
            pride_tools.search_projects,
            keyword=query,
            max_results=max_results,
        )
        if is_error(search_result):
            return {
                "annotation": {"kind": "pride_project", "source": "PRIDE", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"PRIDE search failed: {search_result['error']['message']}"],
                "search": {"count": 0, "records": []},
                "pride": {"found": False},
            }
        hit = (search_result.get("records") or [{}])[0]
        resolved_accession = str(hit.get("accession") or "").strip()
        if not resolved_accession:
            return {
                "annotation": {"kind": "pride_project", "source": "PRIDE", "query": query, "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Could not resolve a PRIDE project from query {query!r}"],
                "search": search_result,
                "pride": {"found": False},
            }
        notes.append(f"Resolved query {query!r} to PRIDE project {resolved_accession}")

    result = run_tool(
        trace,
        "pride.fetch_project",
        pride_tools.fetch_project,
        accession=resolved_accession,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "pride_project", "source": "PRIDE", "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"PRIDE fetch failed: {result['error']['message']}"],
            "search": search_result,
            "pride": {"found": False},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "pride_project",
            "source": "PRIDE",
            "accession": top_record.get("accession"),
            "title": top_record.get("title"),
            "doi": top_record.get("doi"),
            "n_records": result.get("count", 0),
        },
        "confidence": 0.9 if result.get("count", 0) > 0 else 0.0,
        "notes": notes,
        "search": search_result,
        "pride": result,
    }
