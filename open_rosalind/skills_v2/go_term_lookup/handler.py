"""GO term lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import quickgo as quickgo_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    term_id = str(payload.get("term_id") or "").strip()
    max_results = int(payload.get("max_results", 5) or 5)

    if not query and not term_id:
        return {
            "annotation": {"kind": "go_term", "source": "QuickGO", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing GO query or term_id"],
            "search": {"query": "", "count": 0, "records": []},
            "term": {},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search_result = {"query": query, "count": 0, "records": []}
    resolved_term_id = term_id

    if not resolved_term_id:
        search_result = run_tool(
            trace,
            "quickgo.search_terms",
            quickgo_tools.search_terms,
            query=query,
            max_results=max_results,
        )
        if is_error(search_result):
            return {
                "annotation": {"kind": "go_term", "source": "QuickGO", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"GO search failed: {search_result['error']['message']}"],
                "search": {"query": query, "count": 0, "records": []},
                "term": {},
            }

        top_record = (search_result.get("records") or [{}])[0]
        resolved_term_id = str(top_record.get("id") or "").strip()
        if not resolved_term_id:
            return {
                "annotation": {"kind": "go_term", "source": "QuickGO", "query": query, "n_records": 0},
                "confidence": 0.0,
                "notes": [f"No GO terms found for {query!r}"],
                "search": search_result,
                "term": {},
            }
        notes.append(f"Resolved GO query {query!r} to term {resolved_term_id}")

    term_result = run_tool(
        trace,
        "quickgo.fetch_term",
        quickgo_tools.fetch_term,
        term_id=resolved_term_id,
    )
    if is_error(term_result):
        return {
            "annotation": {"kind": "go_term", "source": "QuickGO", "term_id": resolved_term_id, "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"GO fetch failed: {term_result['error']['message']}"],
            "search": search_result,
            "term": {},
        }
    if not term_result.get("found", True):
        return {
            "annotation": {"kind": "go_term", "source": "QuickGO", "term_id": resolved_term_id, "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"GO term {resolved_term_id} was not found"],
            "search": search_result,
            "term": term_result,
        }

    return {
        "annotation": {
            "kind": "go_term",
            "source": "QuickGO",
            "term_id": term_result.get("id"),
            "name": term_result.get("name"),
            "aspect": term_result.get("aspect"),
            "is_obsolete": term_result.get("is_obsolete"),
            "n_child_terms": len(term_result.get("child_terms") or []),
        },
        "confidence": 0.85,
        "notes": notes,
        "search": search_result,
        "term": term_result,
    }
