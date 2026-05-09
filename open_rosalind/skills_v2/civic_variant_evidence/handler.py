"""CIViC variant evidence handler."""
from __future__ import annotations

from typing import Any

from ...tools import civic as civic_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or payload.get("name") or "").strip()
    if not query:
        return {
            "annotation": {"kind": "civic_variant_evidence", "source": "CIViC", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing CIViC query or variant name"],
            "typeahead": {"count": 0, "records": []},
            "civic": {"count": 0, "records": []},
        }

    trace = ensure_trace(trace)
    typeahead_result = run_tool(trace, "civic.typeahead", civic_tools.typeahead, query=query)
    if is_error(typeahead_result):
        return {
            "annotation": {"kind": "civic_variant_evidence", "source": "CIViC", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"CIViC typeahead failed: {typeahead_result['error']['message']}"],
            "typeahead": {"count": 0, "records": []},
            "civic": {"count": 0, "records": []},
        }

    result = run_tool(
        trace,
        "civic.fetch_variant_evidence",
        civic_tools.fetch_variant_evidence,
        variant_name=query,
        first=3,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "civic_variant_evidence", "source": "CIViC", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"CIViC evidence fetch failed: {result['error']['message']}"],
            "typeahead": typeahead_result,
            "civic": {"count": 0, "records": []},
        }

    top_record = (result.get("records") or [{}])[0]
    top_evidence = (top_record.get("evidence_items") or [{}])[0]
    return {
        "annotation": {
            "kind": "civic_variant_evidence",
            "source": "CIViC",
            "query": result.get("query", query),
            "n_records": result.get("count", 0),
            "variant_name": top_record.get("name"),
            "feature_name": top_record.get("feature_name"),
            "top_evidence_level": top_evidence.get("evidence_level"),
            "top_evidence_type": top_evidence.get("evidence_type"),
            "top_significance": top_evidence.get("significance"),
            "top_disease_name": top_evidence.get("disease_name"),
        },
        "confidence": 0.8 if result.get("count", 0) > 0 else 0.0,
        "notes": [],
        "typeahead": typeahead_result,
        "civic": result,
    }
