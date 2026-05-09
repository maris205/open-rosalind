"""PharmGKB clinical annotation handler."""
from __future__ import annotations

from typing import Any

from ...tools import pharmgkb as pharmgkb_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    chemical_name = str(payload.get("chemical_name") or "").strip()
    gene_symbol = str(payload.get("gene_symbol") or "").strip()
    variant_symbol = str(payload.get("variant_symbol") or "").strip()
    accession_id = str(payload.get("accession_id") or "").strip()
    annotation_id = payload.get("annotation_id")
    max_results = int(payload.get("max_results", 5) or 5)

    if not any([chemical_name, gene_symbol, variant_symbol, accession_id, annotation_id is not None]):
        return {
            "annotation": {"kind": "pharmgkb_clinical_annotation", "source": "PharmGKB", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing chemical_name, gene_symbol, variant_symbol, accession_id, or annotation_id"],
            "search": {"count": 0, "records": []},
            "pharmgkb": {"found": False},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search_result = {"count": 0, "records": []}
    resolved_accession_id = accession_id
    resolved_annotation_id = annotation_id

    if not resolved_accession_id and resolved_annotation_id is None:
        search_result = run_tool(
            trace,
            "pharmgkb.search_clinical_annotations",
            pharmgkb_tools.search_clinical_annotations,
            chemical_name=chemical_name or None,
            gene_symbol=gene_symbol or None,
            variant_symbol=variant_symbol or None,
            max_results=max_results,
        )
        if is_error(search_result):
            return {
                "annotation": {"kind": "pharmgkb_clinical_annotation", "source": "PharmGKB", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"PharmGKB search failed: {search_result['error']['message']}"],
                "search": {"count": 0, "records": []},
                "pharmgkb": {"found": False},
            }
        top_hit = (search_result.get("records") or [{}])[0]
        resolved_accession_id = str(top_hit.get("accession_id") or "").strip()
        resolved_annotation_id = top_hit.get("id")
        if not resolved_accession_id and resolved_annotation_id is None:
            return {
                "annotation": {"kind": "pharmgkb_clinical_annotation", "source": "PharmGKB", "n_records": 0},
                "confidence": 0.0,
                "notes": ["No PharmGKB clinical annotations matched the query"],
                "search": search_result,
                "pharmgkb": {"found": False},
            }
        notes.append("Resolved query to top PharmGKB clinical annotation hit")

    result = run_tool(
        trace,
        "pharmgkb.fetch_clinical_annotation",
        pharmgkb_tools.fetch_clinical_annotation,
        annotation_id=resolved_annotation_id,
        accession_id=resolved_accession_id or None,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "pharmgkb_clinical_annotation", "source": "PharmGKB", "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"PharmGKB detail fetch failed: {result['error']['message']}"],
            "search": search_result,
            "pharmgkb": {"found": False},
        }

    return {
        "annotation": {
            "kind": "pharmgkb_clinical_annotation",
            "source": "PharmGKB",
            "annotation_id": result.get("id"),
            "accession_id": result.get("accession_id"),
            "name": result.get("name"),
            "level_of_evidence": result.get("level_of_evidence"),
            "gene_symbol": (result.get("gene_symbols") or [None])[0],
            "chemical_name": (result.get("chemical_names") or [None])[0],
            "variant_symbol": result.get("variant_symbol"),
            "n_allele_phenotypes": len(result.get("allele_phenotypes") or []),
            "n_records": 1 if result.get("found") else 0,
        },
        "confidence": 0.85 if result.get("found") else 0.0,
        "notes": notes,
        "search": search_result,
        "pharmgkb": result,
    }
