"""CELLxGENE collection lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import cellxgene as cellxgene_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    collection_id = str(payload.get("collection_id") or "").strip()
    max_results = int(payload.get("max_results", 5) or 5)

    if not collection_id:
        return {
            "annotation": {"kind": "cellxgene_collection", "source": "CELLxGENE", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing collection_id"],
            "cellxgene": {"found": False},
        }

    trace = ensure_trace(trace)
    result = run_tool(
        trace,
        "cellxgene.fetch_collection",
        cellxgene_tools.fetch_collection,
        collection_id=collection_id,
        max_results=max_results,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "cellxgene_collection", "source": "CELLxGENE", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"CELLxGENE lookup failed: {result['error']['message']}"],
            "cellxgene": {"found": False},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "cellxgene_collection",
            "source": "CELLxGENE",
            "collection_id": top_record.get("collection_id"),
            "collection_name": top_record.get("collection_name"),
            "n_datasets": top_record.get("n_datasets"),
            "n_records": result.get("count", 0),
        },
        "confidence": 0.95 if result.get("count", 0) > 0 else 0.0,
        "notes": [],
        "cellxgene": result,
    }
