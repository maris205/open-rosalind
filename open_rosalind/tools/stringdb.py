"""STRING network client."""
from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from ._http import make_session
from .base import ToolSpec

BASE_URL = "https://string-db.org/api/tsv"


def _normalize_identifiers(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        tokens = value.replace("\n", ",").replace("\r", ",").split(",")
    elif isinstance(value, list):
        tokens = [str(item) for item in value]
    else:
        raise ValueError("identifiers must be a string or list of strings")
    identifiers = [token.strip() for token in tokens if token and token.strip()]
    if not identifiers:
        raise ValueError("at least one identifier is required")
    return identifiers


def _coerce_number(value: str | None) -> int | float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def _normalize_row(raw: dict[str, str]) -> dict[str, Any]:
    return {
        "string_id_a": raw.get("stringId_A"),
        "string_id_b": raw.get("stringId_B"),
        "preferred_name_a": raw.get("preferredName_A"),
        "preferred_name_b": raw.get("preferredName_B"),
        "ncbi_taxon_id": _coerce_number(raw.get("ncbiTaxonId")),
        "score": _coerce_number(raw.get("score")),
        "nscore": _coerce_number(raw.get("nscore")),
        "fscore": _coerce_number(raw.get("fscore")),
        "pscore": _coerce_number(raw.get("pscore")),
        "ascore": _coerce_number(raw.get("ascore")),
        "escore": _coerce_number(raw.get("escore")),
        "dscore": _coerce_number(raw.get("dscore")),
        "tscore": _coerce_number(raw.get("tscore")),
    }


def _post_rows(path: str, form_body: dict[str, Any]) -> list[dict[str, Any]]:
    session = make_session()
    try:
        response = session.post(f"{BASE_URL}/{path}", data=form_body, timeout=30)
        response.raise_for_status()
    finally:
        session.close()

    text = response.text.strip()
    if not text:
        return []
    reader = csv.DictReader(StringIO(text), delimiter="\t")
    return [_normalize_row(row) for row in reader if row]


def _network_url(identifiers: list[str], species: int) -> str:
    joined = "%0D".join(identifiers)
    return f"https://string-db.org/cgi/network?identifiers={joined}&species={species}"


def interaction_partners(
    identifiers: str | list[str],
    species: int = 9606,
    limit: int = 10,
    required_score: int = 400,
    network_type: str = "functional",
    caller_identity: str = "open-rosalind",
) -> dict[str, Any]:
    """Fetch STRING interaction partners for one or more identifiers."""
    clean_identifiers = _normalize_identifiers(identifiers)
    form_body: dict[str, Any] = {
        "species": species,
        "limit": limit,
        "required_score": required_score,
        "network_type": network_type,
        "caller_identity": caller_identity,
    }
    if len(clean_identifiers) == 1:
        form_body["identifier"] = clean_identifiers[0]
    else:
        form_body["identifiers"] = "\r".join(clean_identifiers)
    records = _post_rows(
        "interaction_partners",
        form_body,
    )
    return {
        "mode": "interaction_partners",
        "query_identifiers": clean_identifiers,
        "species": species,
        "count": len(records),
        "records": records,
        "url": _network_url(clean_identifiers, species),
    }


def network(
    identifiers: str | list[str],
    species: int = 9606,
    required_score: int = 400,
    network_type: str = "functional",
    add_nodes: int = 0,
    caller_identity: str = "open-rosalind",
) -> dict[str, Any]:
    """Fetch STRING network edges for one or more identifiers."""
    clean_identifiers = _normalize_identifiers(identifiers)
    records = _post_rows(
        "network",
        {
            "identifiers": "\r".join(clean_identifiers),
            "species": species,
            "required_score": required_score,
            "network_type": network_type,
            "add_nodes": add_nodes,
            "caller_identity": caller_identity,
        },
    )
    return {
        "mode": "network",
        "query_identifiers": clean_identifiers,
        "species": species,
        "count": len(records),
        "records": records,
        "url": _network_url(clean_identifiers, species),
    }


INTERACTION_PARTNERS_SPEC = ToolSpec(
    name="string.interaction_partners",
    description="Fetch STRING interaction partners for one or more gene/protein identifiers.",
    input_schema={
        "type": "object",
        "properties": {
            "identifiers": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ]
            },
            "species": {"type": "integer", "default": 9606},
            "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            "required_score": {"type": "integer", "default": 400, "minimum": 0, "maximum": 1000},
            "network_type": {"type": "string", "default": "functional"},
        },
        "required": ["identifiers"],
    },
    output_schema={"type": "object"},
    handler=interaction_partners,
)


NETWORK_SPEC = ToolSpec(
    name="string.network",
    description="Fetch STRING network edges among one or more gene/protein identifiers.",
    input_schema={
        "type": "object",
        "properties": {
            "identifiers": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ]
            },
            "species": {"type": "integer", "default": 9606},
            "required_score": {"type": "integer", "default": 400, "minimum": 0, "maximum": 1000},
            "network_type": {"type": "string", "default": "functional"},
            "add_nodes": {"type": "integer", "default": 0, "minimum": 0, "maximum": 25},
        },
        "required": ["identifiers"],
    },
    output_schema={"type": "object"},
    handler=network,
)
