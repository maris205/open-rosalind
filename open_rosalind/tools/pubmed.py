"""PubMed E-utilities client (esearch + esummary)."""
from __future__ import annotations

from typing import Any

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def search(query: str, max_results: int = 5) -> dict[str, Any]:
    es = get_json(
        f"{BASE_URL}/esearch.fcgi",
        params={"db": "pubmed", "term": query, "retmode": "json", "retmax": max_results, "sort": "relevance"},
        timeout=30,
    )
    ids = es.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return {"query": query, "count": 0, "hits": []}
    sm = get_json(
        f"{BASE_URL}/esummary.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
        timeout=30,
    )
    res = sm.get("result", {})
    hits = []
    for pmid in ids:
        d = res.get(pmid, {})
        if not d:
            continue
        authors = [a.get("name") for a in (d.get("authors") or []) if a.get("name")]
        hits.append({
            "pmid": pmid,
            "title": d.get("title"),
            "authors": authors[:5],
            "journal": d.get("fulljournalname") or d.get("source"),
            "year": (d.get("pubdate") or "").split(" ")[0],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return {"query": query, "count": len(hits), "hits": hits}


SEARCH_SPEC = ToolSpec(
    name="pubmed.search",
    description="Search PubMed for biomedical literature. Returns top-N papers with title, authors, journal, year, PMID, URL.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search,
)
