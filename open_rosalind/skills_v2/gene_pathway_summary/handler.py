"""Gene pathway summary handler."""
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
    max_results = int(payload.get("max_results", 5) or 5)

    if not query:
        return {
            "annotation": {"kind": "gene_pathway_summary", "event_count": 0},
            "confidence": 0.0,
            "notes": ["Missing gene or pathway query"],
            "evidence": [],
            "gene_result": {},
            "pathway_result": {},
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

    symbol = str(gene_annotation.get("symbol") or query).strip()
    pathway_result = execute_skill_v2(
        "reactome_pathway_lookup",
        {"query": symbol, "species": "Homo sapiens", "max_results": max_results},
        trace=trace,
    )
    evidence.append({"step": "reactome_pathway_lookup", "result": pathway_result})

    pathway_annotation = pathway_result.get("annotation", {})
    return {
        "annotation": {
            "kind": "gene_pathway_summary",
            "symbol": symbol,
            "species": gene_annotation.get("species"),
            "ensembl_gene_id": gene_annotation.get("ensembl_gene_id"),
            "ncbi_gene_id": gene_annotation.get("ncbi_gene_id"),
            "pathway_stable_id": pathway_annotation.get("stable_id"),
            "pathway_name": pathway_annotation.get("name"),
            "event_count": pathway_annotation.get("event_count"),
            "literature_count": pathway_annotation.get("literature_count"),
        },
        "confidence": _confidence(gene_result, pathway_result),
        "notes": _merge_notes(gene_result.get("notes", []), pathway_result.get("notes", [])),
        "evidence": evidence,
        "gene_result": gene_result,
        "pathway_result": pathway_result,
        "trace": _trace_snapshot(trace),
    }
