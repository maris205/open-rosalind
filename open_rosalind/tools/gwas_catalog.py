"""GWAS Catalog REST client."""
from __future__ import annotations

from typing import Any

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://www.ebi.ac.uk/gwas/rest/api/v2"


def _page_count(data: dict[str, Any], fallback: int) -> int:
    page = data.get("page") or {}
    total_elements = page.get("totalElements")
    return int(total_elements) if isinstance(total_elements, int) else fallback


def _normalize_study(raw: dict[str, Any]) -> dict[str, Any]:
    traits = raw.get("efo_traits") or []
    return {
        "accession_id": raw.get("accession_id"),
        "disease_trait": raw.get("disease_trait"),
        "pubmed_id": str(raw.get("pubmed_id")) if raw.get("pubmed_id") is not None else None,
        "first_author": raw.get("first_author"),
        "initial_sample_size": raw.get("initial_sample_size"),
        "genotyping_technologies": raw.get("genotyping_technologies") or [],
        "efo_traits": [{"efo_id": trait.get("efo_id"), "efo_trait": trait.get("efo_trait")} for trait in traits[:10]],
        "url": (raw.get("_links") or {}).get("self", {}).get("href"),
    }


def _normalize_association(raw: dict[str, Any]) -> dict[str, Any]:
    traits = raw.get("efo_traits") or []
    snp_alleles = raw.get("snp_allele") or []
    return {
        "association_id": raw.get("association_id"),
        "accession_id": raw.get("accession_id"),
        "reported_trait": raw.get("reported_trait"),
        "mapped_genes": raw.get("mapped_genes") or [],
        "p_value": raw.get("p_value"),
        "risk_frequency": raw.get("risk_frequency"),
        "odds_ratio": raw.get("or_per_copy_num"),
        "beta": raw.get("beta"),
        "locations": raw.get("locations") or [],
        "efo_traits": [{"efo_id": trait.get("efo_id"), "efo_trait": trait.get("efo_trait")} for trait in traits[:10]],
        "snp_allele": snp_alleles[:10],
        "url": (raw.get("_links") or {}).get("self", {}).get("href"),
        "snp_url": (raw.get("_links") or {}).get("snp", {}).get("href"),
    }


def search_studies(efo_trait: str, size: int = 5) -> dict[str, Any]:
    """Search GWAS Catalog studies by EFO trait string."""
    clean_trait = efo_trait.strip()
    if not clean_trait:
        raise ValueError("efo_trait is required")

    data = get_json(f"{BASE_URL}/studies", params={"efo_trait": clean_trait, "size": size}, timeout=30)
    studies = [_normalize_study(item) for item in ((data.get("_embedded") or {}).get("studies") or [])[:size]]
    return {
        "query": clean_trait,
        "count": len(studies),
        "record_count_available": _page_count(data, len(studies)),
        "records": studies,
    }


def search_associations(efo_trait: str | None = None, mapped_gene: str | None = None, size: int = 5) -> dict[str, Any]:
    """Search GWAS Catalog associations by EFO trait or mapped gene."""
    clean_trait = (efo_trait or "").strip()
    clean_gene = (mapped_gene or "").strip()
    if not clean_trait and not clean_gene:
        raise ValueError("efo_trait or mapped_gene is required")

    params: dict[str, Any] = {"size": size}
    if clean_trait:
        params["efo_trait"] = clean_trait
    if clean_gene:
        params["mapped_gene"] = clean_gene

    data = get_json(f"{BASE_URL}/associations", params=params, timeout=30)
    associations = [
        _normalize_association(item)
        for item in ((data.get("_embedded") or {}).get("associations") or [])[:size]
    ]
    return {
        "query": clean_trait or clean_gene,
        "count": len(associations),
        "record_count_available": _page_count(data, len(associations)),
        "records": associations,
    }


SEARCH_STUDIES_SPEC = ToolSpec(
    name="gwas_catalog.search_studies",
    description="Search GWAS Catalog studies by EFO trait string.",
    input_schema={
        "type": "object",
        "properties": {
            "efo_trait": {"type": "string"},
            "size": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["efo_trait"],
    },
    output_schema={"type": "object"},
    handler=search_studies,
)


SEARCH_ASSOCIATIONS_SPEC = ToolSpec(
    name="gwas_catalog.search_associations",
    description="Search GWAS Catalog associations by EFO trait or mapped gene.",
    input_schema={
        "type": "object",
        "properties": {
            "efo_trait": {"type": "string"},
            "mapped_gene": {"type": "string"},
            "size": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
    },
    output_schema={"type": "object"},
    handler=search_associations,
)
