"""CIViC GraphQL client."""
from __future__ import annotations

from typing import Any

from ._http import post_json
from .base import ToolSpec

ENDPOINT = "https://civicdb.org/api/graphql"

TYPEAHEAD_QUERY = """
query Typeahead($q: String!) {
  entityTypeahead(queryTerm: $q) {
    id
    name
    resultType
  }
}
"""

VARIANT_EVIDENCE_QUERY = """
query VariantEvidence($name: String!, $first: Int!) {
  variants(name: $name, first: $first) {
    nodes {
      id
      name
      feature { id name }
      evidenceItems(first: 5) {
        nodes {
          id
          description
          evidenceLevel
          evidenceType
          evidenceDirection
          significance
          disease { name }
          therapies { name }
        }
      }
    }
  }
}
"""


def typeahead(query: str) -> dict[str, Any]:
    """Resolve CIViC entities from a free-text typeahead query."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    data = post_json(ENDPOINT, {"query": TYPEAHEAD_QUERY, "variables": {"q": clean_query}}, timeout=60)
    if data.get("errors"):
        raise ValueError("; ".join(error.get("message", "unknown error") for error in data["errors"]))

    hits = ((data.get("data") or {}).get("entityTypeahead") or [])[:10]
    return {
        "query": clean_query,
        "count": len(hits),
        "records": [{"id": hit.get("id"), "name": hit.get("name"), "result_type": hit.get("resultType")} for hit in hits],
    }


def fetch_variant_evidence(variant_name: str, first: int = 3) -> dict[str, Any]:
    """Fetch CIViC variant evidence by variant name."""
    clean_name = variant_name.strip()
    if not clean_name:
        raise ValueError("name is required")

    data = post_json(ENDPOINT, {"query": VARIANT_EVIDENCE_QUERY, "variables": {"name": clean_name, "first": first}}, timeout=60)
    if data.get("errors"):
        raise ValueError("; ".join(error.get("message", "unknown error") for error in data["errors"]))

    nodes = (((data.get("data") or {}).get("variants") or {}).get("nodes") or [])[:first]
    records = []
    for node in nodes:
        evidence_items = (((node.get("evidenceItems") or {}).get("nodes")) or [])[:10]
        records.append(
            {
                "id": node.get("id"),
                "name": node.get("name"),
                "feature_name": (node.get("feature") or {}).get("name"),
                "evidence_items": [
                    {
                        "id": item.get("id"),
                        "description": item.get("description"),
                        "evidence_level": item.get("evidenceLevel"),
                        "evidence_type": item.get("evidenceType"),
                        "evidence_direction": item.get("evidenceDirection"),
                        "significance": item.get("significance"),
                        "disease_name": (item.get("disease") or {}).get("name"),
                        "therapies": [therapy.get("name") for therapy in (item.get("therapies") or [])[:5]],
                    }
                    for item in evidence_items
                ],
            }
        )
    return {"query": clean_name, "count": len(records), "records": records}


TYPEAHEAD_SPEC = ToolSpec(
    name="civic.typeahead",
    description="Resolve CIViC entities from a free-text typeahead query.",
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=typeahead,
)


VARIANT_EVIDENCE_SPEC = ToolSpec(
    name="civic.fetch_variant_evidence",
    description="Fetch CIViC variant evidence items by variant name.",
    input_schema={
        "type": "object",
        "properties": {
            "variant_name": {"type": "string"},
            "first": {"type": "integer", "default": 3, "minimum": 1, "maximum": 10},
        },
        "required": ["variant_name"],
    },
    output_schema={"type": "object"},
    handler=fetch_variant_evidence,
)
