"""GO to pathway bridge handler."""
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
    query = str(payload.get("query") or payload.get("term_id") or "").strip()
    species = str(payload.get("species") or "Homo sapiens").strip() or "Homo sapiens"

    if not query:
        return {
            "annotation": {"kind": "go_pathway_bridge", "event_count": 0},
            "confidence": 0.0,
            "notes": ["Missing GO query or term_id"],
            "evidence": [],
            "go_result": {},
            "pathway_result": {},
            "trace": [],
        }

    trace = ensure_trace(trace)
    go_payload = {"term_id": query} if query.startswith("GO:") else {"query": query}
    go_result = execute_skill_v2("go_term_lookup", go_payload, trace=trace)
    evidence = [{"step": "go_term_lookup", "result": go_result}]

    term_name = str(go_result.get("annotation", {}).get("name") or query).strip()
    pathway_result = execute_skill_v2(
        "reactome_pathway_lookup",
        {"query": term_name, "species": species},
        trace=trace,
    )
    evidence.append({"step": "reactome_pathway_lookup", "result": pathway_result})

    go_annotation = go_result.get("annotation", {})
    pathway_annotation = pathway_result.get("annotation", {})
    return {
        "annotation": {
            "kind": "go_pathway_bridge",
            "term_id": go_annotation.get("term_id"),
            "term_name": go_annotation.get("name"),
            "aspect": go_annotation.get("aspect"),
            "pathway_stable_id": pathway_annotation.get("stable_id"),
            "pathway_name": pathway_annotation.get("name"),
            "event_count": pathway_annotation.get("event_count"),
        },
        "confidence": _confidence(go_result, pathway_result),
        "notes": _merge_notes(go_result.get("notes", []), pathway_result.get("notes", [])),
        "evidence": evidence,
        "go_result": go_result,
        "pathway_result": pathway_result,
        "trace": _trace_snapshot(trace),
    }
