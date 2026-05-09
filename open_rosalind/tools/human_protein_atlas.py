"""Human Protein Atlas JSON client."""
from __future__ import annotations

from typing import Any

import requests

from ._http import make_session
from .base import ToolSpec

BASE_URL = "https://www.proteinatlas.org"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def fetch_gene(ensembl_id: str) -> dict[str, Any]:
    """Fetch a Human Protein Atlas gene summary by Ensembl gene identifier."""
    clean_id = ensembl_id.strip()
    if not clean_id:
        raise ValueError("ensembl_id is required")

    session = make_session()
    try:
        response = session.get(
            f"{BASE_URL}/{clean_id}.json",
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if response.status_code == 404:
            return {"query": clean_id, "found": False, "count": 0, "records": []}
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            return {"query": clean_id, "found": False, "count": 0, "records": []}
        raise
    finally:
        session.close()

    if not isinstance(data, dict):
        raise ValueError("Human Protein Atlas response was not a JSON object")

    record = {
        "gene": data.get("Gene"),
        "ensembl_id": data.get("Ensembl") or clean_id,
        "gene_description": data.get("Gene description"),
        "gene_synonyms": _as_list(data.get("Gene synonym")),
        "uniprot_ids": _as_list(data.get("Uniprot")),
        "protein_class": _as_list(data.get("Protein class")),
        "biological_process": _as_list(data.get("Biological process")),
        "molecular_function": _as_list(data.get("Molecular function")),
        "subcellular_main_location": _as_list(data.get("Subcellular main location")),
        "subcellular_location": _as_list(data.get("Subcellular location")),
        "disease_involvement": data.get("Disease involvement"),
        "rna_tissue_distribution": data.get("RNA tissue distribution"),
        "rna_tissue_specificity": data.get("RNA tissue specificity"),
        "rna_tissue_specificity_score": data.get("RNA tissue specificity score"),
        "rna_tissue_specific_ntpm": data.get("RNA tissue specific nTPM"),
        "rna_cell_line_distribution": data.get("RNA cell line distribution"),
        "rna_cell_line_specificity": data.get("RNA cell line specificity"),
        "tissue_expression_cluster": data.get("Tissue expression cluster"),
        "cell_line_expression_cluster": data.get("Cell line expression cluster"),
    }
    return {"query": clean_id, "found": True, "count": 1, "records": [record]}


FETCH_GENE_SPEC = ToolSpec(
    name="human_protein_atlas.fetch_gene",
    description="Fetch a Human Protein Atlas gene summary by Ensembl gene identifier.",
    input_schema={
        "type": "object",
        "properties": {"ensembl_id": {"type": "string"}},
        "required": ["ensembl_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_gene,
)
