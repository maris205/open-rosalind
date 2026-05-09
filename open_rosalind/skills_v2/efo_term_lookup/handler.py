"""EFO term lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import efo as efo_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    term_id = str(payload.get("term_id") or payload.get("iri") or "").strip()
    max_results = int(payload.get("max_results", 5) or 5)

    if not query and not term_id:
        return {
            "annotation": {"kind": "efo_term", "source": "EFO", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing query or term_id"],
            "search": {"count": 0, "records": []},
            "efo": {"found": False},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search_result = {"count": 0, "records": []}
    resolved_term_id = term_id

    if not resolved_term_id or not resolved_term_id.startswith(("http://", "https://")):
        search_result = run_tool(
            trace,
            "efo.search_terms",
            efo_tools.search_terms,
            query=query or term_id,
            max_results=max_results,
        )
        if is_error(search_result):
            return {
                "annotation": {"kind": "efo_term", "source": "EFO", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"EFO search failed: {search_result['error']['message']}"],
                "search": {"count": 0, "records": []},
                "efo": {"found": False},
            }
        hit = (search_result.get("records") or [{}])[0]
        resolved_term_id = str(hit.get("iri") or hit.get("obo_id") or "").strip()
        if not resolved_term_id:
            return {
                "annotation": {"kind": "efo_term", "source": "EFO", "query": query or term_id, "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Could not resolve an EFO term from query {query or term_id!r}"],
                "search": search_result,
                "efo": {"found": False},
            }
        notes.append(f"Resolved query {query or term_id!r} to EFO term {resolved_term_id}")

    result = run_tool(
        trace,
        "efo.fetch_term",
        efo_tools.fetch_term,
        term_id=resolved_term_id,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "efo_term", "source": "EFO", "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"EFO fetch failed: {result['error']['message']}"],
            "search": search_result,
            "efo": {"found": False},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "efo_term",
            "source": "EFO",
            "iri": top_record.get("iri"),
            "label": top_record.get("label"),
            "obo_id": top_record.get("obo_id"),
            "has_children": top_record.get("has_children"),
            "n_records": result.get("count", 0),
        },
        "confidence": 0.9 if result.get("count", 0) > 0 else 0.0,
        "notes": notes,
        "search": search_result,
        "efo": result,
    }
