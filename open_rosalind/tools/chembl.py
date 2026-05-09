"""ChEMBL search client."""
from __future__ import annotations

from typing import Any

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"


def _available_count(data: dict[str, Any], fallback: int) -> int:
    page_meta = data.get("page_meta") or {}
    total_count = page_meta.get("total_count")
    return int(total_count) if isinstance(total_count, int) else fallback


def _normalize_synonyms(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    values: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            text = item.get("molecule_synonym") or item.get("synonym") or item.get("component_synonym")
        else:
            text = str(item)
        if text and text not in values:
            values.append(text)
    return values[:10]


def _normalize_molecule(raw: dict[str, Any]) -> dict[str, Any]:
    props = raw.get("molecule_properties") or {}
    chembl_id = raw.get("molecule_chembl_id")
    return {
        "molecule_chembl_id": chembl_id,
        "pref_name": raw.get("pref_name"),
        "molecule_type": raw.get("molecule_type"),
        "max_phase": raw.get("max_phase"),
        "structure_type": raw.get("structure_type"),
        "drug_type": raw.get("drug_type"),
        "atc_classifications": raw.get("atc_classifications") or [],
        "synonyms": _normalize_synonyms(raw.get("molecule_synonyms") or raw.get("synonyms")),
        "molecule_properties": {
            "full_mwt": props.get("full_mwt"),
            "alogp": props.get("alogp"),
            "psa": props.get("psa"),
            "hba": props.get("hba"),
            "hbd": props.get("hbd"),
            "qed_weighted": props.get("qed_weighted"),
            "ro3_pass": props.get("ro3_pass"),
        },
        "url": f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/" if chembl_id else None,
    }


def _normalize_target(raw: dict[str, Any]) -> dict[str, Any]:
    chembl_id = raw.get("target_chembl_id")
    components = raw.get("target_components") or []
    component_names: list[str] = []
    component_accessions: list[str] = []
    for item in components:
        if not isinstance(item, dict):
            continue
        accession = item.get("accession")
        if accession and accession not in component_accessions:
            component_accessions.append(accession)
        component_name = item.get("component_description") or item.get("component_name")
        if component_name and component_name not in component_names:
            component_names.append(component_name)
    return {
        "target_chembl_id": chembl_id,
        "pref_name": raw.get("pref_name"),
        "target_type": raw.get("target_type"),
        "organism": raw.get("organism"),
        "synonyms": _normalize_synonyms(raw.get("target_components") or raw.get("target_synonyms")),
        "component_names": component_names[:10],
        "component_accessions": component_accessions[:10],
        "url": f"https://www.ebi.ac.uk/chembl/target_report_card/{chembl_id}/" if chembl_id else None,
    }


def search_molecules(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search ChEMBL molecules by free-text query."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    data = get_json(
        f"{BASE_URL}/molecule/search.json",
        params={"q": clean_query, "limit": max_results},
        timeout=30,
    )
    records = [_normalize_molecule(item) for item in (data.get("molecules") or [])[:max_results] if isinstance(item, dict)]
    return {
        "query": clean_query,
        "entity": "molecule",
        "count": len(records),
        "record_count_available": _available_count(data, len(records)),
        "records": records,
    }


def search_targets(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search ChEMBL targets by free-text query."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    data = get_json(
        f"{BASE_URL}/target/search.json",
        params={"q": clean_query, "limit": max_results},
        timeout=30,
    )
    records = [_normalize_target(item) for item in (data.get("targets") or [])[:max_results] if isinstance(item, dict)]
    return {
        "query": clean_query,
        "entity": "target",
        "count": len(records),
        "record_count_available": _available_count(data, len(records)),
        "records": records,
    }


SEARCH_MOLECULES_SPEC = ToolSpec(
    name="chembl.search_molecules",
    description="Search ChEMBL molecules by free-text query or ChEMBL molecule ID.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 25},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search_molecules,
)


SEARCH_TARGETS_SPEC = ToolSpec(
    name="chembl.search_targets",
    description="Search ChEMBL targets by free-text query or ChEMBL target ID.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 25},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search_targets,
)
