"""gnomAD variant lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import gnomad as gnomad_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    variant_id = str(payload.get("variant_id") or "").strip()
    rsid = str(payload.get("rsid") or "").strip()
    dataset = str(payload.get("dataset") or "gnomad_r4").strip() or "gnomad_r4"

    if not variant_id and not rsid:
        return {
            "annotation": {"kind": "gnomad_variant", "source": "gnomAD", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing variant_id or rsid"],
            "gnomad": {},
        }

    trace = ensure_trace(trace)
    result = run_tool(
        trace,
        "gnomad.fetch_variant",
        gnomad_tools.fetch_variant,
        variant_id=variant_id or None,
        rsid=rsid or None,
        dataset=dataset,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "gnomad_variant", "source": "gnomAD", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"gnomAD lookup failed: {result['error']['message']}"],
            "gnomad": {},
        }
    if not result.get("found", True):
        return {
            "annotation": {"kind": "gnomad_variant", "source": "gnomAD", "query": result.get("query"), "n_records": 0},
            "confidence": 0.0,
            "notes": [f"No gnomAD record found for {result.get('query')!r}"],
            "gnomad": result,
        }

    top_consequence = (result.get("transcript_consequences") or [{}])[0]
    return {
        "annotation": {
            "kind": "gnomad_variant",
            "source": "gnomAD",
            "variant_id": result.get("variant_id"),
            "dataset": result.get("dataset"),
            "gene_symbol": top_consequence.get("gene_symbol"),
            "major_consequence": top_consequence.get("major_consequence"),
            "exome_af": (result.get("exome") or {}).get("af"),
            "genome_af": (result.get("genome") or {}).get("af"),
        },
        "confidence": 0.85,
        "notes": [],
        "gnomad": result,
    }
