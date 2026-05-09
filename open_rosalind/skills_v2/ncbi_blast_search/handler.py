"""NCBI BLAST search handler."""
from __future__ import annotations

from typing import Any

from ...tools import ncbi_blast as ncbi_blast_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    program = str(payload.get("program") or "").strip()
    database = str(payload.get("database") or "").strip()
    query_fasta = str(payload.get("query_fasta") or "").strip()
    email = str(payload.get("email") or "").strip() or None
    max_hits = int(payload.get("max_hits", 5) or 5)
    max_queries = int(payload.get("max_queries", 5) or 5)
    wait_timeout_sec = int(payload.get("wait_timeout_sec", 900) or 900)

    if not program or not database or not query_fasta:
        return {
            "annotation": {"kind": "ncbi_blast", "source": "NCBI BLAST", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing program, database, or query_fasta"],
            "blast": {"status": "INVALID", "has_hits": False, "query_summaries": []},
        }

    trace = ensure_trace(trace)
    result = run_tool(
        trace,
        "ncbi_blast.run_search",
        ncbi_blast_tools.run_search,
        program=program,
        database=database,
        query_fasta=query_fasta,
        email=email,
        max_hits=max_hits,
        max_queries=max_queries,
        wait_timeout_sec=wait_timeout_sec,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "ncbi_blast", "source": "NCBI BLAST", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"NCBI BLAST search failed: {result['error']['message']}"],
            "blast": {"status": "ERROR", "has_hits": False, "query_summaries": []},
        }

    top_query = (result.get("query_summaries") or [{}])[0]
    top_hit = (top_query.get("top_hits") or [{}])[0]
    notes: list[str] = []
    status = result.get("status")
    if status == "WAITING":
        notes.append("BLAST request was submitted but did not finish within wait_timeout_sec")

    confidence = 0.0
    if status == "READY" and result.get("has_hits"):
        confidence = 0.8
    elif status == "WAITING":
        confidence = 0.25

    return {
        "annotation": {
            "kind": "ncbi_blast",
            "source": "NCBI BLAST",
            "rid": result.get("rid"),
            "status": status,
            "program": result.get("program"),
            "database": result.get("database"),
            "top_accession": top_hit.get("accession"),
            "top_title": top_hit.get("title"),
            "top_evalue": top_hit.get("evalue"),
            "n_records": top_query.get("hit_count_returned", 0),
        },
        "confidence": confidence,
        "notes": notes,
        "blast": result,
    }
