"""NCBI Gene lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import ncbi_gene as ncbi_gene_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or payload.get("gene_symbol") or payload.get("symbol") or "").strip()
    gene_id = str(payload.get("gene_id") or "").strip()
    species = str(payload.get("species") or "Homo sapiens").strip() or "Homo sapiens"
    max_results = int(payload.get("max_results", 3) or 3)

    if not query and not gene_id:
        return {
            "annotation": {"kind": "gene", "source": "NCBI Gene", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing NCBI gene query or gene_id"],
            "search": {"query": "", "species": species, "count": 0, "ids": []},
            "gene": {},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search_result = {"query": query, "species": species, "count": 0, "ids": []}
    resolved_gene_id = gene_id

    if not resolved_gene_id:
        search_result = run_tool(
            trace,
            "ncbi_gene.search_gene",
            ncbi_gene_tools.search_gene,
            query=query,
            species=species,
            max_results=max_results,
        )
        if is_error(search_result):
            return {
                "annotation": {"kind": "gene", "source": "NCBI Gene", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"NCBI Gene search failed: {search_result['error']['message']}"],
                "search": {"query": query, "species": species, "count": 0, "ids": []},
                "gene": {},
            }
        resolved_gene_id = str((search_result.get("ids") or [""])[0]).strip()
        if not resolved_gene_id:
            return {
                "annotation": {"kind": "gene", "source": "NCBI Gene", "query": query, "n_records": 0},
                "confidence": 0.0,
                "notes": [f"No NCBI Gene record was found for {query!r}"],
                "search": search_result,
                "gene": {},
            }
        notes.append(f"Resolved NCBI query {query!r} to Gene ID {resolved_gene_id}")

    gene_result = run_tool(trace, "ncbi_gene.fetch_gene", ncbi_gene_tools.fetch_gene, gene_id=resolved_gene_id)
    if is_error(gene_result):
        return {
            "annotation": {"kind": "gene", "source": "NCBI Gene", "gene_id": resolved_gene_id, "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"NCBI Gene fetch failed: {gene_result['error']['message']}"],
            "search": search_result,
            "gene": {},
        }
    if not gene_result.get("found", True):
        return {
            "annotation": {"kind": "gene", "source": "NCBI Gene", "gene_id": resolved_gene_id, "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"NCBI Gene record {resolved_gene_id} was not found"],
            "search": search_result,
            "gene": gene_result,
        }

    return {
        "annotation": {
            "kind": "gene",
            "source": "NCBI Gene",
            "gene_id": gene_result.get("gene_id"),
            "symbol": gene_result.get("symbol"),
            "species": gene_result.get("species"),
            "chromosome": gene_result.get("chromosome"),
            "map_location": gene_result.get("map_location"),
            "mim_ids": gene_result.get("mim_ids") or [],
        },
        "confidence": 0.88,
        "notes": notes,
        "search": search_result,
        "gene": gene_result,
    }
