"""Gene GO summary handler."""
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
    query = str(payload.get("query") or payload.get("gene_symbol") or payload.get("symbol") or "").strip()
    species = str(payload.get("species") or "homo_sapiens").strip() or "homo_sapiens"

    if not query:
        return {
            "annotation": {"kind": "gene_go_summary", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing gene query"],
            "evidence": [],
            "gene_result": {},
            "go_result": {},
            "trace": [],
        }

    trace = ensure_trace(trace)
    gene_result = execute_skill_v2(
        "gene_cross_reference",
        {"query": query, "species": species},
        trace=trace,
    )
    evidence = [{"step": "gene_cross_reference", "result": gene_result}]

    gene_annotation = gene_result.get("annotation", {})
    go_query = f"{gene_annotation.get('symbol') or query} biological process"
    go_result = execute_skill_v2("go_term_lookup", {"query": go_query}, trace=trace)
    evidence.append({"step": "go_term_lookup", "result": go_result})

    go_annotation = go_result.get("annotation", {})
    return {
        "annotation": {
            "kind": "gene_go_summary",
            "symbol": gene_annotation.get("symbol") or query,
            "species": gene_annotation.get("species"),
            "ensembl_gene_id": gene_annotation.get("ensembl_gene_id"),
            "ncbi_gene_id": gene_annotation.get("ncbi_gene_id"),
            "term_id": go_annotation.get("term_id"),
            "term_name": go_annotation.get("name"),
            "aspect": go_annotation.get("aspect"),
            "n_child_terms": go_annotation.get("n_child_terms"),
        },
        "confidence": _confidence(gene_result, go_result),
        "notes": _merge_notes(gene_result.get("notes", []), go_result.get("notes", [])),
        "evidence": evidence,
        "gene_result": gene_result,
        "go_result": go_result,
        "trace": _trace_snapshot(trace),
    }
