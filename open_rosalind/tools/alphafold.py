"""AlphaFold DB REST client."""
from __future__ import annotations

from typing import Any

import requests

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://alphafold.ebi.ac.uk/api"


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    sequence = record.get("sequence") or record.get("uniprotSequence") or ""
    sequence_start = record.get("sequenceStart") or 1
    sequence_end = record.get("sequenceEnd") or len(sequence)
    if sequence and isinstance(sequence_start, int) and isinstance(sequence_end, int):
        sequence_length = max(sequence_end - sequence_start + 1, 0)
    else:
        sequence_length = len(sequence)

    return {
        "entry_id": record.get("entryId") or record.get("modelEntityId"),
        "model_entity_id": record.get("modelEntityId"),
        "uniprot_accession": record.get("uniprotAccession"),
        "uniprot_id": record.get("uniprotId"),
        "gene": record.get("gene"),
        "organism": record.get("organismScientificName"),
        "description": record.get("uniprotDescription"),
        "mean_plddt": record.get("globalMetricValue"),
        "latest_version": record.get("latestVersion"),
        "model_created_date": record.get("modelCreatedDate"),
        "sequence_version_date": record.get("sequenceVersionDate"),
        "sequence_start": sequence_start,
        "sequence_end": sequence_end,
        "sequence_length": sequence_length,
        "is_reviewed": record.get("isReviewed"),
        "is_reference_proteome": record.get("isReferenceProteome"),
        "is_complex": record.get("isComplex"),
        "fractions": {
            "very_low": record.get("fractionPlddtVeryLow"),
            "low": record.get("fractionPlddtLow"),
            "confident": record.get("fractionPlddtConfident"),
            "very_high": record.get("fractionPlddtVeryHigh"),
        },
        "pdb_url": record.get("pdbUrl"),
        "cif_url": record.get("cifUrl"),
        "bcif_url": record.get("bcifUrl"),
        "plddt_doc_url": record.get("plddtDocUrl"),
        "pae_doc_url": record.get("paeDocUrl"),
        "pae_image_url": record.get("paeImageUrl"),
    }


def fetch_prediction(accession: str) -> dict[str, Any]:
    """Fetch AlphaFold DB prediction metadata for a UniProt accession."""
    clean_accession = accession.strip()
    if not clean_accession:
        raise ValueError("accession is required")

    try:
        data = get_json(f"{BASE_URL}/prediction/{clean_accession}", timeout=30)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            return {"accession": clean_accession, "count": 0, "models": []}
        raise

    if not isinstance(data, list):
        return {"accession": clean_accession, "count": 0, "models": []}

    models = [_normalize_record(record) for record in data if isinstance(record, dict)]
    return {"accession": clean_accession, "count": len(models), "models": models}


FETCH_PREDICTION_SPEC = ToolSpec(
    name="alphafold.fetch_prediction",
    description="Fetch AlphaFold DB structure model metadata for a UniProt accession.",
    input_schema={
        "type": "object",
        "properties": {"accession": {"type": "string"}},
        "required": ["accession"],
    },
    output_schema={"type": "object"},
    handler=fetch_prediction,
)
