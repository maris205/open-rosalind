"""ClinicalTrials.gov study search handler."""
from __future__ import annotations

from typing import Any

from ...tools import clinicaltrials as clinicaltrials_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    condition = str(payload.get("condition") or payload.get("query") or "").strip()
    status = str(payload.get("status") or "").strip() or None
    max_results = int(payload.get("max_results", 5) or 5)

    if not condition:
        return {
            "annotation": {"kind": "clinical_trials", "source": "ClinicalTrials.gov", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing ClinicalTrials.gov condition or query"],
            "clinicaltrials": {"query": "", "count": 0, "records": []},
        }

    trace = ensure_trace(trace)
    result = run_tool(
        trace,
        "clinicaltrials.search_studies",
        clinicaltrials_tools.search_studies,
        condition=condition,
        status=status,
        max_results=max_results,
        page_size=min(max_results, 10),
        max_pages=1,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "clinical_trials", "source": "ClinicalTrials.gov", "query": condition, "n_records": 0},
            "confidence": 0.0,
            "notes": [f"ClinicalTrials.gov search failed: {result['error']['message']}"],
            "clinicaltrials": {"query": condition, "count": 0, "records": []},
        }

    top_record = (result.get("records") or [{}])[0]
    phases = top_record.get("phases") or []
    return {
        "annotation": {
            "kind": "clinical_trials",
            "source": "ClinicalTrials.gov",
            "query": result.get("query", condition),
            "n_records": result.get("count", 0),
            "nct_id": top_record.get("nct_id"),
            "title": top_record.get("brief_title") or top_record.get("official_title"),
            "overall_status": top_record.get("overall_status"),
            "phase": phases[0] if phases else None,
            "lead_sponsor": top_record.get("lead_sponsor"),
        },
        "confidence": 0.85 if result.get("count", 0) > 0 else 0.0,
        "notes": [],
        "clinicaltrials": result,
    }
