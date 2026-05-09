"""PubChem PUG REST client."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def _normalize_descriptions(data: dict[str, Any]) -> list[dict[str, Any]]:
    info = (((data.get("InformationList") or {}).get("Information")) or [])
    records = []
    for item in info[:10]:
        if not isinstance(item, dict):
            continue
        if item.get("Description") or item.get("Title"):
            records.append(
                {
                    "cid": item.get("CID"),
                    "title": item.get("Title"),
                    "description": item.get("Description"),
                    "source_name": item.get("DescriptionSourceName"),
                    "source_url": item.get("DescriptionURL"),
                }
            )
    return records


def _resolve_cid(query: str | None = None, cid: int | str | None = None) -> tuple[int | None, str]:
    if cid is not None:
        clean_cid = int(str(cid).strip())
        return clean_cid, f"cid:{clean_cid}"
    clean_query = (query or "").strip()
    if not clean_query:
        raise ValueError("query or cid is required")
    if clean_query.isdigit():
        return int(clean_query), f"cid:{clean_query}"
    data = get_json(f"{BASE_URL}/compound/name/{quote(clean_query, safe='')}/cids/JSON", timeout=30)
    cid_list = ((data.get("IdentifierList") or {}).get("CID")) or []
    if not cid_list:
        return None, clean_query
    return int(cid_list[0]), clean_query


def lookup_compound(query: str | None = None, cid: int | str | None = None) -> dict[str, Any]:
    """Lookup a PubChem compound by name or CID and return focused properties."""
    resolved_cid, query_text = _resolve_cid(query=query, cid=cid)
    if resolved_cid is None:
        return {"query": query_text, "found": False, "count": 0, "records": []}

    try:
        props = get_json(
            f"{BASE_URL}/compound/cid/{resolved_cid}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON",
            timeout=30,
        )
        desc = get_json(f"{BASE_URL}/compound/cid/{resolved_cid}/description/JSON", timeout=30)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            return {"query": query_text, "cid": resolved_cid, "found": False, "count": 0, "records": []}
        raise

    properties = (((props.get("PropertyTable") or {}).get("Properties")) or [])
    if not properties:
        return {"query": query_text, "cid": resolved_cid, "found": False, "count": 0, "records": []}

    raw = properties[0]
    record = {
        "cid": raw.get("CID") or resolved_cid,
        "query": query_text,
        "molecular_formula": raw.get("MolecularFormula"),
        "molecular_weight": raw.get("MolecularWeight"),
        "canonical_smiles": raw.get("CanonicalSMILES"),
        "iupac_name": raw.get("IUPACName"),
        "descriptions": _normalize_descriptions(desc),
    }
    return {"query": query_text, "cid": resolved_cid, "found": True, "count": 1, "records": [record]}


LOOKUP_COMPOUND_SPEC = ToolSpec(
    name="pubchem.lookup_compound",
    description="Lookup a PubChem compound by name or CID and return focused properties and descriptions.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "cid": {"type": ["integer", "string"]},
        },
    },
    output_schema={"type": "object"},
    handler=lookup_compound,
)
