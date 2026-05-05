"""PubMed search tools."""
from __future__ import annotations

from ...tools import pubmed as base_pubmed

def search(query: str, max_results: int = 10) -> dict:
    return base_pubmed.search(query=query, max_results=max_results)


def fetch_metadata(pmids: list[str] | str) -> dict:
    return base_pubmed.fetch_metadata(pmids=pmids)


def fetch_abstract(pmids: list[str] | str) -> dict:
    return base_pubmed.fetch_abstract(pmids=pmids)
