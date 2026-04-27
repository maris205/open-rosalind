"""UniProt REST API client.

Reference: https://www.uniprot.org/help/api
"""
from __future__ import annotations

from typing import Any

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://rest.uniprot.org"


def search(query: str, size: int = 5, fields: str | None = None) -> dict[str, Any]:
    """Search UniProtKB and return compact records."""
    if fields is None:
        fields = "accession,id,protein_name,organism_name,length,gene_names,cc_function,ft_domain"
    params = {"query": query, "format": "json", "size": size, "fields": fields}
    data = get_json(f"{BASE_URL}/uniprotkb/search", params=params, timeout=30)
    out = []
    for entry in data.get("results", []):
        protein_names = entry.get("proteinDescription", {}).get("recommendedName", {})
        rec_name = protein_names.get("fullName", {}).get("value")
        organism = entry.get("organism", {}).get("scientificName")
        function_texts = []
        for c in entry.get("comments", []) or []:
            if c.get("commentType") == "FUNCTION":
                for t in c.get("texts", []) or []:
                    if t.get("value"):
                        function_texts.append(t["value"])
        out.append({
            "accession": entry.get("primaryAccession"),
            "id": entry.get("uniProtkbId"),
            "name": rec_name,
            "organism": organism,
            "length": entry.get("sequence", {}).get("length"),
            "function": " ".join(function_texts)[:600] if function_texts else None,
        })
    return {"query": query, "count": len(out), "hits": out}


def fetch(accession: str) -> dict[str, Any]:
    """Fetch a single UniProt entry by accession."""
    e = get_json(f"{BASE_URL}/uniprotkb/{accession}.json", timeout=30)
    rec_name = e.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value")
    function_texts = []
    for c in e.get("comments", []) or []:
        if c.get("commentType") == "FUNCTION":
            for t in c.get("texts", []) or []:
                if t.get("value"):
                    function_texts.append(t["value"])
    return {
        "accession": e.get("primaryAccession"),
        "id": e.get("uniProtkbId"),
        "name": rec_name,
        "organism": e.get("organism", {}).get("scientificName"),
        "length": e.get("sequence", {}).get("length"),
        "sequence": e.get("sequence", {}).get("value"),
        "function": " ".join(function_texts) if function_texts else None,
    }


SEARCH_SPEC = ToolSpec(
    name="uniprot.search",
    description="Search UniProtKB for proteins by free-text query (gene name, protein name, organism, accession). Returns up to N compact records.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "size": {"type": "integer", "default": 5, "minimum": 1, "maximum": 25},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search,
)

FETCH_SPEC = ToolSpec(
    name="uniprot.fetch",
    description="Fetch a single UniProt entry (function, organism, sequence) by accession (e.g. P38398).",
    input_schema={
        "type": "object",
        "properties": {"accession": {"type": "string"}},
        "required": ["accession"],
    },
    output_schema={"type": "object"},
    handler=fetch,
)
