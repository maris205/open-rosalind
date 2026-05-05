"""PubMed abstract fetch handler."""
from __future__ import annotations

from typing import Any

from ..literature import tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict, trace: Any) -> dict:
    pmids = payload.get("pmids")
    if not pmids:
        return {
            "annotation": {"kind": "literature_abstract", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing PMIDs"],
            "abstracts": {"count": 0, "records": []},
        }

    trace = ensure_trace(trace)
    result = run_tool(trace, "pubmed.fetch_abstract", tools.fetch_abstract, pmids=pmids)
    if is_error(result):
        return {
            "annotation": {"kind": "literature_abstract", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"Abstract fetch failed: {result['error']['message']}"],
            "abstracts": {"count": 0, "records": []},
        }
    return {
        "annotation": {
            "kind": "literature_abstract",
            "n_records": result["count"],
            "top_pmids": [r["pmid"] for r in result["records"][:5]],
        },
        "confidence": 0.75 if result["count"] > 0 else 0.0,
        "notes": [],
        "abstracts": result,
    }
