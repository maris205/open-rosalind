"""CELLxGENE Discover collection client."""
from __future__ import annotations

from typing import Any

import requests

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://api.cellxgene.cziscience.com/curation/v1"


def _labels(items: Any) -> list[str]:
    values: list[str] = []
    if not isinstance(items, list):
        return values
    for item in items:
        if isinstance(item, dict) and item.get("label") and item["label"] not in values:
            values.append(item["label"])
        elif isinstance(item, str) and item not in values:
            values.append(item)
    return values


def _normalize_dataset(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_id": raw.get("dataset_id"),
        "title": raw.get("title"),
        "cell_count": raw.get("cell_count"),
        "organism": _labels(raw.get("organism")),
        "tissue": _labels(raw.get("tissue")),
        "cell_type": _labels(raw.get("cell_type")),
        "disease": _labels(raw.get("disease")),
        "assay": _labels(raw.get("assay")),
        "is_primary_data": raw.get("is_primary_data"),
        "feature_count": raw.get("feature_count"),
        "explorer_url": raw.get("explorer_url"),
    }


def fetch_collection(collection_id: str, max_results: int = 5) -> dict[str, Any]:
    """Fetch a CELLxGENE collection by collection ID."""
    clean_id = collection_id.strip()
    if not clean_id:
        raise ValueError("collection_id is required")

    try:
        data = get_json(f"{BASE_URL}/collections/{clean_id}", timeout=60)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            return {"query": clean_id, "found": False, "count": 0, "records": []}
        raise

    datasets = data.get("datasets") or []
    record = {
        "collection_id": data.get("collection_id") or clean_id,
        "collection_name": data.get("name"),
        "description": data.get("description"),
        "collection_url": data.get("collection_url"),
        "doi": data.get("doi"),
        "contact_name": data.get("contact_name"),
        "contact_email": data.get("contact_email"),
        "curator_name": data.get("curator_name"),
        "n_datasets": len(datasets),
        "organisms": sorted({label for dataset in datasets for label in _labels(dataset.get("organism"))}),
        "tissues": sorted({label for dataset in datasets for label in _labels(dataset.get("tissue"))}),
        "cell_types": sorted({label for dataset in datasets for label in _labels(dataset.get("cell_type"))}),
        "diseases": sorted({label for dataset in datasets for label in _labels(dataset.get("disease"))}),
        "datasets": [_normalize_dataset(item) for item in datasets[: max(1, min(int(max_results), 10))] if isinstance(item, dict)],
    }
    return {"query": clean_id, "found": True, "count": 1, "records": [record]}


FETCH_COLLECTION_SPEC = ToolSpec(
    name="cellxgene.fetch_collection",
    description="Fetch a CELLxGENE collection by collection ID and summarize its datasets.",
    input_schema={
        "type": "object",
        "properties": {
            "collection_id": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
        },
        "required": ["collection_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_collection,
)
