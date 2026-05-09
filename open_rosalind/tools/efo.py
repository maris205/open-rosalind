"""EFO / OLS4 client for ontology term lookups."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://www.ebi.ac.uk/ols4/api"


def _term_iri(term_id: str) -> str:
    clean = term_id.strip()
    if not clean:
        raise ValueError("term_id is required")
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean
    return f"http://www.ebi.ac.uk/efo/{clean.replace(':', '_')}"


def _encode_iri(iri: str) -> str:
    return quote(quote(iri, safe=""), safe="")


def _normalize_term(raw: dict[str, Any]) -> dict[str, Any]:
    descriptions = raw.get("description") or []
    synonyms = []
    for key in ("exact_synonyms", "related_synonyms", "synonyms"):
        for item in raw.get(key) or []:
            if item and item not in synonyms:
                synonyms.append(item)
    return {
        "iri": raw.get("iri"),
        "label": raw.get("label"),
        "obo_id": raw.get("obo_id"),
        "short_form": raw.get("short_form"),
        "ontology_prefix": raw.get("ontology_prefix"),
        "description": descriptions[0] if descriptions else None,
        "synonyms": synonyms[:10],
        "is_obsolete": raw.get("is_obsolete"),
        "has_children": raw.get("has_children"),
    }


def search_terms(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search EFO terms by free-text query."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    data = get_json(f"{BASE_URL}/search", params={"q": clean_query, "ontology": "efo"}, timeout=30)
    docs = (((data.get("response") or {}).get("docs")) or [])[: max(1, min(int(max_results), 10))]
    records = [_normalize_term(doc) for doc in docs if isinstance(doc, dict)]
    return {"query": clean_query, "count": len(records), "records": records}


def fetch_term(term_id: str) -> dict[str, Any]:
    """Fetch an EFO term by IRI or compact identifier."""
    iri = _term_iri(term_id)
    data = get_json(f"{BASE_URL}/ontologies/efo/terms/{_encode_iri(iri)}", timeout=30)
    return {"query": term_id.strip(), "found": True, "count": 1, "records": [_normalize_term(data)]}


SEARCH_TERMS_SPEC = ToolSpec(
    name="efo.search_terms",
    description="Search EFO terms by free-text query using OLS4.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search_terms,
)


FETCH_TERM_SPEC = ToolSpec(
    name="efo.fetch_term",
    description="Fetch an EFO term by IRI or compact identifier.",
    input_schema={
        "type": "object",
        "properties": {"term_id": {"type": "string"}},
        "required": ["term_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_term,
)
