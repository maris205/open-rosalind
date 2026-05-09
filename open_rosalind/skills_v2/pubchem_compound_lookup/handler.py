"""PubChem compound lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import pubchem as pubchem_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    cid = payload.get("cid")

    if not query and cid is None:
        return {
            "annotation": {"kind": "pubchem_compound", "source": "PubChem", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing query or cid"],
            "pubchem": {"found": False},
        }

    trace = ensure_trace(trace)
    result = run_tool(
        trace,
        "pubchem.lookup_compound",
        pubchem_tools.lookup_compound,
        query=query or None,
        cid=cid,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "pubchem_compound", "source": "PubChem", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"PubChem lookup failed: {result['error']['message']}"],
            "pubchem": {"found": False},
        }

    top_record = (result.get("records") or [{}])[0]
    top_desc = (top_record.get("descriptions") or [{}])[0]
    return {
        "annotation": {
            "kind": "pubchem_compound",
            "source": "PubChem",
            "cid": top_record.get("cid"),
            "name": top_desc.get("title") or top_record.get("iupac_name"),
            "molecular_formula": top_record.get("molecular_formula"),
            "molecular_weight": top_record.get("molecular_weight"),
            "n_records": result.get("count", 0),
        },
        "confidence": 0.9 if result.get("count", 0) > 0 else 0.0,
        "notes": [],
        "pubchem": result,
    }
