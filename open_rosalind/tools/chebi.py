"""ChEBI public API client."""
from __future__ import annotations

from typing import Any

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://www.ebi.ac.uk"


def _normalize_search_hit(raw: dict[str, Any]) -> dict[str, Any]:
    source = raw.get("_source") or {}
    return {
        "chebi_accession": source.get("chebi_accession"),
        "name": source.get("name"),
        "ascii_name": source.get("ascii_name"),
        "definition": source.get("definition"),
        "stars": source.get("stars"),
        "smiles": source.get("smiles"),
        "formula": source.get("formula"),
        "mass": source.get("mass"),
        "default_structure": source.get("default_structure"),
    }


def _normalize_compound(raw: dict[str, Any]) -> dict[str, Any]:
    names = raw.get("names") or {}
    relations = raw.get("ontology_relations") or {}
    incoming = relations.get("incoming_relations") or []
    outgoing = relations.get("outgoing_relations") or []
    synonyms = []
    for item in names.get("SYNONYM") or []:
        if isinstance(item, dict) and item.get("name") and item["name"] not in synonyms:
            synonyms.append(item["name"])
    return {
        "chebi_accession": raw.get("chebi_accession"),
        "name": raw.get("name"),
        "definition": raw.get("definition"),
        "ascii_name": raw.get("ascii_name"),
        "stars": raw.get("stars"),
        "formula": raw.get("formula"),
        "smiles": raw.get("smiles"),
        "mass": raw.get("mass"),
        "synonyms": synonyms[:10],
        "incoming_relation_count": len(incoming) if isinstance(incoming, list) else 0,
        "outgoing_relation_count": len(outgoing) if isinstance(outgoing, list) else 0,
    }


def search_compounds(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search ChEBI compounds by free-text query."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    data = get_json(
        f"{BASE_URL}/chebi/backend/api/public/es_search/",
        params={"query": clean_query, "size": max_results},
        timeout=30,
    )
    hits = (data.get("results") or [])[: max(1, min(int(max_results), 10))]
    records = [_normalize_search_hit(hit) for hit in hits if isinstance(hit, dict)]
    return {"query": clean_query, "count": len(records), "records": records}


def fetch_compound(chebi_id: str) -> dict[str, Any]:
    """Fetch a ChEBI compound by accession."""
    clean_id = chebi_id.strip()
    if not clean_id:
        raise ValueError("chebi_id is required")

    data = get_json(f"{BASE_URL}/chebi/backend/api/public/compound/{clean_id}/", timeout=30)
    return {"query": clean_id, "found": True, "count": 1, "records": [_normalize_compound(data)]}


SEARCH_COMPOUNDS_SPEC = ToolSpec(
    name="chebi.search_compounds",
    description="Search ChEBI compounds by free-text query.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search_compounds,
)


FETCH_COMPOUND_SPEC = ToolSpec(
    name="chebi.fetch_compound",
    description="Fetch a ChEBI compound by accession.",
    input_schema={
        "type": "object",
        "properties": {"chebi_id": {"type": "string"}},
        "required": ["chebi_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_compound,
)
