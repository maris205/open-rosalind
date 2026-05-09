"""BindingDB REST client."""
from __future__ import annotations

from typing import Any

from ._http import make_session
from .base import ToolSpec

BASE_URL = "https://bindingdb.org"


def _normalize_affinity(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": raw.get("query"),
        "monomerid": raw.get("monomerid"),
        "smiles": raw.get("smile"),
        "affinity_type": raw.get("affinity_type"),
        "affinity": raw.get("affinity"),
        "pmid": raw.get("pmid"),
        "doi": raw.get("doi"),
    }


def lookup_ligands(
    uniprot_id: str | None = None,
    pdb_id: str | None = None,
    max_results: int = 5,
) -> dict[str, Any]:
    """Lookup BindingDB ligands for a UniProt accession or PDB ID."""
    clean_uniprot = (uniprot_id or "").strip()
    clean_pdb = (pdb_id or "").strip().upper()
    if bool(clean_uniprot) == bool(clean_pdb):
        raise ValueError("provide exactly one of uniprot_id or pdb_id")

    session = make_session()
    try:
        if clean_uniprot:
            response = session.get(
                f"{BASE_URL}/rest/getLigandsByUniprots",
                params={"uniprot": clean_uniprot, "cutoff": 100, "response": "application/json"},
                timeout=40,
            )
            response.raise_for_status()
            data = response.json()
            root = data.get("getLindsByUniprotsResponse") or {}
            records = root.get("affinities") or []
            query_type = "uniprot"
            query_value = clean_uniprot
        else:
            response = session.get(
                f"{BASE_URL}/rest/getLigandsByPDBs",
                params={"pdb": clean_pdb, "cutoff": 100, "identity": 92, "response": "application/json"},
                timeout=40,
            )
            response.raise_for_status()
            data = response.json()
            root = data.get("getLindsByPDBsResponse") or {}
            records = root.get("affinities") or []
            query_type = "pdb"
            query_value = clean_pdb
    finally:
        session.close()

    normalized = [_normalize_affinity(item) for item in records[: max(1, min(int(max_results), 10))] if isinstance(item, dict)]
    return {
        "query_type": query_type,
        "query": query_value,
        "count": len(normalized),
        "records": normalized,
    }


LOOKUP_LIGANDS_SPEC = ToolSpec(
    name="bindingdb.lookup_ligands",
    description="Lookup BindingDB ligands by UniProt accession or PDB ID.",
    input_schema={
        "type": "object",
        "properties": {
            "uniprot_id": {"type": "string"},
            "pdb_id": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
        },
    },
    output_schema={"type": "object"},
    handler=lookup_ligands,
)
