"""ClinVar variation lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import clinvar_variation as clinvar_variation_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or payload.get("terms") or "").strip()
    refsnp_id = str(payload.get("refsnp_id") or "").strip()

    if not query and not refsnp_id:
        return {
            "annotation": {"kind": "clinvar_variation", "source": "ClinVar/dbSNP", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing variant query/terms or refsnp_id"],
            "search": {"query": "", "count": 0, "records": []},
            "refsnp": {},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search_result = {"query": query, "count": 0, "records": []}
    resolved_rsid = refsnp_id

    if query:
        search_result = run_tool(
            trace,
            "clinvar_variation.search_clinical_tables",
            clinvar_variation_tools.search_clinical_tables,
            terms=query,
            max_results=5,
        )
        if is_error(search_result):
            return {
                "annotation": {"kind": "clinvar_variation", "source": "ClinVar/dbSNP", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"ClinVar variation search failed: {search_result['error']['message']}"],
                "search": {"query": query, "count": 0, "records": []},
                "refsnp": {},
            }
        top_record = (search_result.get("records") or [{}])[0]
        top_identifier = str(top_record.get("identifier") or "")
        if top_identifier.lower().startswith("rs"):
            resolved_rsid = top_identifier
            notes.append(f"Resolved query {query!r} to RefSNP {resolved_rsid}")

    refsnp_result = {}
    if resolved_rsid:
        refsnp_result = run_tool(
            trace,
            "clinvar_variation.fetch_refsnp",
            clinvar_variation_tools.fetch_refsnp,
            refsnp_id=resolved_rsid,
        )
        if is_error(refsnp_result):
            return {
                "annotation": {"kind": "clinvar_variation", "source": "ClinVar/dbSNP", "query": query, "n_records": 0},
                "confidence": 0.0,
                "notes": notes + [f"RefSNP fetch failed: {refsnp_result['error']['message']}"],
                "search": search_result,
                "refsnp": {},
            }

    top_frequency = refsnp_result.get("top_frequency") or {}
    return {
        "annotation": {
            "kind": "clinvar_variation",
            "source": "ClinVar/dbSNP",
            "query": query or resolved_rsid,
            "n_records": search_result.get("count", 0),
            "refsnp_id": refsnp_result.get("refsnp_id"),
            "variant_type": refsnp_result.get("variant_type"),
            "anchor": refsnp_result.get("anchor"),
            "top_frequency_study": top_frequency.get("study_name"),
            "top_frequency_af": top_frequency.get("allele_frequency"),
        },
        "confidence": 0.8 if refsnp_result else (0.6 if search_result.get("count", 0) > 0 else 0.0),
        "notes": notes,
        "search": search_result,
        "refsnp": refsnp_result,
    }
