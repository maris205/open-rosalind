"""Ensembl gene lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import ensembl as ensembl_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    symbol = str(payload.get("symbol") or payload.get("gene_symbol") or payload.get("query") or "").strip()
    species = str(payload.get("species") or "homo_sapiens").strip() or "homo_sapiens"

    if not symbol:
        return {
            "annotation": {"kind": "gene", "source": "Ensembl", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing Ensembl gene symbol or query"],
            "gene": {},
        }

    trace = ensure_trace(trace)
    result = run_tool(trace, "ensembl.lookup_gene", ensembl_tools.lookup_gene, symbol=symbol, species=species)
    if is_error(result):
        return {
            "annotation": {"kind": "gene", "source": "Ensembl", "symbol": symbol, "n_records": 0},
            "confidence": 0.0,
            "notes": [f"Ensembl gene lookup failed: {result['error']['message']}"],
            "gene": {},
        }
    if not result.get("found", True):
        return {
            "annotation": {"kind": "gene", "source": "Ensembl", "symbol": symbol, "n_records": 0},
            "confidence": 0.0,
            "notes": [f"No Ensembl gene was found for {symbol!r}"],
            "gene": result,
        }

    return {
        "annotation": {
            "kind": "gene",
            "source": "Ensembl",
            "symbol": result.get("symbol"),
            "species": result.get("species"),
            "ensembl_gene_id": result.get("ensembl_gene_id"),
            "biotype": result.get("biotype"),
            "canonical_transcript": result.get("canonical_transcript"),
            "n_transcripts": result.get("n_transcripts", 0),
            "seq_region_name": result.get("seq_region_name"),
        },
        "confidence": 0.88,
        "notes": [],
        "gene": result,
    }
