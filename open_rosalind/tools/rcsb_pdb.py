"""RCSB PDB Search API and core metadata client."""
from __future__ import annotations

from typing import Any

import requests

from ._http import get_json, post_json
from .base import ToolSpec

SEARCH_ENDPOINT = "https://search.rcsb.org/rcsbsearch/v2/query"
CORE_ENTRY_BASE = "https://data.rcsb.org/rest/v1/core/entry"


def _first_resolution(entry_info: dict[str, Any], refine: list[dict[str, Any]]) -> float | None:
    combined = entry_info.get("resolution_combined")
    if isinstance(combined, list) and combined:
        try:
            return float(combined[0])
        except (TypeError, ValueError):
            return None
    raw = entry_info.get("diffrn_resolution_high")
    if raw is not None:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    if refine:
        raw = refine[0].get("ls_d_res_high")
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None
    return None


def search_entries(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search RCSB PDB entries with the Search API."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    limit = max(1, min(int(max_results), 10))
    data = post_json(
        SEARCH_ENDPOINT,
        {
            "query": {
                "type": "terminal",
                "service": "full_text",
                "parameters": {"value": clean_query},
            },
            "return_type": "entry",
            "request_options": {
                "paginate": {"start": 0, "rows": limit},
                "scoring_strategy": "combined",
            },
        },
        timeout=60,
    )

    result_set = data.get("result_set") or []
    records = []
    for item in result_set[:limit]:
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "entry_id": item.get("identifier"),
                "score": item.get("score"),
            }
        )

    return {
        "query": clean_query,
        "count": len(records),
        "total_count": data.get("total_count"),
        "records": records,
    }


def fetch_entry(entry_id: str) -> dict[str, Any]:
    """Fetch focused core metadata for an RCSB PDB entry."""
    clean_id = entry_id.strip().upper()
    if not clean_id:
        raise ValueError("entry_id is required")

    try:
        data = get_json(f"{CORE_ENTRY_BASE}/{clean_id}", timeout=60)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            return {"entry_id": clean_id, "found": False}
        raise

    struct = data.get("struct") or {}
    entry_info = data.get("rcsb_entry_info") or {}
    citation = data.get("rcsb_primary_citation") or {}
    accession = data.get("rcsb_accession_info") or {}
    identifiers = data.get("rcsb_entry_container_identifiers") or {}
    exptl = data.get("exptl") or []
    refine = [item for item in (data.get("refine") or []) if isinstance(item, dict)]

    methods = [
        item.get("method")
        for item in exptl
        if isinstance(item, dict) and item.get("method")
    ]
    polymer_entity_ids = identifiers.get("polymer_entity_ids") or []
    nonpolymer_entity_ids = identifiers.get("non_polymer_entity_ids") or []

    return {
        "entry_id": identifiers.get("entry_id") or clean_id,
        "found": True,
        "title": struct.get("title"),
        "experimental_methods": methods or [_ for _ in [entry_info.get("experimental_method")] if _],
        "resolution": _first_resolution(entry_info, refine),
        "structure_methodology": entry_info.get("structure_determination_methodology"),
        "polymer_entity_count": entry_info.get("polymer_entity_count"),
        "nonpolymer_entity_count": entry_info.get("nonpolymer_entity_count"),
        "assembly_count": entry_info.get("assembly_count"),
        "molecular_weight": entry_info.get("molecular_weight"),
        "polymer_entity_ids": polymer_entity_ids,
        "nonpolymer_entity_ids": nonpolymer_entity_ids,
        "pubmed_id": identifiers.get("pubmed_id") or citation.get("pdbx_database_id_PubMed"),
        "citation_title": citation.get("title"),
        "citation_year": citation.get("year"),
        "citation_doi": citation.get("pdbx_database_id_DOI"),
        "deposit_date": accession.get("deposit_date"),
        "release_date": accession.get("initial_release_date"),
        "revision_date": accession.get("revision_date"),
        "url": f"https://www.rcsb.org/structure/{clean_id}",
    }


SEARCH_ENTRIES_SPEC = ToolSpec(
    name="rcsb_pdb.search_entries",
    description="Search RCSB PDB entries with the full-text Search API.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search_entries,
)


FETCH_ENTRY_SPEC = ToolSpec(
    name="rcsb_pdb.fetch_entry",
    description="Fetch focused RCSB PDB core metadata for an entry identifier.",
    input_schema={
        "type": "object",
        "properties": {"entry_id": {"type": "string"}},
        "required": ["entry_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_entry,
)
