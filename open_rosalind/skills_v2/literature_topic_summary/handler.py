"""Literature topic summary handler."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from ..literature import tools
from ..literature.helpers import clean_pubmed_query
from ..runtime import ensure_trace, is_error, run_tool

_SUMMARY_STOPWORDS = {
    "about", "across", "after", "also", "among", "analysis", "article", "articles",
    "base", "between", "biology", "cell", "cells", "current", "disease", "editing",
    "effect", "effects", "evidence", "find", "for", "from", "gene", "genes", "human",
    "journal", "latest", "literature", "mechanism", "mechanisms", "method", "methods",
    "new", "paper", "papers", "pathway", "pathways", "protein", "proteins", "recent",
    "report", "reports", "research", "result", "results", "review", "reviews", "role",
    "shows", "signaling", "study", "studies", "summary", "topic", "using", "what",
}


def _merge_records(metadata: dict[str, Any], abstracts: dict[str, Any]) -> list[dict[str, Any]]:
    abstract_map = {record.get("pmid"): record for record in abstracts.get("records", [])}
    records: list[dict[str, Any]] = []
    for record in metadata.get("records", []):
        pmid = record.get("pmid")
        abstract_record = abstract_map.get(pmid, {})
        records.append(
            {
                "pmid": pmid,
                "title": record.get("title"),
                "journal": record.get("journal"),
                "year": record.get("year"),
                "doi": record.get("doi"),
                "url": record.get("url"),
                "abstract": abstract_record.get("abstract") or "",
            }
        )
    return records


def _recurring_terms(records: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query_terms = set(re.findall(r"[A-Za-z][A-Za-z\-]{2,}", query.lower()))
    counter: Counter[str] = Counter()
    for record in records:
        text = " ".join([record.get("title") or "", record.get("abstract") or ""])
        for token in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text.lower()):
            if token in _SUMMARY_STOPWORDS or token in query_terms:
                continue
            counter[token] += 1
    return [{"term": term, "count": count} for term, count in counter.most_common(8)]


def _top_journals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter(record.get("journal") for record in records if record.get("journal"))
    return [{"journal": journal, "count": count} for journal, count in counter.most_common(5)]


def _highlights(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    highlights: list[dict[str, Any]] = []
    for record in records[:5]:
        abstract = (record.get("abstract") or "").strip()
        snippet = abstract.split(". ", 1)[0].strip() if abstract else ""
        if snippet and len(snippet) > 240:
            snippet = snippet[:237].rstrip() + "..."
        highlights.append(
            {
                "pmid": record.get("pmid"),
                "title": record.get("title"),
                "journal": record.get("journal"),
                "year": record.get("year"),
                "snippet": snippet,
            }
        )
    return highlights


def _overview(query: str, records: list[dict[str, Any]], recurring_terms: list[dict[str, Any]]) -> str:
    years = [record.get("year") for record in records if record.get("year")]
    unique_years = sorted({year for year in years if year}, reverse=True)
    top_terms = ", ".join(term["term"] for term in recurring_terms[:5]) or "no recurring terms extracted"
    if unique_years:
        return (
            f"Retrieved {len(records)} PubMed-backed records for {query!r}; "
            f"recurring terms include {top_terms}; publication years span {unique_years[-1]} to {unique_years[0]}."
        )
    return f"Retrieved {len(records)} PubMed-backed records for {query!r}; recurring terms include {top_terms}."


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    max_results = int(payload.get("max_results", 5) or 5)
    if not query:
        return {
            "annotation": {"kind": "literature_topic_summary", "n_hits": 0},
            "confidence": 0.0,
            "notes": ["Missing query"],
            "pubmed": {"query": "", "count": 0, "hits": []},
            "metadata": {"count": 0, "records": []},
            "abstracts": {"count": 0, "records": []},
            "topic_summary": {},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    cleaned_query = clean_pubmed_query(query)
    if cleaned_query != query:
        trace.log("query_cleaned", {"raw": query, "cleaned": cleaned_query})

    search_result = run_tool(trace, "pubmed.search", tools.search, query=cleaned_query, max_results=max_results)
    if not is_error(search_result) and search_result.get("count", 0) == 0 and "[dp]" in cleaned_query:
        relaxed_query = cleaned_query.split(" AND ", 1)[0].strip("() ")
        trace.log("fallback", {"reason": "pubmed empty with year filter; dropping year"})
        retry = run_tool(trace, "pubmed.search", tools.search, query=relaxed_query, max_results=max_results)
        if not is_error(retry) and retry.get("count", 0) > 0:
            search_result = retry
            notes.append(f"Relaxed year-constrained query to {relaxed_query!r}")

    if is_error(search_result):
        return {
            "annotation": {"kind": "literature_topic_summary", "query": cleaned_query, "n_hits": 0},
            "confidence": 0.0,
            "notes": notes + [f"PubMed search failed: {search_result['error']['message']}"],
            "pubmed": {"query": cleaned_query, "count": 0, "hits": []},
            "metadata": {"count": 0, "records": []},
            "abstracts": {"count": 0, "records": []},
            "topic_summary": {},
        }

    pmids = [hit.get("pmid") for hit in (search_result.get("hits") or [])[:max_results] if hit.get("pmid")]
    metadata = {"count": 0, "records": []}
    abstracts = {"count": 0, "records": []}

    if pmids:
        metadata_result = run_tool(trace, "pubmed.fetch_metadata", tools.fetch_metadata, pmids=pmids)
        if is_error(metadata_result):
            notes.append(f"Metadata fetch failed: {metadata_result['error']['message']}")
        else:
            metadata = metadata_result

        abstracts_result = run_tool(trace, "pubmed.fetch_abstract", tools.fetch_abstract, pmids=pmids)
        if is_error(abstracts_result):
            notes.append(f"Abstract fetch failed: {abstracts_result['error']['message']}")
        else:
            abstracts = abstracts_result

    records = _merge_records(metadata, abstracts)
    recurring_terms = _recurring_terms(records, cleaned_query)
    topic_summary = {
        "overview": _overview(cleaned_query, records, recurring_terms),
        "papers_considered": len(records),
        "top_journals": _top_journals(records),
        "recurring_terms": recurring_terms,
        "highlights": _highlights(records),
    }

    return {
        "annotation": {
            "kind": "literature_topic_summary",
            "query": cleaned_query,
            "n_hits": search_result.get("count", 0),
            "top_pmids": pmids,
        },
        "confidence": 0.85 if records else (0.6 if search_result.get("count", 0) > 0 else 0.0),
        "notes": notes,
        "pubmed": search_result,
        "metadata": metadata,
        "abstracts": abstracts,
        "topic_summary": topic_summary,
    }
