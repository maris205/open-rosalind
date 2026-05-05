"""UniProt entry fetch handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace, is_error, run_tool
from ..uniprot import tools


def handler(payload: dict, trace: Any) -> dict:
    accession = payload.get("accession", "").strip()
    if not accession:
        return {
            "annotation": {"kind": "protein"},
            "confidence": 0.0,
            "notes": ["Missing accession"],
            "entry": {},
        }

    trace = ensure_trace(trace)
    result = run_tool(trace, "uniprot.fetch", tools.fetch, accession=accession)
    if is_error(result):
        return {
            "annotation": {"kind": "protein"},
            "confidence": 0.0,
            "notes": [f"UniProt fetch failed: {result['error']['message']}"],
            "entry": {},
        }

    return {
        "annotation": {
            "kind": "protein",
            "accession": result.get("accession"),
            "name": result.get("name"),
            "organism": result.get("organism"),
            "length": result.get("length"),
        },
        "confidence": 0.95,
        "notes": [],
        "entry": result,
    }
