"""Open Targets GraphQL client."""
from __future__ import annotations

from typing import Any

from ._http import post_json
from .base import ToolSpec

ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"

SEARCH_QUERY = """
query Search($q: String!) {
  search(queryString: $q) {
    total
    hits {
      id
      entity
      object {
        ... on Target {
          approvedSymbol
          approvedName
          biotype
        }
      }
    }
  }
}
"""

TARGET_DISEASE_QUERY = """
query Target($id: String!) {
  target(ensemblId: $id) {
    id
    approvedSymbol
    approvedName
    associatedDiseases(page: { index: 0, size: 5 }) {
      count
      rows {
        disease { id name }
        score
        datasourceScores { id score }
      }
    }
  }
}
"""


def search(query: str) -> dict[str, Any]:
    """Search Open Targets for a target/disease/study term."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    data = post_json(ENDPOINT, {"query": SEARCH_QUERY, "variables": {"q": clean_query}}, timeout=60)
    if data.get("errors"):
        raise ValueError("; ".join(error.get("message", "unknown error") for error in data["errors"]))

    search_data = ((data.get("data") or {}).get("search") or {})
    hits = []
    for hit in (search_data.get("hits") or [])[:10]:
        obj = hit.get("object") or {}
        hits.append(
            {
                "id": hit.get("id"),
                "entity": hit.get("entity"),
                "approved_symbol": obj.get("approvedSymbol"),
                "approved_name": obj.get("approvedName"),
                "biotype": obj.get("biotype"),
            }
        )
    return {"query": clean_query, "count": len(hits), "total": search_data.get("total"), "hits": hits}


def fetch_target_diseases(ensembl_id: str) -> dict[str, Any]:
    """Fetch top disease associations for an Open Targets target."""
    clean_id = ensembl_id.strip()
    if not clean_id:
        raise ValueError("ensembl_id is required")

    data = post_json(ENDPOINT, {"query": TARGET_DISEASE_QUERY, "variables": {"id": clean_id}}, timeout=60)
    if data.get("errors"):
        raise ValueError("; ".join(error.get("message", "unknown error") for error in data["errors"]))

    target = ((data.get("data") or {}).get("target") or {})
    associations = ((target.get("associatedDiseases") or {}).get("rows") or [])
    rows = []
    for row in associations[:10]:
        rows.append(
            {
                "disease_id": (row.get("disease") or {}).get("id"),
                "disease_name": (row.get("disease") or {}).get("name"),
                "score": row.get("score"),
                "datasource_scores": row.get("datasourceScores") or [],
            }
        )
    return {
        "ensembl_id": target.get("id") or clean_id,
        "approved_symbol": target.get("approvedSymbol"),
        "approved_name": target.get("approvedName"),
        "count": len(rows),
        "record_count_available": ((target.get("associatedDiseases") or {}).get("count")),
        "records": rows,
    }


SEARCH_SPEC = ToolSpec(
    name="opentargets.search",
    description="Search Open Targets for target-oriented entities using the platform search endpoint.",
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search,
)


FETCH_TARGET_DISEASES_SPEC = ToolSpec(
    name="opentargets.fetch_target_diseases",
    description="Fetch top disease associations for an Open Targets target by Ensembl gene ID.",
    input_schema={
        "type": "object",
        "properties": {"ensembl_id": {"type": "string"}},
        "required": ["ensembl_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_target_diseases,
)
