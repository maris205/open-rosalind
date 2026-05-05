"""ClinVar E-utilities client."""
from __future__ import annotations

from typing import Any

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _classification(raw: dict[str, Any], key: str) -> dict[str, Any]:
    block = raw.get(key) or {}
    return {
        "description": block.get("description"),
        "review_status": block.get("review_status"),
        "last_evaluated": block.get("last_evaluated"),
        "traits": _trait_names(block.get("trait_set") or []),
    }


def _trait_names(trait_set: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for item in trait_set:
        trait_name = item.get("trait_name")
        if trait_name and trait_name not in names:
            names.append(trait_name)
    return names


def _xref_ids(xrefs: list[dict[str, Any]], db_source: str) -> list[str]:
    values: list[str] = []
    for xref in xrefs:
        if xref.get("db_source") != db_source:
            continue
        db_id = xref.get("db_id")
        if db_id and db_id not in values:
            values.append(db_id)
    return values


def _unique_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return unique


def _normalize_record(raw: dict[str, Any]) -> dict[str, Any]:
    variation = (raw.get("variation_set") or [{}])[0]
    variation_xrefs = variation.get("variation_xrefs") or []
    genes = raw.get("genes") or []

    germline = _classification(raw, "germline_classification")
    clinical_impact = _classification(raw, "clinical_impact_classification")
    oncogenicity = _classification(raw, "oncogenicity_classification")
    all_traits = _unique_strings(germline["traits"] + clinical_impact["traits"] + oncogenicity["traits"])

    return {
        "uid": raw.get("uid"),
        "accession": raw.get("accession"),
        "accession_version": raw.get("accession_version"),
        "title": raw.get("title"),
        "gene": (genes[0] or {}).get("symbol") if genes else raw.get("gene_sort"),
        "genes": [
            {
                "symbol": gene.get("symbol"),
                "geneid": gene.get("geneid"),
                "strand": gene.get("strand"),
            }
            for gene in genes
        ],
        "protein_change": raw.get("protein_change"),
        "variant_type": variation.get("variant_type") or raw.get("obj_type"),
        "molecular_consequences": raw.get("molecular_consequence_list") or [],
        "canonical_spdi": variation.get("canonical_spdi"),
        "aliases": variation.get("aliases") or [],
        "dbsnp_ids": _xref_ids(variation_xrefs, "dbSNP"),
        "uniprot_ids": _xref_ids(variation_xrefs, "UniProtKB"),
        "omim_ids": _xref_ids(variation_xrefs, "OMIM"),
        "germline_classification": germline,
        "clinical_impact_classification": clinical_impact,
        "oncogenicity_classification": oncogenicity,
        "trait_names": all_traits,
        "scv_count": len((raw.get("supporting_submissions") or {}).get("scv") or []),
        "rcv_count": len((raw.get("supporting_submissions") or {}).get("rcv") or []),
        "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{raw.get('uid')}/",
    }


def search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search ClinVar variation records and return compact summaries."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    esearch = get_json(
        f"{BASE_URL}/esearch.fcgi",
        params={"db": "clinvar", "term": clean_query, "retmode": "json", "retmax": max_results, "sort": "relevance"},
        timeout=30,
    )
    ids = esearch.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return {"query": clean_query, "count": 0, "records": []}

    summary = get_json(
        f"{BASE_URL}/esummary.fcgi",
        params={"db": "clinvar", "id": ",".join(ids), "retmode": "json", "version": "2.0"},
        timeout=30,
    )
    result = summary.get("result", {})

    records: list[dict[str, Any]] = []
    for uid in result.get("uids", ids):
        raw = result.get(uid, {})
        if not raw or raw.get("error"):
            continue
        records.append(_normalize_record(raw))

    return {"query": clean_query, "count": len(records), "records": records}


SEARCH_SPEC = ToolSpec(
    name="clinvar.search",
    description="Search ClinVar variation records by gene, HGVS/protein change, disease, or free-text query.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search,
)
