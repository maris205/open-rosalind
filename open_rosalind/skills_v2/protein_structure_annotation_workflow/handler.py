"""Protein structure annotation workflow handler."""
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


def _confidence(*results: dict[str, Any]) -> float:
    values = [float(result.get("confidence", 0.0)) for result in results if result]
    values = [value for value in values if value > 0]
    if not values:
        return 0.0
    return round(min(sum(values) / len(values), 0.95), 2)


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    accession = str(payload.get("accession") or "").strip()

    if not query and not accession:
        return {
            "annotation": {"kind": "workflow", "workflow": "protein_structure_annotation"},
            "confidence": 0.0,
            "notes": ["Missing protein query or accession"],
            "evidence": [],
            "protein_result": {},
            "structure_result": {},
            "trace": [],
        }

    trace = ensure_trace(trace)
    protein_payload = {"accession": accession, "query": query}
    protein_result = execute_skill_v2("protein_annotation_summary", protein_payload, trace=trace)
    evidence = [{"step": "protein_annotation_summary", "result": protein_result}]

    resolved_accession = str(
        protein_result.get("annotation", {}).get("accession")
        or accession
        or ""
    ).strip()
    structure_result = execute_skill_v2(
        "protein_structure_summary",
        {"accession": resolved_accession, "query": query or resolved_accession},
        trace=trace,
    )
    evidence.append({"step": "protein_structure_summary", "result": structure_result})

    protein_annotation = protein_result.get("annotation", {})
    structure_annotation = structure_result.get("annotation", {})
    return {
        "annotation": {
            "kind": "workflow",
            "workflow": "protein_structure_annotation",
            "accession": protein_annotation.get("accession") or structure_annotation.get("accession"),
            "name": protein_annotation.get("name") or structure_annotation.get("name"),
            "organism": protein_annotation.get("organism") or structure_annotation.get("organism"),
            "length": protein_annotation.get("length") or structure_annotation.get("length"),
            "model_id": structure_annotation.get("model_id"),
            "mean_plddt": structure_annotation.get("mean_plddt"),
            "n_models": structure_annotation.get("n_models"),
        },
        "confidence": _confidence(protein_result, structure_result),
        "notes": _merge_notes(protein_result.get("notes", []), structure_result.get("notes", [])),
        "evidence": evidence,
        "protein_result": protein_result,
        "structure_result": structure_result,
        "trace": _trace_snapshot(trace),
    }
