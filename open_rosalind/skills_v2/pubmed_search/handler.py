"""PubMed search handler."""
from __future__ import annotations

from typing import Any

from ..literature import tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict, trace: Any) -> dict:
    query = payload.get("query", "").strip()
    max_results = int(payload.get("max_results", 10) or 10)
    if not query:
        return {
            "annotation": {"kind": "literature", "n_hits": 0},
            "confidence": 0.0,
            "notes": ["Missing query"],
            "pubmed": {"query": "", "count": 0, "hits": []},
        }

    trace = ensure_trace(trace)
    result = run_tool(trace, "pubmed.search", tools.search, query=query, max_results=max_results)
    if is_error(result):
        return {
            "annotation": {"kind": "literature", "n_hits": 0},
            "confidence": 0.0,
            "notes": [f"PubMed search failed: {result['error']['message']}"],
            "pubmed": {"query": query, "count": 0, "hits": []},
        }

    return {
        "annotation": {
            "kind": "literature",
            "query": result.get("query", query),
            "n_hits": result.get("count", 0),
            "top_pmids": [hit.get("pmid") for hit in (result.get("hits") or [])[:5] if hit.get("pmid")],
        },
        "confidence": 0.8 if result.get("count", 0) > 0 else 0.0,
        "notes": [],
        "pubmed": result,
    }
