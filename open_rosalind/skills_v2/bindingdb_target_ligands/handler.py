"""BindingDB target ligands handler."""
from __future__ import annotations

from typing import Any

from ...tools import bindingdb as bindingdb_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    uniprot_id = str(payload.get("uniprot_id") or "").strip()
    pdb_id = str(payload.get("pdb_id") or "").strip()
    max_results = int(payload.get("max_results", 5) or 5)

    if bool(uniprot_id) == bool(pdb_id):
        return {
            "annotation": {"kind": "bindingdb", "source": "BindingDB", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Provide exactly one of uniprot_id or pdb_id"],
            "bindingdb": {"count": 0, "records": []},
        }

    trace = ensure_trace(trace)
    result = run_tool(
        trace,
        "bindingdb.lookup_ligands",
        bindingdb_tools.lookup_ligands,
        uniprot_id=uniprot_id or None,
        pdb_id=pdb_id or None,
        max_results=max_results,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "bindingdb", "source": "BindingDB", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"BindingDB lookup failed: {result['error']['message']}"],
            "bindingdb": {"count": 0, "records": []},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "bindingdb",
            "source": "BindingDB",
            "query_type": result.get("query_type"),
            "query": result.get("query"),
            "top_affinity_type": top_record.get("affinity_type"),
            "top_affinity": top_record.get("affinity"),
            "top_pmid": top_record.get("pmid"),
            "n_records": result.get("count", 0),
        },
        "confidence": 0.85 if result.get("count", 0) > 0 else 0.0,
        "notes": [],
        "bindingdb": result,
    }
