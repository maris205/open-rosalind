"""Protein-level helper tools built on UniProt."""
from __future__ import annotations

from ..uniprot import tools as uniprot_tools


def annotation_summary(query: str, accession: str | None = None) -> dict:
    if accession:
        entry = uniprot_tools.fetch(accession=accession)
        return {"entry": entry, "search": {"count": 1, "hits": [entry]}}

    results = uniprot_tools.search(query=query, max_results=5)
    if not results.get("hits"):
        return {"entry": {}, "search": results}
    top = results["hits"][0]
    entry = uniprot_tools.fetch(accession=top["accession"])
    return {"entry": entry, "search": results}
