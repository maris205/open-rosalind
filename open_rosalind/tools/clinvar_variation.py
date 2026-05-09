"""ClinVar Clinical Tables + dbSNP RefSNP client."""
from __future__ import annotations

from typing import Any

from ._http import get_json
from .base import ToolSpec

CLINICAL_TABLES_URL = "https://clinicaltables.nlm.nih.gov/api/variants/v4/search"
VARIATION_BASE_URL = "https://api.ncbi.nlm.nih.gov/variation/v0"


def search_clinical_tables(terms: str, max_results: int = 5) -> dict[str, Any]:
    """Search ClinVar variant records via Clinical Tables autocomplete API."""
    clean_terms = terms.strip()
    if not clean_terms:
        raise ValueError("terms is required")

    data = get_json(
        CLINICAL_TABLES_URL,
        params={"terms": clean_terms, "maxList": max_results},
        timeout=30,
    )
    if not isinstance(data, list) or len(data) < 4:
        return {"query": clean_terms, "count": 0, "records": []}

    identifiers = data[1] if isinstance(data[1], list) else []
    rows = data[3] if isinstance(data[3], list) else []
    records: list[dict[str, Any]] = []
    for identifier, row in zip(identifiers[:max_results], rows[:max_results]):
        record = {"identifier": identifier}
        if isinstance(row, list):
            for idx, value in enumerate(row[:8]):
                record[f"field_{idx}"] = value
        records.append(record)

    return {"query": clean_terms, "count": len(records), "records": records}


def _extract_hgvs(placements: list[dict[str, Any]]) -> list[str]:
    hgvs_values: list[str] = []
    for placement in placements:
        for allele in placement.get("alleles") or []:
            hgvs = allele.get("hgvs")
            if hgvs and hgvs not in hgvs_values:
                hgvs_values.append(hgvs)
    return hgvs_values[:10]


def _extract_frequencies(annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for annotation in annotations:
        for freq in annotation.get("frequency") or []:
            total = freq.get("total_count")
            allele_count = freq.get("allele_count")
            af = None
            if isinstance(total, int) and total > 0 and isinstance(allele_count, int):
                af = allele_count / total
            records.append(
                {
                    "study_name": freq.get("study_name"),
                    "allele_count": allele_count,
                    "total_count": total,
                    "allele_frequency": af,
                    "observation": freq.get("observation"),
                }
            )
    records.sort(key=lambda item: (item.get("study_name") or "", -(item.get("allele_frequency") or 0.0)))
    return records[:10]


def fetch_refsnp(refsnp_id: str | int) -> dict[str, Any]:
    """Fetch a RefSNP object by rsID from NCBI Variation Services."""
    raw_id = str(refsnp_id).strip()
    if not raw_id:
        raise ValueError("refsnp_id is required")

    clean_id = raw_id.lower().removeprefix("rs")
    data = get_json(f"{VARIATION_BASE_URL}/refsnp/{clean_id}", timeout=30)
    primary = data.get("primary_snapshot_data") or {}
    placements = primary.get("placements_with_allele") or []
    annotations = primary.get("allele_annotations") or []

    hgvs_values = _extract_hgvs(placements)
    frequencies = _extract_frequencies(annotations)
    top_frequency = max(
        (record for record in frequencies if isinstance(record.get("allele_frequency"), float)),
        key=lambda record: record["allele_frequency"],
        default=None,
    )

    return {
        "refsnp_id": str(data.get("refsnp_id") or clean_id),
        "variant_type": primary.get("variant_type"),
        "anchor": primary.get("anchor"),
        "hgvs": hgvs_values,
        "citations": [str(citation) for citation in (data.get("citations") or [])[:10]],
        "merges": data.get("dbsnp1_merges") or [],
        "allele_frequencies": frequencies,
        "top_frequency": top_frequency,
        "url": f"https://www.ncbi.nlm.nih.gov/snp/rs{data.get('refsnp_id') or clean_id}",
    }


SEARCH_CLINICAL_TABLES_SPEC = ToolSpec(
    name="clinvar_variation.search_clinical_tables",
    description="Search ClinVar variant identifiers using the NLM Clinical Tables API.",
    input_schema={
        "type": "object",
        "properties": {
            "terms": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["terms"],
    },
    output_schema={"type": "object"},
    handler=search_clinical_tables,
)


FETCH_REFSNP_SPEC = ToolSpec(
    name="clinvar_variation.fetch_refsnp",
    description="Fetch a RefSNP object by rsID from NCBI Variation Services.",
    input_schema={
        "type": "object",
        "properties": {"refsnp_id": {"anyOf": [{"type": "string"}, {"type": "integer"}]}},
        "required": ["refsnp_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_refsnp,
)
