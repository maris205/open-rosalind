"""Ensembl REST client for gene lookups and cross-references."""
from __future__ import annotations

from typing import Any

import requests

from ._http import make_session
from .base import ToolSpec

BASE_URL = "https://rest.ensembl.org"


def _species_name(species: str) -> str:
    clean = species.strip().replace(" ", "_").lower()
    return clean or "homo_sapiens"


def _get_json(path: str, params: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    session = make_session()
    response = session.get(
        f"{BASE_URL}{path}",
        params=params,
        headers={"Accept": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _normalize_transcript(raw: dict[str, Any], canonical_transcript: str | None) -> dict[str, Any]:
    translation = raw.get("Translation") or {}
    transcript_id = raw.get("id")
    return {
        "id": transcript_id,
        "display_name": raw.get("display_name"),
        "biotype": raw.get("biotype"),
        "is_canonical": bool(raw.get("is_canonical")) or transcript_id == canonical_transcript,
        "length": raw.get("length"),
        "translation_id": translation.get("id"),
        "protein_length": translation.get("length"),
    }


def lookup_gene(symbol: str, species: str = "homo_sapiens") -> dict[str, Any]:
    """Look up an Ensembl gene by symbol."""
    clean_symbol = symbol.strip()
    if not clean_symbol:
        raise ValueError("symbol is required")

    clean_species = _species_name(species)
    try:
        data = _get_json(f"/lookup/symbol/{clean_species}/{clean_symbol}", params={"expand": 1}, timeout=30)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            return {"query": clean_symbol, "species": clean_species, "found": False}
        raise

    canonical_transcript = data.get("canonical_transcript")
    transcripts = data.get("Transcript") or []
    normalized_transcripts = [
        _normalize_transcript(transcript, canonical_transcript)
        for transcript in transcripts
        if isinstance(transcript, dict)
    ]

    return {
        "query": clean_symbol,
        "species": clean_species,
        "found": True,
        "ensembl_gene_id": data.get("id"),
        "symbol": data.get("display_name") or clean_symbol,
        "description": data.get("description"),
        "biotype": data.get("biotype"),
        "object_type": data.get("object_type"),
        "assembly_name": data.get("assembly_name"),
        "seq_region_name": data.get("seq_region_name"),
        "start": data.get("start"),
        "end": data.get("end"),
        "strand": data.get("strand"),
        "canonical_transcript": canonical_transcript,
        "n_transcripts": len(normalized_transcripts),
        "transcripts": normalized_transcripts[:20],
        "url": f"https://www.ensembl.org/id/{data.get('id')}",
    }


def _normalize_xref(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "dbname": raw.get("dbname"),
        "primary_id": raw.get("primary_id"),
        "display_id": raw.get("display_id"),
        "description": raw.get("description"),
        "synonyms": raw.get("synonyms") or [],
        "info_type": raw.get("info_type"),
        "db_display_name": raw.get("db_display_name"),
        "linkage_types": raw.get("linkage_types") or [],
    }


def fetch_xrefs(ensembl_id: str, external_db: str | None = None) -> dict[str, Any]:
    """Fetch Ensembl cross-references for a stable Ensembl ID."""
    clean_id = ensembl_id.strip()
    if not clean_id:
        raise ValueError("ensembl_id is required")

    params: dict[str, Any] = {"all_levels": 1}
    if external_db and external_db.strip():
        params["external_db"] = external_db.strip()

    records = _get_json(f"/xrefs/id/{clean_id}", params=params, timeout=30)
    normalized = [_normalize_xref(record) for record in records if isinstance(record, dict)]
    return {
        "ensembl_id": clean_id,
        "count": len(normalized),
        "records": normalized,
    }


LOOKUP_GENE_SPEC = ToolSpec(
    name="ensembl.lookup_gene",
    description="Look up an Ensembl gene by symbol and return canonical locus and transcript metadata.",
    input_schema={
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "species": {"type": "string", "default": "homo_sapiens"},
        },
        "required": ["symbol"],
    },
    output_schema={"type": "object"},
    handler=lookup_gene,
)


FETCH_XREFS_SPEC = ToolSpec(
    name="ensembl.fetch_xrefs",
    description="Fetch Ensembl cross-references for a stable Ensembl identifier.",
    input_schema={
        "type": "object",
        "properties": {
            "ensembl_id": {"type": "string"},
            "external_db": {"type": "string"},
        },
        "required": ["ensembl_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_xrefs,
)
