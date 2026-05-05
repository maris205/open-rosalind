"""PubMed E-utilities client (esearch + esummary + efetch)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from ._http import get_json, make_session
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


def fetch_metadata(pmids: list[str] | str) -> dict[str, Any]:
    if isinstance(pmids, str):
        pmid_list = [pmids]
    else:
        pmid_list = [str(p).strip() for p in pmids if str(p).strip()]
    if not pmid_list:
        return {"count": 0, "records": []}

    sm = get_json(
        f"{BASE_URL}/esummary.fcgi",
        params={"db": "pubmed", "id": ",".join(pmid_list), "retmode": "json"},
        timeout=30,
    )
    res = sm.get("result", {})
    records = []
    for pmid in pmid_list:
        d = res.get(pmid, {})
        if not d:
            continue
        authors = [a.get("name") for a in (d.get("authors") or []) if a.get("name")]
        article_ids = d.get("articleids") or []
        doi = next((a.get("value") for a in article_ids if a.get("idtype") == "doi"), None)
        records.append({
            "pmid": pmid,
            "title": d.get("title"),
            "authors": authors[:10],
            "journal": d.get("fulljournalname") or d.get("source"),
            "year": (d.get("pubdate") or "").split(" ")[0],
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return {"count": len(records), "records": records}


def fetch_abstract(pmids: list[str] | str) -> dict[str, Any]:
    if isinstance(pmids, str):
        pmid_list = [pmids]
    else:
        pmid_list = [str(p).strip() for p in pmids if str(p).strip()]
    if not pmid_list:
        return {"count": 0, "records": []}

    session = make_session()
    resp = session.get(
        f"{BASE_URL}/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(pmid_list), "rettype": "abstract", "retmode": "xml"},
        timeout=30,
    )
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    records = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        title = article.findtext(".//ArticleTitle") or ""
        abstract_parts = []
        for abstract_node in article.findall(".//Abstract/AbstractText"):
            label = abstract_node.attrib.get("Label")
            text = "".join(abstract_node.itertext()).strip()
            if not text:
                continue
            abstract_parts.append(f"{label}: {text}" if label else text)
        records.append({
            "pmid": pmid,
            "title": title,
            "abstract": "\n".join(abstract_parts).strip(),
        })
    return {"count": len(records), "records": records}


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


FETCH_METADATA_SPEC = ToolSpec(
    name="pubmed.fetch_metadata",
    description="Fetch PubMed metadata for one or more PMIDs, including authors, journal, year, DOI, and URL.",
    input_schema={
        "type": "object",
        "properties": {
            "pmids": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ]
            }
        },
        "required": ["pmids"],
    },
    output_schema={"type": "object"},
    handler=fetch_metadata,
)


FETCH_ABSTRACT_SPEC = ToolSpec(
    name="pubmed.fetch_abstract",
    description="Fetch PubMed abstracts for one or more PMIDs.",
    input_schema={
        "type": "object",
        "properties": {
            "pmids": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ]
            }
        },
        "required": ["pmids"],
    },
    output_schema={"type": "object"},
    handler=fetch_abstract,
)
