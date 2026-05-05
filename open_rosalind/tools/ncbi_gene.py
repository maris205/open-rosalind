"""NCBI Gene E-utilities client."""
from __future__ import annotations

from typing import Any

from ._http import get_json
from .base import ToolSpec

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _species_name(species: str) -> str:
    clean = " ".join(species.replace("_", " ").split())
    if not clean:
        return "Homo sapiens"
    parts = clean.split(" ")
    if len(parts) == 1:
        return parts[0]
    return " ".join([parts[0].capitalize(), *[part.lower() for part in parts[1:]]])


def _split_csv(text: str | None) -> list[str]:
    if not text:
        return []
    values: list[str] = []
    for part in text.split(","):
        item = part.strip()
        if item and item not in values:
            values.append(item)
    return values


def search_gene(query: str, species: str = "Homo sapiens", max_results: int = 3) -> dict[str, Any]:
    """Search NCBI Gene IDs by symbol or free-text query."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query is required")

    clean_species = _species_name(species)
    term = f"{clean_query}[gene] AND {clean_species}[organism]"
    data = get_json(
        f"{BASE_URL}/esearch.fcgi",
        params={"db": "gene", "term": term, "retmode": "json", "retmax": max_results},
        timeout=30,
    )
    result = data.get("esearchresult", {})
    ids = [str(gene_id) for gene_id in result.get("idlist", []) if str(gene_id).strip()]
    return {
        "query": clean_query,
        "species": clean_species,
        "count": len(ids),
        "ids": ids,
        "query_translation": result.get("querytranslation"),
    }


def fetch_gene(gene_id: str) -> dict[str, Any]:
    """Fetch a compact NCBI Gene summary by Gene ID."""
    clean_id = gene_id.strip()
    if not clean_id:
        raise ValueError("gene_id is required")

    data = get_json(
        f"{BASE_URL}/esummary.fcgi",
        params={"db": "gene", "id": clean_id, "retmode": "json"},
        timeout=30,
    )
    result = data.get("result", {})
    raw = result.get(clean_id) or {}
    if not raw or raw.get("error"):
        return {"gene_id": clean_id, "found": False}

    genomic_info = (raw.get("genomicinfo") or [{}])[0]
    chr_start = genomic_info.get("chrstart")
    chr_stop = genomic_info.get("chrstop")
    if isinstance(chr_start, int) and isinstance(chr_stop, int):
        start = min(chr_start, chr_stop)
        end = max(chr_start, chr_stop)
        strand = -1 if chr_start > chr_stop else 1
    else:
        start = None
        end = None
        strand = None

    symbol = raw.get("nomenclaturesymbol") or raw.get("name")
    return {
        "gene_id": clean_id,
        "found": True,
        "symbol": symbol,
        "name": raw.get("name"),
        "description": raw.get("description"),
        "summary": raw.get("summary"),
        "species": (raw.get("organism") or {}).get("scientificname"),
        "chromosome": raw.get("chromosome"),
        "map_location": raw.get("maplocation"),
        "aliases": _split_csv(raw.get("otheraliases")),
        "other_designations": _split_csv(raw.get("otherdesignations")),
        "nomenclature_name": raw.get("nomenclaturename"),
        "nomenclature_status": raw.get("nomenclaturestatus"),
        "mim_ids": [str(item) for item in raw.get("mim") or [] if str(item).strip()],
        "genomic_location": {
            "chraccver": genomic_info.get("chraccver"),
            "chromosome": genomic_info.get("chrloc") or raw.get("chromosome"),
            "start": start,
            "end": end,
            "strand": strand,
            "exon_count": genomic_info.get("exoncount"),
        },
        "url": f"https://www.ncbi.nlm.nih.gov/gene/{clean_id}",
    }


SEARCH_GENE_SPEC = ToolSpec(
    name="ncbi_gene.search_gene",
    description="Search NCBI Gene by symbol or free-text query and return matching Gene IDs.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "species": {"type": "string", "default": "Homo sapiens"},
            "max_results": {"type": "integer", "default": 3, "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    handler=search_gene,
)


FETCH_GENE_SPEC = ToolSpec(
    name="ncbi_gene.fetch_gene",
    description="Fetch a compact NCBI Gene summary by Gene ID.",
    input_schema={
        "type": "object",
        "properties": {"gene_id": {"type": "string"}},
        "required": ["gene_id"],
    },
    output_schema={"type": "object"},
    handler=fetch_gene,
)
