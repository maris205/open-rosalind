"""Bgee expression lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import bgee as bgee_tools
from ...tools import ensembl as ensembl_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    gene_symbol = str(payload.get("gene_symbol") or "").strip()
    ensembl_id = str(payload.get("ensembl_id") or "").strip()
    species = str(payload.get("species") or "homo_sapiens").strip() or "homo_sapiens"
    max_results = int(payload.get("max_results", 5) or 5)

    if not gene_symbol and not ensembl_id:
        return {
            "annotation": {"kind": "bgee_expression", "source": "Bgee", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing gene_symbol or ensembl_id"],
            "gene_lookup": {"found": False},
            "bgee": {"count": 0, "records": []},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    gene_lookup: dict[str, Any] = {"found": False}

    if not ensembl_id:
        gene_lookup = run_tool(
            trace,
            "ensembl.lookup_gene",
            ensembl_tools.lookup_gene,
            symbol=gene_symbol,
            species=species,
        )
        if is_error(gene_lookup):
            return {
                "annotation": {"kind": "bgee_expression", "source": "Bgee", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Ensembl gene lookup failed: {gene_lookup['error']['message']}"],
                "gene_lookup": {"found": False},
                "bgee": {"count": 0, "records": []},
            }
        if not gene_lookup.get("found"):
            return {
                "annotation": {"kind": "bgee_expression", "source": "Bgee", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Could not resolve Ensembl gene for symbol {gene_symbol!r}"],
                "gene_lookup": gene_lookup,
                "bgee": {"count": 0, "records": []},
            }
        ensembl_id = str(gene_lookup.get("ensembl_gene_id") or "").strip()
        notes.append(f"Resolved gene symbol {gene_symbol!r} to Ensembl gene {ensembl_id}")

    result = run_tool(
        trace,
        "bgee.lookup_expression",
        bgee_tools.lookup_expression,
        ensembl_id=ensembl_id,
        max_results=max_results,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "bgee_expression", "source": "Bgee", "ensembl_id": ensembl_id, "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"Bgee lookup failed: {result['error']['message']}"],
            "gene_lookup": gene_lookup,
            "bgee": {"count": 0, "records": []},
        }

    top_record = (result.get("records") or [{}])[0]
    resolved_symbol = gene_lookup.get("symbol") or gene_symbol or None
    return {
        "annotation": {
            "kind": "bgee_expression",
            "source": "Bgee",
            "gene_symbol": resolved_symbol,
            "ensembl_id": ensembl_id,
            "top_anatomical_entity": top_record.get("anatomical_entity_name"),
            "top_expression_score": top_record.get("expression_score"),
            "n_records": result.get("count", 0),
        },
        "confidence": 0.85 if result.get("count", 0) > 0 else 0.0,
        "notes": notes,
        "gene_lookup": gene_lookup,
        "bgee": result,
    }
