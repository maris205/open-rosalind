"""ChEMBL search handler."""
from __future__ import annotations

from typing import Any

from ...tools import chembl as chembl_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    entity = str(payload.get("entity") or "molecule").strip().lower()
    query = str(payload.get("query") or payload.get("chembl_id") or "").strip()
    max_results = int(payload.get("max_results", 5) or 5)

    if entity not in {"molecule", "target"}:
        return {
            "annotation": {"kind": "chembl", "source": "ChEMBL", "entity": entity, "n_records": 0},
            "confidence": 0.0,
            "notes": [f"Unsupported ChEMBL entity {entity!r}; use 'molecule' or 'target'"],
            "chembl": {"entity": entity, "query": query, "count": 0, "records": []},
        }

    if not query:
        return {
            "annotation": {"kind": "chembl", "source": "ChEMBL", "entity": entity, "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing ChEMBL query or chembl_id"],
            "chembl": {"entity": entity, "query": "", "count": 0, "records": []},
        }

    trace = ensure_trace(trace)
    if entity == "target":
        result = run_tool(
            trace,
            "chembl.search_targets",
            chembl_tools.search_targets,
            query=query,
            max_results=max_results,
        )
    else:
        result = run_tool(
            trace,
            "chembl.search_molecules",
            chembl_tools.search_molecules,
            query=query,
            max_results=max_results,
        )

    if is_error(result):
        return {
            "annotation": {"kind": "chembl", "source": "ChEMBL", "entity": entity, "query": query, "n_records": 0},
            "confidence": 0.0,
            "notes": [f"ChEMBL search failed: {result['error']['message']}"],
            "chembl": {"entity": entity, "query": query, "count": 0, "records": []},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "chembl",
            "source": "ChEMBL",
            "entity": entity,
            "query": result.get("query", query),
            "n_records": result.get("count", 0),
            "chembl_id": top_record.get("molecule_chembl_id") or top_record.get("target_chembl_id"),
            "pref_name": top_record.get("pref_name"),
            "target_type": top_record.get("target_type"),
            "organism": top_record.get("organism"),
            "max_phase": top_record.get("max_phase"),
        },
        "confidence": 0.8 if result.get("count", 0) > 0 else 0.0,
        "notes": [],
        "chembl": result,
    }
