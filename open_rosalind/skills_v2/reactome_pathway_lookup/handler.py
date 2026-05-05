"""Reactome pathway lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import reactome as reactome_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    stable_id = str(payload.get("stable_id") or "").strip()
    species = str(payload.get("species") or "Homo sapiens").strip() or "Homo sapiens"
    max_results = int(payload.get("max_results", 5) or 5)

    if not query and not stable_id:
        return {
            "annotation": {"kind": "pathway", "source": "Reactome", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing Reactome query or stable_id"],
            "search": {"query": "", "species": species, "count": 0, "records": []},
            "pathway": {},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search_result = {"query": query, "species": species, "count": 0, "records": []}
    resolved_stable_id = stable_id

    if not resolved_stable_id:
        search_result = run_tool(
            trace,
            "reactome.search_pathways",
            reactome_tools.search_pathways,
            query=query,
            species=species,
            max_results=max_results,
        )
        if is_error(search_result):
            return {
                "annotation": {"kind": "pathway", "source": "Reactome", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Reactome search failed: {search_result['error']['message']}"],
                "search": {"query": query, "species": species, "count": 0, "records": []},
                "pathway": {},
            }

        top_record = (search_result.get("records") or [{}])[0]
        resolved_stable_id = str(top_record.get("st_id") or "").strip()
        if not resolved_stable_id:
            return {
                "annotation": {"kind": "pathway", "source": "Reactome", "query": query, "n_records": 0},
                "confidence": 0.0,
                "notes": [f"No Reactome pathways found for {query!r}"],
                "search": search_result,
                "pathway": {},
            }
        notes.append(f"Resolved Reactome query {query!r} to pathway {resolved_stable_id}")

    pathway_result = run_tool(
        trace,
        "reactome.fetch_pathway",
        reactome_tools.fetch_pathway,
        stable_id=resolved_stable_id,
    )
    if is_error(pathway_result):
        return {
            "annotation": {"kind": "pathway", "source": "Reactome", "stable_id": resolved_stable_id, "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"Reactome fetch failed: {pathway_result['error']['message']}"],
            "search": search_result,
            "pathway": {},
        }

    return {
        "annotation": {
            "kind": "pathway",
            "source": "Reactome",
            "stable_id": pathway_result.get("st_id"),
            "name": pathway_result.get("display_name"),
            "species": pathway_result.get("species"),
            "event_count": pathway_result.get("event_count"),
            "literature_count": len(pathway_result.get("literature") or []),
        },
        "confidence": 0.85,
        "notes": notes,
        "search": search_result,
        "pathway": pathway_result,
    }
