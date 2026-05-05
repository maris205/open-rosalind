"""Reactome ContentService client."""
from __future__ import annotations

import re
from typing import Any

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://reactome.org/ContentService"
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str | None) -> str | None:
    if not text:
        return text
    return _TAG_RE.sub("", text)


def search_pathways(query: str, species: str = "Homo sapiens", max_results: int = 5) -> dict[str, Any]:
    """Search Reactome pathways by free-text query."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    data = get_json(
        f"{BASE_URL}/search/query",
        params={
            "query": clean_query,
            "species": species,
            "types": "Pathway",
            "cluster": "true",
        },
        timeout=30,
    )
    records: list[dict[str, Any]] = []
    for group in data.get("results", []):
        for entry in group.get("entries", []):
            records.append(
                {
                    "db_id": entry.get("dbId"),
                    "st_id": entry.get("stId") or entry.get("id"),
                    "name": _strip_html(entry.get("name")),
                    "species": entry.get("species") or [],
                    "summary": _strip_html(entry.get("summation")),
                    "is_disease": bool(entry.get("isDisease") or entry.get("disease")),
                    "has_diagram": bool(entry.get("hasEHLD") or entry.get("hasDiagram")),
                    "url": f"https://reactome.org/content/detail/{entry.get('stId') or entry.get('id')}",
                }
            )
            if len(records) >= max_results:
                break
        if len(records) >= max_results:
            break

    return {
        "query": clean_query,
        "species": species,
        "count": len(records),
        "records": records,
    }


def fetch_pathway(stable_id: str) -> dict[str, Any]:
    """Fetch a Reactome pathway record by stable ID."""
    clean_id = stable_id.strip()
    if not clean_id:
        raise ValueError("stable_id is required")

    data = get_json(f"{BASE_URL}/data/query/{clean_id}", timeout=30)
    literature = data.get("literatureReference") or []
    events = data.get("hasEvent") or []
    orthologs = data.get("orthologousEvent") or []
    summary_blocks = data.get("summation") or []
    cross_references = data.get("crossReference") or []
    review_status = data.get("reviewStatus") or {}

    return {
        "db_id": data.get("dbId"),
        "st_id": data.get("stId") or clean_id,
        "display_name": data.get("displayName"),
        "species": data.get("speciesName"),
        "summary": _strip_html(summary_blocks[0].get("text")) if summary_blocks else None,
        "is_in_disease": bool(data.get("isInDisease")),
        "release_date": data.get("releaseDate"),
        "last_updated_date": data.get("lastUpdatedDate"),
        "review_status": review_status.get("definition") or review_status.get("displayName"),
        "has_diagram": bool(data.get("hasDiagram") or data.get("hasEHLD")),
        "event_count": len(events),
        "events": [
            {
                "st_id": event.get("stId"),
                "name": event.get("displayName"),
                "category": event.get("category"),
                "class_name": event.get("className"),
            }
            for event in events[:10]
        ],
        "literature": [
            {
                "title": ref.get("title"),
                "journal": ref.get("journal"),
                "year": ref.get("year"),
                "pmid": str(ref.get("pubMedIdentifier")) if ref.get("pubMedIdentifier") is not None else None,
                "url": ref.get("url"),
            }
            for ref in literature[:10]
        ],
        "ortholog_species": [event.get("speciesName") for event in orthologs[:10] if event.get("speciesName")],
        "cross_references": [
            {
                "database": ref.get("databaseName"),
                "identifier": ref.get("identifier"),
                "url": ref.get("url"),
            }
            for ref in cross_references[:10]
        ],
        "url": f"https://reactome.org/content/detail/{data.get('stId') or clean_id}",
    }


SEARCH_PATHWAYS_SPEC = ToolSpec(
    name="reactome.search_pathways",
    description="Search Reactome pathways by free-text query and species.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "species": {"type": "string", "default": "Homo sapiens"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search_pathways,
)


FETCH_PATHWAY_SPEC = ToolSpec(
    name="reactome.fetch_pathway",
    description="Fetch a detailed Reactome pathway record by stable ID (e.g. R-HSA-69541).",
    input_schema={
        "type": "object",
        "properties": {"stable_id": {"type": "string"}},
        "required": ["stable_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_pathway,
)
