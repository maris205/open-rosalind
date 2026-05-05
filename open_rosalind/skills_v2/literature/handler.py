"""Literature search handler."""
from __future__ import annotations

from typing import Any

from . import tools
from .helpers import clean_pubmed_query
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict:
    query = payload.get("query", "").strip()
    if not query:
        return {"annotation": {"kind": "literature"}, "confidence": 0.0, "notes": ["Empty query"], "pubmed": {}}

    trace = ensure_trace(trace)
    notes: list[str] = []
    cleaned_query = clean_pubmed_query(query)
    if cleaned_query != query:
        trace.log("query_cleaned", {"raw": query, "cleaned": cleaned_query})

    results = run_tool(trace, "pubmed.search", tools.search, query=cleaned_query, max_results=10)
    if not is_error(results) and results.get("count", 0) == 0 and "[dp]" in cleaned_query:
        relaxed_query = cleaned_query.split(" AND ", 1)[0].strip("() ")
        trace.log("fallback", {"reason": "pubmed empty with year filter; dropping year"})
        retry = run_tool(trace, "pubmed.search", tools.search, query=relaxed_query, max_results=10)
        if not is_error(retry) and retry.get("count", 0) > 0:
            results = retry
            notes.append(f"Relaxed year-constrained query to {relaxed_query!r}")

    if is_error(results):
        return {
            "annotation": {"kind": "literature"},
            "confidence": 0.0,
            "notes": notes + [f"Search failed: {results['error']['message']}"],
            "pubmed": {},
        }

    pmids = [h["pmid"] for h in results["hits"][:3] if h.get("pmid")]
    metadata = {"count": 0, "records": []}
    abstracts = {"count": 0, "records": []}

    if pmids:
        md = run_tool(trace, "pubmed.fetch_metadata", tools.fetch_metadata, pmids=pmids)
        if is_error(md):
            notes.append(f"Metadata fetch failed: {md['error']['message']}")
        else:
            metadata = md

        ab = run_tool(trace, "pubmed.fetch_abstract", tools.fetch_abstract, pmids=pmids)
        if is_error(ab):
            notes.append(f"Abstract fetch failed: {ab['error']['message']}")
        else:
            abstracts = ab

    return {
        "annotation": {
            "kind": "literature",
            "query": cleaned_query,
            "n_hits": results["count"],
            "top_pmids": pmids,
        },
        "confidence": 0.8 if results["count"] > 0 else 0.0,
        "notes": notes,
        "pubmed": results,
        "metadata": metadata,
        "abstracts": abstracts,
    }
