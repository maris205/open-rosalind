"""Workflow skill: sequence analysis -> protein annotation summary."""
from __future__ import annotations

from typing import Any

from ..executor import execute_skill_v2
from ..runtime import ensure_trace


def _trace_snapshot(trace: Any) -> list[dict]:
    return list(getattr(trace, "events", []))


def handler(payload: dict, trace: Any) -> dict:
    sequence = payload.get("sequence", "").strip()
    if not sequence:
        return {
            "annotation": {"kind": "workflow", "workflow": "protein_annotation"},
            "confidence": 0.0,
            "notes": ["Empty sequence"],
            "evidence": [],
            "trace": [],
        }

    trace = ensure_trace(trace)
    notes: list[str] = []

    seq_result = execute_skill_v2("sequence_basic_analysis", {"sequence": sequence}, trace=trace)
    if seq_result.get("annotation", {}).get("primary_type") != "protein":
        notes.append("Primary sequence is not classified as protein")
        return {
            "annotation": {
                "kind": "workflow",
                "workflow": "protein_annotation",
                "primary_type": seq_result.get("annotation", {}).get("primary_type"),
            },
            "confidence": 0.3 if seq_result.get("annotation") else 0.0,
            "notes": notes + seq_result.get("notes", []),
            "evidence": [{"step": "sequence_basic_analysis", "result": seq_result}],
            "trace": _trace_snapshot(trace),
        }

    protein_query = sequence
    hint = seq_result.get("uniprot_hint") or {}
    top_match = hint.get("top_match")
    protein_payload = {"accession": top_match, "query": top_match or protein_query}
    protein_result = execute_skill_v2("protein_annotation_summary", protein_payload, trace=trace)

    notes.extend(seq_result.get("notes", []))
    notes.extend(protein_result.get("notes", []))

    return {
        "annotation": {
            "kind": "workflow",
            "workflow": "protein_annotation",
            "primary_type": seq_result.get("annotation", {}).get("primary_type"),
            "length": seq_result.get("annotation", {}).get("length"),
            "accession": protein_result.get("annotation", {}).get("accession"),
            "name": protein_result.get("annotation", {}).get("name"),
            "organism": protein_result.get("annotation", {}).get("organism"),
        },
        "confidence": round(
            min(
                max(seq_result.get("confidence", 0.0), protein_result.get("confidence", 0.0)),
                0.95,
            ),
            2,
        ),
        "notes": notes,
        "evidence": [
            {"step": "sequence_basic_analysis", "result": seq_result},
            {"step": "protein_annotation_summary", "result": protein_result},
        ],
        "sequence_result": seq_result,
        "protein_result": protein_result,
        "trace": _trace_snapshot(trace),
    }
