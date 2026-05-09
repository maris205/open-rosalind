"""Bgee SPARQL client for expression lookups."""
from __future__ import annotations

from typing import Any

from ._http import make_session
from .base import ToolSpec

ENDPOINT = "https://www.bgee.org/sparql/"

QUERY_TEMPLATE = """
PREFIX orth: <http://purl.org/net/orth#>
PREFIX genex: <http://purl.org/genex#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT DISTINCT ?anat ?anatName ?score {
  ?seq a orth:Gene .
  ?seq dcterms:identifier "%(ensembl_id)s" .
  ?expression a genex:Expression .
  ?expression genex:hasExpressionCondition ?condition .
  ?expression genex:hasExpressionLevel ?score .
  ?expression genex:hasSequenceUnit ?seq .
  ?condition genex:hasAnatomicalEntity ?anat .
  ?anat rdfs:label ?anatName .
  FILTER (?anat != obo:GO_0005575)
}
ORDER BY DESC(?score)
LIMIT %(limit)s
"""


def _obo_id(uri: str | None) -> str | None:
    if not uri:
        return None
    return uri.rstrip("/").rsplit("/", 1)[-1]


def _binding_value(binding: dict[str, Any], key: str) -> str | None:
    value = binding.get(key)
    if not isinstance(value, dict):
        return None
    raw = value.get("value")
    return str(raw) if raw is not None else None


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def lookup_expression(ensembl_id: str, max_results: int = 5) -> dict[str, Any]:
    """Fetch top Bgee expression calls for a stable Ensembl gene identifier."""
    clean_id = ensembl_id.strip()
    if not clean_id:
        raise ValueError("ensembl_id is required")

    limit = max(1, min(int(max_results), 20))
    query = QUERY_TEMPLATE % {"ensembl_id": clean_id, "limit": limit}

    session = make_session()
    try:
        response = session.get(
            ENDPOINT,
            params={"query": query, "format": "json"},
            headers={"Accept": "application/sparql-results+json"},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
    finally:
        session.close()

    results = data.get("results") or {}
    bindings = results.get("bindings") or []
    records = []
    for binding in bindings[:limit]:
        if not isinstance(binding, dict):
            continue
        records.append(
            {
                "anatomical_entity_id": _obo_id(_binding_value(binding, "anat")),
                "anatomical_entity_name": _binding_value(binding, "anatName"),
                "expression_score": _to_float(_binding_value(binding, "score")),
            }
        )

    return {
        "query": clean_id,
        "ensembl_id": clean_id,
        "count": len(records),
        "records": records,
    }


LOOKUP_EXPRESSION_SPEC = ToolSpec(
    name="bgee.lookup_expression",
    description="Fetch top Bgee anatomical expression calls by stable Ensembl gene identifier.",
    input_schema={
        "type": "object",
        "properties": {
            "ensembl_id": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["ensembl_id"],
    },
    output_schema={"type": "object"},
    handler=lookup_expression,
)
