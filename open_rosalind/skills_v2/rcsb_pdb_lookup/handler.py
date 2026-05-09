"""RCSB PDB lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import rcsb_pdb as rcsb_pdb_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    entry_id = str(payload.get("entry_id") or "").strip()
    max_results = int(payload.get("max_results", 5) or 5)

    if not query and not entry_id:
        return {
            "annotation": {"kind": "rcsb_pdb", "source": "RCSB PDB", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing query or entry_id"],
            "search": {"count": 0, "records": []},
            "pdb": {"found": False},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search_result = {"count": 0, "records": []}
    resolved_entry_id = entry_id

    if not resolved_entry_id:
        search_result = run_tool(
            trace,
            "rcsb_pdb.search_entries",
            rcsb_pdb_tools.search_entries,
            query=query,
            max_results=max_results,
        )
        if is_error(search_result):
            return {
                "annotation": {"kind": "rcsb_pdb", "source": "RCSB PDB", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"RCSB PDB search failed: {search_result['error']['message']}"],
                "search": {"count": 0, "records": []},
                "pdb": {"found": False},
            }
        top_hit = (search_result.get("records") or [{}])[0]
        resolved_entry_id = str(top_hit.get("entry_id") or "").strip()
        if not resolved_entry_id:
            return {
                "annotation": {"kind": "rcsb_pdb", "source": "RCSB PDB", "query": query, "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Could not resolve an RCSB PDB entry from query {query!r}"],
                "search": search_result,
                "pdb": {"found": False},
            }
        notes.append(f"Resolved query {query!r} to RCSB PDB entry {resolved_entry_id}")

    result = run_tool(
        trace,
        "rcsb_pdb.fetch_entry",
        rcsb_pdb_tools.fetch_entry,
        entry_id=resolved_entry_id,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "rcsb_pdb", "source": "RCSB PDB", "entry_id": resolved_entry_id, "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"RCSB PDB fetch failed: {result['error']['message']}"],
            "search": search_result,
            "pdb": {"found": False},
        }

    return {
        "annotation": {
            "kind": "rcsb_pdb",
            "source": "RCSB PDB",
            "entry_id": result.get("entry_id"),
            "title": result.get("title"),
            "experimental_method": (result.get("experimental_methods") or [None])[0],
            "resolution": result.get("resolution"),
            "polymer_entity_count": result.get("polymer_entity_count"),
            "n_records": 1 if result.get("found") else 0,
        },
        "confidence": 0.85 if result.get("found") else 0.0,
        "notes": notes,
        "search": search_result,
        "pdb": result,
    }
