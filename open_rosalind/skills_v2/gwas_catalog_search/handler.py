"""GWAS Catalog search handler."""
from __future__ import annotations

from typing import Any

from ...tools import gwas_catalog as gwas_catalog_tools
from ..runtime import ensure_trace, is_error, run_tool


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    efo_trait = str(payload.get("efo_trait") or payload.get("query") or "").strip()
    mapped_gene = str(payload.get("mapped_gene") or "").strip()
    mode = str(payload.get("mode") or ("associations" if mapped_gene else "studies")).strip().lower()
    size = int(payload.get("size", 5) or 5)

    if not efo_trait and not mapped_gene:
        return {
            "annotation": {"kind": "gwas_catalog", "source": "GWAS Catalog", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing efo_trait/query or mapped_gene"],
            "gwas": {"count": 0, "records": []},
        }

    trace = ensure_trace(trace)
    if mode == "associations":
        result = run_tool(
            trace,
            "gwas_catalog.search_associations",
            gwas_catalog_tools.search_associations,
            efo_trait=efo_trait or None,
            mapped_gene=mapped_gene or None,
            size=size,
        )
    else:
        result = run_tool(
            trace,
            "gwas_catalog.search_studies",
            gwas_catalog_tools.search_studies,
            efo_trait=efo_trait,
            size=size,
        )

    if is_error(result):
        return {
            "annotation": {"kind": "gwas_catalog", "source": "GWAS Catalog", "n_records": 0},
            "confidence": 0.0,
            "notes": [f"GWAS Catalog lookup failed: {result['error']['message']}"],
            "gwas": {"count": 0, "records": []},
        }

    top_record = (result.get("records") or [{}])[0]
    return {
        "annotation": {
            "kind": "gwas_catalog",
            "source": "GWAS Catalog",
            "mode": mode,
            "query": result.get("query"),
            "n_records": result.get("count", 0),
            "accession_id": top_record.get("accession_id"),
            "disease_trait": top_record.get("disease_trait"),
            "reported_trait": top_record.get("reported_trait"),
            "mapped_genes": top_record.get("mapped_genes"),
            "p_value": top_record.get("p_value"),
        },
        "confidence": 0.8 if result.get("count", 0) > 0 else 0.0,
        "notes": [],
        "gwas": result,
    }
