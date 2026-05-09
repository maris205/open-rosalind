"""ClinicalTrials.gov v2 client."""
from __future__ import annotations

from typing import Any

from ._http import make_session
from .base import ToolSpec

BASE_URL = "https://clinicaltrials.gov/api/v2"


def _normalize_status(status: str | None) -> str | None:
    if not status:
        return None
    clean = status.strip().upper().replace(" ", "_").replace("-", "_")
    return clean or None


def _location_summary(raw: dict[str, Any]) -> str | None:
    parts = [
        raw.get("facility"),
        raw.get("city"),
        raw.get("state"),
        raw.get("country"),
    ]
    text = ", ".join(part for part in parts if part)
    return text or None


def _normalize_study(raw: dict[str, Any]) -> dict[str, Any]:
    protocol = raw.get("protocolSection") or {}
    ident = protocol.get("identificationModule") or {}
    status = protocol.get("statusModule") or {}
    desc = protocol.get("descriptionModule") or {}
    design = protocol.get("designModule") or {}
    conditions = protocol.get("conditionsModule") or {}
    interventional = protocol.get("armsInterventionsModule") or {}
    sponsor = protocol.get("sponsorCollaboratorsModule") or {}
    contacts = protocol.get("contactsLocationsModule") or {}

    interventions = interventional.get("interventions") or []
    locations = contacts.get("locations") or []

    return {
        "nct_id": ident.get("nctId"),
        "brief_title": ident.get("briefTitle"),
        "official_title": ident.get("officialTitle"),
        "overall_status": status.get("overallStatus"),
        "study_type": design.get("studyType"),
        "phases": design.get("phases") or [],
        "conditions": conditions.get("conditions") or [],
        "interventions": [
            {
                "name": item.get("name"),
                "type": item.get("type"),
                "description": item.get("description"),
            }
            for item in interventions[:10]
            if isinstance(item, dict)
        ],
        "lead_sponsor": (sponsor.get("leadSponsor") or {}).get("name"),
        "brief_summary": desc.get("briefSummary"),
        "start_date": (status.get("startDateStruct") or {}).get("date"),
        "primary_completion_date": (status.get("primaryCompletionDateStruct") or {}).get("date"),
        "completion_date": (status.get("completionDateStruct") or {}).get("date"),
        "locations": [
            {
                "facility": item.get("facility"),
                "city": item.get("city"),
                "state": item.get("state"),
                "country": item.get("country"),
                "summary": _location_summary(item),
            }
            for item in locations[:10]
            if isinstance(item, dict)
        ],
        "url": f"https://clinicaltrials.gov/study/{ident.get('nctId')}" if ident.get("nctId") else None,
    }


def search_studies(
    condition: str,
    status: str | None = None,
    max_results: int = 10,
    page_size: int = 10,
    max_pages: int = 1,
) -> dict[str, Any]:
    """Search ClinicalTrials.gov studies by condition."""
    clean_condition = condition.strip()
    if not clean_condition:
        raise ValueError("condition is required")

    clean_status = _normalize_status(status)
    page_size = max(1, min(page_size, max_results))
    max_pages = max(1, max_pages)

    session = make_session()
    try:
        studies: list[dict[str, Any]] = []
        next_page_token: str | None = None
        total_count: int | None = None
        pages_fetched = 0

        while pages_fetched < max_pages and len(studies) < max_results:
            params: dict[str, Any] = {"query.cond": clean_condition, "pageSize": min(page_size, max_results - len(studies))}
            if clean_status:
                params["filter.overallStatus"] = clean_status
            if next_page_token:
                params["pageToken"] = next_page_token

            response = session.get(
                f"{BASE_URL}/studies",
                params=params,
                headers={"Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            pages_fetched += 1

            if isinstance(data.get("totalCount"), int):
                total_count = int(data["totalCount"])

            for item in data.get("studies") or []:
                if isinstance(item, dict):
                    studies.append(_normalize_study(item))
                    if len(studies) >= max_results:
                        break

            next_page_token = data.get("nextPageToken") if isinstance(data.get("nextPageToken"), str) else None
            if not next_page_token:
                break

        return {
            "query": clean_condition,
            "status": clean_status,
            "count": len(studies),
            "record_count_available": total_count if isinstance(total_count, int) else len(studies),
            "pages_fetched": pages_fetched,
            "next_page_token": next_page_token,
            "records": studies[:max_results],
        }
    finally:
        session.close()


SEARCH_STUDIES_SPEC = ToolSpec(
    name="clinicaltrials.search_studies",
    description="Search ClinicalTrials.gov studies by condition and optional overall status filter.",
    input_schema={
        "type": "object",
        "properties": {
            "condition": {"type": "string"},
            "status": {"type": "string"},
            "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            "page_size": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            "max_pages": {"type": "integer", "default": 1, "minimum": 1, "maximum": 5},
        },
        "required": ["condition"],
    },
    output_schema={"type": "object"},
    handler=search_studies,
)
