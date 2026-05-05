"""Pathway literature summary handler."""
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
    query = str(payload.get("query") or payload.get("stable_id") or "").strip()
    species = str(payload.get("species") or "Homo sapiens").strip() or "Homo sapiens"
    max_results = int(payload.get("max_results", 5) or 5)

    if not query:
        return {
            "annotation": {"kind": "pathway_literature_summary", "n_hits": 0},
            "confidence": 0.0,
            "notes": ["Missing pathway query or stable_id"],
            "evidence": [],
            "pathway_result": {},
            "literature_result": {},
            "trace": [],
        }

    trace = ensure_trace(trace)
    pathway_payload = {"stable_id": query} if query.startswith("R-") else {"query": query, "species": species}
    pathway_result = execute_skill_v2("reactome_pathway_lookup", pathway_payload, trace=trace)
    evidence = [{"step": "reactome_pathway_lookup", "result": pathway_result}]

    pathway_annotation = pathway_result.get("annotation", {})
    pathway_name = str(pathway_annotation.get("name") or query).strip()
    literature_query = f"{pathway_name} pathway"
    literature_result = execute_skill_v2(
        "literature_topic_summary",
        {"query": literature_query, "max_results": max_results},
        trace=trace,
    )
    evidence.append({"step": "literature_topic_summary", "result": literature_result})

    literature_annotation = literature_result.get("annotation", {})
    return {
        "annotation": {
            "kind": "pathway_literature_summary",
            "stable_id": pathway_annotation.get("stable_id"),
            "name": pathway_annotation.get("name"),
            "species": pathway_annotation.get("species"),
            "event_count": pathway_annotation.get("event_count"),
            "top_pmids": literature_annotation.get("top_pmids") or [],
            "n_hits": literature_annotation.get("n_hits", 0),
        },
        "confidence": _confidence(pathway_result, literature_result),
        "notes": _merge_notes(pathway_result.get("notes", []), literature_result.get("notes", [])),
        "evidence": evidence,
        "pathway_result": pathway_result,
        "literature_result": literature_result,
        "trace": _trace_snapshot(trace),
    }
