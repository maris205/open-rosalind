"""ClinVar search handler."""
from __future__ import annotations

from typing import Any

from ...tools import clinvar as clinvar_tools
from ..runtime import ensure_trace, is_error, run_tool


def _build_query(payload: dict[str, Any]) -> str:
    explicit_query = str(payload.get("query") or "").strip()
    if explicit_query:
        return explicit_query

    terms: list[str] = []
    gene_symbol = str(payload.get("gene_symbol") or "").strip()
    mutation = str(payload.get("mutation") or "").strip()
    disease = str(payload.get("disease") or "").strip()
    if gene_symbol:
        terms.append(f"{gene_symbol}[gene]")
    if mutation:
        terms.append(mutation)
    if disease:
        terms.append(disease)
    return " AND ".join(terms)


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = _build_query(payload)
    max_results = int(payload.get("max_results", 5) or 5)
    if not query:
        return {
            "annotation": {"kind": "clinvar", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing ClinVar query or gene/mutation inputs"],
            "clinvar": {"query": "", "count": 0, "records": []},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    if not str(payload.get("query") or "").strip():
        notes.append(f"Built ClinVar query {query!r} from structured inputs")

    result = run_tool(trace, "clinvar.search", clinvar_tools.search, query=query, max_results=max_results)
    if is_error(result):
        return {
            "annotation": {"kind": "clinvar", "query": query, "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"ClinVar search failed: {result['error']['message']}"],
            "clinvar": {"query": query, "count": 0, "records": []},
        }

    top_record = (result.get("records") or [{}])[0]
    germline = top_record.get("germline_classification") or {}
    oncogenicity = top_record.get("oncogenicity_classification") or {}
    clinical_impact = top_record.get("clinical_impact_classification") or {}
    return {
        "annotation": {
            "kind": "clinvar",
            "query": result.get("query", query),
            "n_records": result.get("count", 0),
            "accession": top_record.get("accession"),
            "gene": top_record.get("gene"),
            "protein_change": top_record.get("protein_change"),
            "germline_significance": germline.get("description"),
            "oncogenicity": oncogenicity.get("description"),
            "clinical_impact": clinical_impact.get("description"),
            "trait_names": (top_record.get("trait_names") or [])[:5],
        },
        "confidence": 0.85 if result.get("count", 0) > 0 else 0.0,
        "notes": notes,
        "clinvar": result,
    }
