"""PharmGKB clinical annotation client."""
from __future__ import annotations

from typing import Any

import requests

from ._http import get_json, make_session
from .base import ToolSpec

BASE_URL = "https://api.pharmgkb.org/v1/data"


def _name_list(items: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if isinstance(item, dict) and item.get("name"):
            out.append(str(item["name"]))
    return out


def _symbol_list(items: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if isinstance(item, dict) and item.get("symbol"):
            out.append(str(item["symbol"]))
    return out


def _annotation_query_mode(
    chemical_name: str | None = None,
    gene_symbol: str | None = None,
    variant_symbol: str | None = None,
) -> tuple[str, str]:
    values = {
        "chemical_name": (chemical_name or "").strip(),
        "gene_symbol": (gene_symbol or "").strip(),
        "variant_symbol": (variant_symbol or "").strip(),
    }
    provided = [(mode, value) for mode, value in values.items() if value]
    if len(provided) != 1:
        raise ValueError("provide exactly one of chemical_name, gene_symbol, or variant_symbol")
    return provided[0]


def _normalize_base_record(raw: dict[str, Any]) -> dict[str, Any]:
    location = raw.get("location") or {}
    variant = location.get("variant") or {}
    genes = location.get("genes") or []
    return {
        "id": raw.get("id"),
        "accession_id": raw.get("accessionId"),
        "name": raw.get("name"),
        "score": raw.get("score"),
        "types": raw.get("types") or [],
        "level_of_evidence": (raw.get("levelOfEvidence") or {}).get("term"),
        "chemical_names": _name_list(raw.get("relatedChemicals")),
        "gene_symbols": _symbol_list(genes),
        "variant_symbol": variant.get("symbol"),
        "rsid": location.get("rsid"),
    }


def _normalize_detail_record(raw: dict[str, Any]) -> dict[str, Any]:
    location = raw.get("location") or {}
    variant = location.get("variant") or {}
    genes = location.get("genes") or []
    return {
        "id": raw.get("id"),
        "accession_id": raw.get("accessionId"),
        "name": raw.get("name"),
        "score": raw.get("score"),
        "types": raw.get("types") or [],
        "level_of_evidence": (raw.get("levelOfEvidence") or {}).get("term"),
        "override_level": raw.get("overrideLevel"),
        "chemical_names": _name_list(raw.get("relatedChemicals")),
        "gene_symbols": _symbol_list(genes),
        "variant_symbol": variant.get("symbol"),
        "rsid": location.get("rsid"),
        "location_display_name": location.get("displayName"),
        "related_diseases": _name_list(raw.get("relatedDiseases")),
        "related_guidelines": _name_list(raw.get("relatedGuidelines")),
        "related_labels": _name_list(raw.get("relatedLabels")),
        "related_variations": [
            {
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "obj_class": item.get("objCls"),
            }
            for item in (raw.get("relatedVariations") or [])[:10]
            if isinstance(item, dict)
        ],
        "allele_phenotypes": [
            {
                "allele": item.get("allele"),
                "phenotype": item.get("phenotype"),
                "limited_evidence": item.get("limitedEvidence"),
            }
            for item in (raw.get("allelePhenotypes") or [])[:10]
            if isinstance(item, dict)
        ],
    }


def search_clinical_annotations(
    chemical_name: str | None = None,
    gene_symbol: str | None = None,
    variant_symbol: str | None = None,
    max_results: int = 5,
) -> dict[str, Any]:
    """Search PharmGKB clinical annotations by drug, gene, or variant symbol."""
    mode, query = _annotation_query_mode(
        chemical_name=chemical_name,
        gene_symbol=gene_symbol,
        variant_symbol=variant_symbol,
    )
    limit = max(1, min(int(max_results), 10))

    param_name = {
        "chemical_name": "relatedChemicals.name",
        "gene_symbol": "location.genes.symbol",
        "variant_symbol": "location.variant.symbol",
    }[mode]
    data = get_json(
        f"{BASE_URL}/clinicalAnnotation",
        params={param_name: query, "view": "base"},
        timeout=60,
    )
    if data.get("status") == "fail":
        errors = data.get("data", {}).get("errors") or []
        raise ValueError("; ".join(error.get("message", "unknown error") for error in errors))

    raw_records = data.get("data") or []
    records = [
        _normalize_base_record(raw)
        for raw in raw_records[:limit]
        if isinstance(raw, dict)
    ]
    return {
        "mode": mode,
        "query": query,
        "count": len(records),
        "records": records,
    }


def fetch_clinical_annotation(
    annotation_id: int | str | None = None,
    accession_id: str | None = None,
) -> dict[str, Any]:
    """Fetch a PharmGKB clinical annotation detail record."""
    target = (accession_id or "").strip()
    if not target and annotation_id is not None:
        target = str(annotation_id).strip()
    if not target:
        raise ValueError("annotation_id or accession_id is required")

    session = make_session()
    try:
        response = session.get(
            f"{BASE_URL}/clinicalAnnotation/{target}",
            headers={"Accept": "application/json"},
            timeout=60,
        )
        if response.status_code == 404:
            return {"query": target, "found": False}
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            return {"query": target, "found": False}
        raise
    finally:
        session.close()

    if payload.get("status") == "fail":
        errors = payload.get("data", {}).get("errors") or []
        raise ValueError("; ".join(error.get("message", "unknown error") for error in errors))

    raw = payload.get("data") or {}
    if not isinstance(raw, dict):
        return {"query": target, "found": False}
    record = _normalize_detail_record(raw)
    record["query"] = target
    record["found"] = True
    return record


SEARCH_CLINICAL_ANNOTATIONS_SPEC = ToolSpec(
    name="pharmgkb.search_clinical_annotations",
    description="Search PharmGKB clinical annotations by chemical name, gene symbol, or variant symbol.",
    input_schema={
        "type": "object",
        "properties": {
            "chemical_name": {"type": "string"},
            "gene_symbol": {"type": "string"},
            "variant_symbol": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
        },
    },
    output_schema={"type": "object"},
    handler=search_clinical_annotations,
)


FETCH_CLINICAL_ANNOTATION_SPEC = ToolSpec(
    name="pharmgkb.fetch_clinical_annotation",
    description="Fetch a PharmGKB clinical annotation detail by numeric ID or accession ID.",
    input_schema={
        "type": "object",
        "properties": {
            "annotation_id": {"type": ["integer", "string"]},
            "accession_id": {"type": "string"},
        },
    },
    output_schema={"type": "object"},
    handler=fetch_clinical_annotation,
)
