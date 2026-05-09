"""PRIDE Archive client."""
from __future__ import annotations

from typing import Any

import requests

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://www.ebi.ac.uk/pride/ws/archive/v2"


def _normalize_project(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "accession": raw.get("accession"),
        "title": raw.get("title"),
        "doi": raw.get("doi"),
        "publication_date": raw.get("publicationDate"),
        "submission_date": raw.get("submissionDate"),
        "project_description": raw.get("projectDescription"),
        "organisms": raw.get("organisms") or [],
        "organism_parts": raw.get("organismParts") or [],
        "experiment_types": raw.get("experimentTypes") or [],
        "keywords": raw.get("keywords") or [],
        "total_file_downloads": raw.get("totalFileDownloads"),
    }


def search_projects(keyword: str, max_results: int = 5) -> dict[str, Any]:
    """Search PRIDE projects by keyword."""
    clean_keyword = keyword.strip()
    if not clean_keyword:
        raise ValueError("keyword is required")

    data = get_json(
        f"{BASE_URL}/projects",
        params={"keyword": clean_keyword, "pageSize": max(1, min(int(max_results), 10))},
        timeout=60,
    )
    records = [_normalize_project(item) for item in (data or [])[: max(1, min(int(max_results), 10))] if isinstance(item, dict)]
    return {"query": clean_keyword, "count": len(records), "records": records}


def fetch_project(accession: str) -> dict[str, Any]:
    """Fetch a PRIDE project by accession."""
    clean_accession = accession.strip().upper()
    if not clean_accession:
        raise ValueError("accession is required")

    try:
        data = get_json(f"{BASE_URL}/projects/{clean_accession}", timeout=60)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            return {"query": clean_accession, "found": False, "count": 0, "records": []}
        raise

    return {"query": clean_accession, "found": True, "count": 1, "records": [_normalize_project(data)]}


SEARCH_PROJECTS_SPEC = ToolSpec(
    name="pride.search_projects",
    description="Search PRIDE projects by keyword.",
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
        },
        "required": ["keyword"],
    },
    output_schema={"type": "object"},
    handler=search_projects,
)


FETCH_PROJECT_SPEC = ToolSpec(
    name="pride.fetch_project",
    description="Fetch a PRIDE project by accession.",
    input_schema={
        "type": "object",
        "properties": {"accession": {"type": "string"}},
        "required": ["accession"],
    },
    output_schema={"type": "object"},
    handler=fetch_project,
)
