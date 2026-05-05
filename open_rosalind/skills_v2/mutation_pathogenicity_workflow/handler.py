"""Mutation pathogenicity workflow handler."""
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
    mutation_result = execute_skill_v2("mutation_impact_summary", payload, trace=trace)
    evidence = [{"step": "mutation_impact_summary", "result": mutation_result}]

    mutation_annotation = mutation_result.get("annotation", {})
    if float(mutation_result.get("confidence", 0.0)) == 0.0:
        return {
            "annotation": {
                "kind": "workflow",
                "workflow": "mutation_pathogenicity",
                "gene_symbol": mutation_annotation.get("gene_symbol"),
                "accession": mutation_annotation.get("accession"),
            },
            "confidence": 0.0,
            "notes": mutation_result.get("notes", []),
            "evidence": evidence,
            "mutation_result": mutation_result,
            "literature_result": {},
            "trace": _trace_snapshot(trace),
        }

    query_terms = [
        str(payload.get("gene_symbol") or mutation_annotation.get("gene_symbol") or "").strip(),
        str(payload.get("mutation") or mutation_annotation.get("mutation") or "").strip(),
        "pathogenicity",
    ]
    literature_query = " ".join(term for term in query_terms if term)
    literature_result = execute_skill_v2(
        "literature_topic_summary",
        {"query": literature_query, "max_results": int(payload.get("max_results", 5) or 5)},
        trace=trace,
    )
    evidence.append({"step": "literature_topic_summary", "result": literature_result})

    literature_annotation = literature_result.get("annotation", {})
    return {
        "annotation": {
            "kind": "workflow",
            "workflow": "mutation_pathogenicity",
            "gene_symbol": mutation_annotation.get("gene_symbol"),
            "accession": mutation_annotation.get("accession"),
            "protein_name": mutation_annotation.get("protein_name"),
            "mutation": mutation_annotation.get("mutation"),
            "overall_assessment": mutation_annotation.get("overall_assessment"),
            "germline_significance": mutation_annotation.get("germline_significance"),
            "oncogenicity": mutation_annotation.get("oncogenicity"),
            "top_pmids": literature_annotation.get("top_pmids") or [],
            "n_hits": literature_annotation.get("n_hits", 0),
        },
        "confidence": _confidence(mutation_result, literature_result),
        "notes": _merge_notes(mutation_result.get("notes", []), literature_result.get("notes", [])),
        "evidence": evidence,
        "mutation_result": mutation_result,
        "literature_result": literature_result,
        "trace": _trace_snapshot(trace),
    }
