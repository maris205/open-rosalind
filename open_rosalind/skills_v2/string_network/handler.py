"""STRING network handler."""
from __future__ import annotations

from typing import Any

from ...tools import stringdb as stringdb_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    identifiers = payload.get("identifiers")
    if identifiers is None:
        identifiers = str(payload.get("query") or "").strip()

    mode = str(payload.get("mode") or "interaction_partners").strip().lower()
    species = int(payload.get("species", 9606) or 9606)
    required_score = int(payload.get("required_score", 400) or 400)
    limit = int(payload.get("limit", 10) or 10)
    add_nodes = int(payload.get("add_nodes", 0) or 0)

    if identifiers is None or identifiers == "":
        return {
            "annotation": {"kind": "protein_network", "source": "STRING", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing STRING identifiers or query"],
            "string": {"mode": mode, "count": 0, "records": []},
        }

    if mode not in {"interaction_partners", "network"}:
        return {
            "annotation": {"kind": "protein_network", "source": "STRING", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"Unsupported STRING mode {mode!r}; use 'interaction_partners' or 'network'"],
            "string": {"mode": mode, "count": 0, "records": []},
        }

    trace = ensure_trace(trace)
    if mode == "network":
        result = run_tool(
            trace,
            "string.network",
            stringdb_tools.network,
            identifiers=identifiers,
            species=species,
            required_score=required_score,
            add_nodes=add_nodes,
        )
    else:
        result = run_tool(
            trace,
            "string.interaction_partners",
            stringdb_tools.interaction_partners,
            identifiers=identifiers,
            species=species,
            required_score=required_score,
            limit=limit,
        )

    if is_error(result):
        return {
            "annotation": {"kind": "protein_network", "source": "STRING", "mode": mode, "n_records": 0},
            "confidence": 0.0,
            "notes": [f"STRING lookup failed: {result['error']['message']}"],
            "string": {"mode": mode, "count": 0, "records": []},
        }

    records = result.get("records") or []
    top_record = records[0] if records else {}
    top_partners = []
    for item in records[:5]:
        partner = item.get("preferred_name_b")
        if partner and partner not in top_partners:
            top_partners.append(partner)

    return {
        "annotation": {
            "kind": "protein_network",
            "source": "STRING",
            "mode": result.get("mode", mode),
            "n_records": result.get("count", 0),
            "top_query": top_record.get("preferred_name_a"),
            "top_partner": top_record.get("preferred_name_b"),
            "top_score": top_record.get("score"),
            "top_partners": top_partners,
        },
        "confidence": 0.85 if result.get("count", 0) > 0 else 0.0,
        "notes": [],
        "string": result,
    }
