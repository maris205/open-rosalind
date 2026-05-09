"""ChEBI compound lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import chebi as chebi_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    chebi_id = str(payload.get("chebi_id") or "").strip()

    if not query and not chebi_id:
        return {
            "annotation": {"kind": "chebi_compound", "source": "ChEBI", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing query or chebi_id"],
            "search": {"count": 0, "records": []},
            "chebi": {"found": False},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search_result = {"count": 0, "records": []}
    resolved_chebi_id = chebi_id

    if not resolved_chebi_id:
        search_result = run_tool(
            trace,
            "chebi.search_compounds",
            chebi_tools.search_compounds,
            query=query,
            max_results=int(payload.get("max_results", 5) or 5),
        )
        if is_error(search_result):
            return {
                "annotation": {"kind": "chebi_compound", "source": "ChEBI", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"ChEBI search failed: {search_result['error']['message']}"],
                "search": {"count": 0, "records": []},
                "chebi": {"found": False},
            }
        hit = (search_result.get("records") or [{}])[0]
        resolved_chebi_id = str(hit.get("chebi_accession") or "").strip()
        if not resolved_chebi_id:
            return {
                "annotation": {"kind": "chebi_compound", "source": "ChEBI", "query": query, "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Could not resolve a ChEBI compound from query {query!r}"],
                "search": search_result,
                "chebi": {"found": False},
            }
        notes.append(f"Resolved query {query!r} to ChEBI compound {resolved_chebi_id}")

    result = run_tool(
        trace,
        "chebi.fetch_compound",
        chebi_tools.fetch_compound,
        chebi_id=resolved_chebi_id,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "chebi_compound", "source": "ChEBI", "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"ChEBI fetch failed: {result['error']['message']}"],
            "search": search_result,
            "chebi": {"found": False},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "chebi_compound",
            "source": "ChEBI",
            "chebi_accession": top_record.get("chebi_accession"),
            "name": top_record.get("name"),
            "definition": top_record.get("definition"),
            "n_records": result.get("count", 0),
        },
        "confidence": 0.9 if result.get("count", 0) > 0 else 0.0,
        "notes": notes,
        "search": search_result,
        "chebi": result,
    }
