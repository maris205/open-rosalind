"""Human Protein Atlas lookup handler."""
from __future__ import annotations

from typing import Any

from ...tools import ensembl as ensembl_tools
from ...tools import human_protein_atlas as hpa_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    gene_symbol = str(payload.get("gene_symbol") or "").strip()
    ensembl_id = str(payload.get("ensembl_id") or "").strip()
    species = str(payload.get("species") or "homo_sapiens").strip() or "homo_sapiens"

    if not gene_symbol and not ensembl_id:
        return {
            "annotation": {"kind": "human_protein_atlas", "source": "Human Protein Atlas", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing gene_symbol or ensembl_id"],
            "gene_lookup": {"found": False},
            "hpa": {"found": False, "count": 0, "records": []},
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
                "annotation": {"kind": "human_protein_atlas", "source": "Human Protein Atlas", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Ensembl gene lookup failed: {gene_lookup['error']['message']}"],
                "gene_lookup": {"found": False},
                "hpa": {"found": False, "count": 0, "records": []},
            }
        if not gene_lookup.get("found"):
            return {
                "annotation": {"kind": "human_protein_atlas", "source": "Human Protein Atlas", "n_records": 0},
                "confidence": 0.0,
                "notes": [f"Could not resolve Ensembl gene for symbol {gene_symbol!r}"],
                "gene_lookup": gene_lookup,
                "hpa": {"found": False, "count": 0, "records": []},
            }
        ensembl_id = str(gene_lookup.get("ensembl_gene_id") or "").strip()
        notes.append(f"Resolved gene symbol {gene_symbol!r} to Ensembl gene {ensembl_id}")

    result = run_tool(
        trace,
        "human_protein_atlas.fetch_gene",
        hpa_tools.fetch_gene,
        ensembl_id=ensembl_id,
    )
    if is_error(result):
        return {
            "annotation": {"kind": "human_protein_atlas", "source": "Human Protein Atlas", "ensembl_id": ensembl_id, "n_records": 0},
            "confidence": 0.0,
            "notes": notes + [f"Human Protein Atlas lookup failed: {result['error']['message']}"],
            "gene_lookup": gene_lookup,
            "hpa": {"found": False, "count": 0, "records": []},
        }

    records = result.get("records") or []
    top_record = records[0] if records else {}
    return {
        "annotation": {
            "kind": "human_protein_atlas",
            "source": "Human Protein Atlas",
            "gene_symbol": top_record.get("gene") or gene_lookup.get("symbol") or gene_symbol or None,
            "ensembl_id": top_record.get("ensembl_id") or ensembl_id,
            "uniprot_id": (top_record.get("uniprot_ids") or [None])[0],
            "top_subcellular_location": (top_record.get("subcellular_main_location") or [None])[0],
            "rna_tissue_specificity": top_record.get("rna_tissue_specificity"),
            "n_records": result.get("count", 0),
        },
        "confidence": 0.9 if result.get("found") and result.get("count", 0) > 0 else 0.0,
        "notes": notes,
        "gene_lookup": gene_lookup,
        "hpa": result,
    }
