"""Workflow skill: mutation assessment -> protein annotation -> literature."""
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


def _build_protein_payload(payload: dict[str, Any], mutation_result: dict[str, Any]) -> dict[str, Any]:
    context = mutation_result.get("protein_context") or {}
    accession = context.get("accession")
    if accession:
        return {"accession": accession}

    gene_symbol = str(payload.get("gene_symbol") or context.get("gene_symbol") or "").strip()
    if gene_symbol:
        return {"query": gene_symbol}

    query = str(payload.get("query") or "").strip()
    if query:
        return {"query": query}
    return {}


def _build_literature_query(
    payload: dict[str, Any],
    mutation_result: dict[str, Any],
    protein_result: dict[str, Any],
) -> str:
    raw_query = str(payload.get("query") or "").strip()
    if raw_query:
        return raw_query

    gene_symbol = str(
        payload.get("gene_symbol")
        or mutation_result.get("protein_context", {}).get("gene_symbol")
        or ""
    ).strip()
    accession = str(
        mutation_result.get("protein_context", {}).get("accession")
        or protein_result.get("annotation", {}).get("accession")
        or ""
    ).strip()
    mutation = str(payload.get("mutation") or "").strip()

    terms = [term for term in (gene_symbol, accession, mutation) if term]
    if not terms:
        return ""
    return " ".join(terms + ["mutation pathogenicity"])


def _workflow_confidence(*results: dict[str, Any]) -> float:
    values = [float(result.get("confidence", 0.0)) for result in results if result]
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

    mutation_payload_result = mutation_result.get("mutation") or {}
    if mutation_result.get("confidence", 0.0) == 0.0 or mutation_payload_result.get("error"):
        return {
            "annotation": {
                "kind": "workflow",
                "workflow": "mutation_assessment",
                "gene_symbol": mutation_result.get("annotation", {}).get("gene_symbol"),
                "accession": mutation_result.get("annotation", {}).get("accession"),
                "n_differences": mutation_result.get("annotation", {}).get("n_differences"),
                "overall_assessment": mutation_result.get("annotation", {}).get("overall_assessment"),
            },
            "confidence": 0.0,
            "notes": mutation_result.get("notes", []),
            "evidence": evidence,
            "mutation_result": mutation_result,
            "protein_result": {},
            "literature_result": {},
            "trace": _trace_snapshot(trace),
        }

    protein_payload = _build_protein_payload(payload, mutation_result)
    protein_result: dict[str, Any] = {}
    notes = list(mutation_result.get("notes", []))
    if protein_payload:
        protein_result = execute_skill_v2("protein_annotation_summary", protein_payload, trace=trace)
        evidence.append({"step": "protein_annotation_summary", "result": protein_result})
        notes = _merge_notes(notes, protein_result.get("notes", []))
    else:
        notes.append("Skipped protein annotation because no gene symbol or accession was available")

    literature_query = _build_literature_query(payload, mutation_result, protein_result)
    literature_result: dict[str, Any] = {}
    if literature_query:
        literature_result = execute_skill_v2(
            "literature_search",
            {"query": literature_query},
            trace=trace,
        )
        evidence.append({"step": "literature_search", "result": literature_result})
        notes = _merge_notes(notes, literature_result.get("notes", []))
    else:
        notes.append("Skipped literature search because no grounded mutation query could be built")

    mutation_annotation = mutation_result.get("annotation", {})
    protein_annotation = protein_result.get("annotation", {})
    literature_annotation = literature_result.get("annotation", {})

    return {
        "annotation": {
            "kind": "workflow",
            "workflow": "mutation_assessment",
            "gene_symbol": mutation_annotation.get("gene_symbol"),
            "accession": mutation_annotation.get("accession") or protein_annotation.get("accession"),
            "protein_name": protein_annotation.get("name"),
            "organism": protein_annotation.get("organism"),
            "mutation": payload.get("mutation"),
            "n_differences": mutation_annotation.get("n_differences"),
            "overall_assessment": mutation_annotation.get("overall_assessment"),
            "literature_hits": literature_annotation.get("n_hits"),
        },
        "confidence": _workflow_confidence(mutation_result, protein_result, literature_result),
        "notes": notes,
        "evidence": evidence,
        "mutation_result": mutation_result,
        "protein_result": protein_result,
        "literature_result": literature_result,
        "trace": _trace_snapshot(trace),
    }
