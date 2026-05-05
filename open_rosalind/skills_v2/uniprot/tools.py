"""UniProt tools: fetch and search."""
from __future__ import annotations

from ...tools import uniprot as base_uniprot

def fetch(accession: str) -> dict:
    return base_uniprot.fetch(accession=accession)


def search(query: str, max_results: int = 10) -> dict:
    return base_uniprot.search(query=query, size=max_results)
