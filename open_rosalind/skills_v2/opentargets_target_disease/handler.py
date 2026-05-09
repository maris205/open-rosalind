"""Open Targets target-disease handler."""
from __future__ import annotations

from typing import Any

from ...tools import opentargets as opentargets_tools
from ..runtime import ensure_trace, is_error, run_tool


def _pick_target_hit(hits: list[dict[str, Any]]) -> dict[str, Any] | None:
    for hit in hits:
        if hit.get("entity") == "target":
            return hit
    return hits[0] if hits else None


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    ensembl_id = str(payload.get("ensembl_id") or "").strip()

    if not query and not ensembl_id:
        return {
            "annotation": {"kind": "opentargets_target_disease", "source": "Open Targets", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing query or ensembl_id"],
            "search": {"count": 0, "hits": []},
            "target_diseases": {"count": 0, "records": []},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search_result = {"count": 0, "hits": []}
    resolved_id = ensembl_id

    if not resolved_id:
        search_result = run_tool(trace, "opentargets.search", opentargets_tools.search, query=query)
        if is_error(search_result):
            return {
                "annotation": {"kind": "opentargets_target_disease", "source": "Open Targets", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Open Targets search failed: {search_result['error']['message']}"],
                "search": {"count": 0, "hits": []},
                "target_diseases": {"count": 0, "records": []},
            }
        hit = _pick_target_hit(search_result.get("hits") or [])
        resolved_id = str((hit or {}).get("id") or "").strip()
        if not resolved_id:
            return {
                "annotation": {"kind": "opentargets_target_disease", "source": "Open Targets", "query": query, "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Could not resolve Open Targets target from query {query!r}"],
                "search": search_result,
                "target_diseases": {"count": 0, "records": []},
            }
        notes.append(f"Resolved query {query!r} to Open Targets target {resolved_id}")

    result = run_tool(
        trace,
        "opentargets.fetch_target_diseases",
        opentargets_tools.fetch_target_diseases,
        ensembl_id=resolved_id,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "opentargets_target_disease", "source": "Open Targets", "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"Open Targets disease fetch failed: {result['error']['message']}"],
            "search": search_result,
            "target_diseases": {"count": 0, "records": []},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "opentargets_target_disease",
            "source": "Open Targets",
            "ensembl_id": result.get("ensembl_id"),
            "approved_symbol": result.get("approved_symbol"),
            "approved_name": result.get("approved_name"),
            "top_disease_id": top_record.get("disease_id"),
            "top_disease_name": top_record.get("disease_name"),
            "top_score": top_record.get("score"),
            "n_records": result.get("count", 0),
        },
        "confidence": 0.85 if result.get("count", 0) > 0 else 0.0,
        "notes": notes,
        "search": search_result,
        "target_diseases": result,
    }
