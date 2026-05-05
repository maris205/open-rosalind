"""Mutation impact summary handler."""
from __future__ import annotations

from typing import Any

from ..executor import execute_skill_v2
from ..runtime import ensure_trace


def _trace_snapshot(trace: Any) -> list[dict]:
    return list(getattr(trace, "events", []))


def _merge_notes(*groups: list[str]) -> list[str]:
    notes: list[str] = []
    for group in groups:
        for note in group:
            if note not in notes:
                notes.append(note)
    return notes


def _average_nonzero(*values: float) -> float:
    non_zero = [value for value in values if value > 0]
    if not non_zero:
        return 0.0
    return round(min(sum(non_zero) / len(non_zero), 0.95), 2)


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    trace = ensure_trace(trace)

    mutation_payload = {
        key: value
        for key, value in payload.items()
        if key in {"wt", "mt", "wild_type", "mutant", "mutation", "gene_symbol", "query"}
    }
    mutation_result = execute_skill_v2("mutation_effect", mutation_payload, trace=trace)
    evidence = [{"step": "mutation_effect", "result": mutation_result}]

    mutation_annotation = mutation_result.get("annotation", {})
    mutation_confidence = float(mutation_result.get("confidence", 0.0))
    if mutation_confidence == 0.0:
        return {
            "annotation": {
                "kind": "mutation_impact_summary",
                "gene_symbol": mutation_annotation.get("gene_symbol"),
                "accession": mutation_annotation.get("accession"),
            },
            "confidence": 0.0,
            "notes": mutation_result.get("notes", []),
            "evidence": evidence,
            "mutation_result": mutation_result,
            "clinvar_result": {},
            "protein_result": {},
            "impact_summary": {},
            "trace": _trace_snapshot(trace),
        }

    clinvar_payload = {
        "gene_symbol": payload.get("gene_symbol"),
        "mutation": payload.get("mutation"),
        "query": payload.get("clinvar_query") or payload.get("query"),
    }
    clinvar_result = execute_skill_v2("clinvar_search", clinvar_payload, trace=trace)
    evidence.append({"step": "clinvar_search", "result": clinvar_result})

    protein_payload: dict[str, Any] = {}
    accession = mutation_annotation.get("accession")
    if accession:
        protein_payload = {"accession": accession}
    elif payload.get("gene_symbol"):
        protein_payload = {"query": payload["gene_symbol"]}

    protein_result: dict[str, Any] = {}
    if protein_payload:
        protein_result = execute_skill_v2("protein_annotation_summary", protein_payload, trace=trace)
        evidence.append({"step": "protein_annotation_summary", "result": protein_result})

    notes = _merge_notes(
        mutation_result.get("notes", []),
        clinvar_result.get("notes", []),
        protein_result.get("notes", []),
    )

    clinvar_annotation = clinvar_result.get("annotation", {})
    protein_annotation = protein_result.get("annotation", {})
    differences = (mutation_result.get("mutation") or {}).get("differences", [])
    impact_summary = {
        "overall_assessment": mutation_annotation.get("overall_assessment"),
        "categories": [diff.get("category") for diff in differences if diff.get("category")],
        "notable_flags": mutation_annotation.get("notable_flags") or [],
        "clinvar_support": {
            "germline_significance": clinvar_annotation.get("germline_significance"),
            "oncogenicity": clinvar_annotation.get("oncogenicity"),
            "clinical_impact": clinvar_annotation.get("clinical_impact"),
            "trait_names": clinvar_annotation.get("trait_names") or [],
        },
        "protein_context": {
            "name": protein_annotation.get("name"),
            "organism": protein_annotation.get("organism"),
            "function": protein_annotation.get("function"),
        },
    }

    return {
        "annotation": {
            "kind": "mutation_impact_summary",
            "gene_symbol": mutation_annotation.get("gene_symbol"),
            "accession": mutation_annotation.get("accession"),
            "protein_name": protein_annotation.get("name"),
            "mutation": payload.get("mutation"),
            "overall_assessment": mutation_annotation.get("overall_assessment"),
            "germline_significance": clinvar_annotation.get("germline_significance"),
            "oncogenicity": clinvar_annotation.get("oncogenicity"),
            "trait_names": clinvar_annotation.get("trait_names") or [],
        },
        "confidence": _average_nonzero(
            mutation_confidence,
            float(clinvar_result.get("confidence", 0.0)),
            float(protein_result.get("confidence", 0.0)),
        ),
        "notes": notes,
        "evidence": evidence,
        "mutation_result": mutation_result,
        "clinvar_result": clinvar_result,
        "protein_result": protein_result,
        "impact_summary": impact_summary,
        "trace": _trace_snapshot(trace),
    }
