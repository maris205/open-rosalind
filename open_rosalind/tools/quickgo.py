"""QuickGO REST client."""
from __future__ import annotations

from typing import Any

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://www.ebi.ac.uk/QuickGO/services/ontology/go"


def _normalize_term(raw: dict[str, Any]) -> dict[str, Any]:
    definition = raw.get("definition") or {}
    synonyms = raw.get("synonyms") or []
    children = raw.get("children") or []
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "aspect": raw.get("aspect"),
        "is_obsolete": bool(raw.get("isObsolete")),
        "definition": definition.get("text"),
        "usage": raw.get("usage"),
        "synonyms": [
            {"name": synonym.get("name"), "type": synonym.get("type")}
            for synonym in synonyms[:10]
        ],
        "child_terms": [
            {"id": child.get("id"), "relation": child.get("relation")}
            for child in children[:15]
        ],
    }


def search_terms(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search GO terms by free-text query."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    data = get_json(
        f"{BASE_URL}/search",
        params={"query": clean_query, "limit": max_results, "page": 1},
        timeout=30,
    )
    results = [_normalize_term(item) for item in data.get("results", [])[:max_results]]
    return {"query": clean_query, "count": len(results), "records": results}


def fetch_term(term_id: str) -> dict[str, Any]:
    """Fetch a GO term by accession."""
    clean_id = term_id.strip()
    if not clean_id:
        raise ValueError("term_id is required")

    data = get_json(f"{BASE_URL}/terms/{clean_id}", timeout=30)
    results = data.get("results") or []
    if not results:
        return {"id": clean_id, "found": False}
    normalized = _normalize_term(results[0])
    normalized["found"] = True
    return normalized


SEARCH_TERMS_SPEC = ToolSpec(
    name="quickgo.search_terms",
    description="Search Gene Ontology terms by free-text query using QuickGO.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search_terms,
)


FETCH_TERM_SPEC = ToolSpec(
    name="quickgo.fetch_term",
    description="Fetch a Gene Ontology term by GO accession (e.g. GO:0006915).",
    input_schema={
        "type": "object",
        "properties": {"term_id": {"type": "string"}},
        "required": ["term_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_term,
)
