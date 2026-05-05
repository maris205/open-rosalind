"""Mutation gene context handler."""
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
    trace = ensure_trace(trace)
    mutation_result = execute_skill_v2("mutation_effect", payload, trace=trace)
    evidence = [{"step": "mutation_effect", "result": mutation_result}]

    mutation_annotation = mutation_result.get("annotation", {})
    gene_symbol = str(
        payload.get("gene_symbol")
        or mutation_annotation.get("gene_symbol")
        or ""
    ).strip()

    gene_result: dict[str, Any] = {}
    if gene_symbol:
        gene_result = execute_skill_v2("gene_cross_reference", {"query": gene_symbol}, trace=trace)
        evidence.append({"step": "gene_cross_reference", "result": gene_result})

    gene_annotation = gene_result.get("annotation", {})
    protein_context = mutation_result.get("protein_context") or {}
    return {
        "annotation": {
            "kind": "mutation_gene_context",
            "gene_symbol": mutation_annotation.get("gene_symbol") or gene_annotation.get("symbol"),
            "accession": mutation_annotation.get("accession") or protein_context.get("accession"),
            "ensembl_gene_id": gene_annotation.get("ensembl_gene_id"),
            "ncbi_gene_id": gene_annotation.get("ncbi_gene_id"),
            "canonical_transcript": gene_annotation.get("canonical_transcript"),
            "mutation": payload.get("mutation"),
            "overall_assessment": mutation_annotation.get("overall_assessment"),
            "n_differences": mutation_annotation.get("n_differences"),
        },
        "confidence": _confidence(mutation_result, gene_result),
        "notes": _merge_notes(mutation_result.get("notes", []), gene_result.get("notes", [])),
        "evidence": evidence,
        "mutation_result": mutation_result,
        "gene_result": gene_result,
        "trace": _trace_snapshot(trace),
    }
