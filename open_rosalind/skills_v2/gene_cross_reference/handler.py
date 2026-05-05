"""Gene cross-reference aggregation handler."""
from __future__ import annotations

from typing import Any

from ...tools import ensembl as ensembl_tools
from ...tools import ncbi_gene as ncbi_gene_tools
from ..runtime import ensure_trace, is_error, run_tool


def _unique_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in unique:
            unique.append(item)
    return unique


def _first_db_ids(records: list[dict[str, Any]], dbname: str, field: str = "primary_id") -> list[str]:
    values: list[str] = []
    for record in records:
        if record.get("dbname") != dbname:
            continue
        raw = record.get(field)
        if raw is None:
            continue
        item = str(raw).strip()
        if item and item not in values:
            values.append(item)
    return values


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or payload.get("symbol") or payload.get("gene_symbol") or "").strip()
    species = str(payload.get("species") or "homo_sapiens").strip() or "homo_sapiens"

    if not query:
        return {
            "annotation": {"kind": "gene_cross_reference", "n_records": 0},
            "confidence": 0.0,
            "notes": ["Missing gene cross-reference query"],
            "evidence": [],
            "ensembl_gene": {},
            "ncbi_gene": {},
            "cross_references": {},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    evidence: list[dict[str, Any]] = []

    ensembl_result = run_tool(trace, "ensembl.lookup_gene", ensembl_tools.lookup_gene, symbol=query, species=species)
    if is_error(ensembl_result):
        return {
            "annotation": {"kind": "gene_cross_reference", "query": query, "n_records": 0},
            "confidence": 0.0,
            "notes": [f"Ensembl gene lookup failed: {ensembl_result['error']['message']}"],
            "evidence": evidence,
            "ensembl_gene": {},
            "ncbi_gene": {},
            "cross_references": {},
        }
    evidence.append({"step": "ensembl.lookup_gene", "result": ensembl_result})
    if not ensembl_result.get("found", True):
        return {
            "annotation": {"kind": "gene_cross_reference", "query": query, "n_records": 0},
            "confidence": 0.0,
            "notes": [f"No Ensembl gene was found for {query!r}"],
            "evidence": evidence,
            "ensembl_gene": ensembl_result,
            "ncbi_gene": {},
            "cross_references": {},
        }

    ensembl_gene_id = str(ensembl_result.get("ensembl_gene_id") or "").strip()
    xrefs_result = run_tool(trace, "ensembl.fetch_xrefs", ensembl_tools.fetch_xrefs, ensembl_id=ensembl_gene_id)
    xref_records: list[dict[str, Any]] = []
    if is_error(xrefs_result):
        notes.append(f"Ensembl xref fetch failed: {xrefs_result['error']['message']}")
        xrefs_result = {"ensembl_id": ensembl_gene_id, "count": 0, "records": []}
    else:
        evidence.append({"step": "ensembl.fetch_xrefs", "result": xrefs_result})
        xref_records = list(xrefs_result.get("records") or [])

    entrez_ids = _first_db_ids(xref_records, "EntrezGene")
    hgnc_ids = _first_db_ids(xref_records, "HGNC")
    omim_ids = _first_db_ids(xref_records, "MIM_GENE")
    ensembl_symbol = str(ensembl_result.get("symbol") or query)

    ncbi_result: dict[str, Any] = {}
    resolved_gene_id = str(payload.get("gene_id") or "").strip()
    if not resolved_gene_id and entrez_ids:
        resolved_gene_id = entrez_ids[0]
        notes.append(f"Resolved NCBI Gene ID {resolved_gene_id} from Ensembl cross-references")
    if not resolved_gene_id:
        search_result = run_tool(
            trace,
            "ncbi_gene.search_gene",
            ncbi_gene_tools.search_gene,
            query=ensembl_symbol,
            species=ensembl_result.get("species", species),
            max_results=3,
        )
        if is_error(search_result):
            notes.append(f"NCBI Gene search failed: {search_result['error']['message']}")
        else:
            evidence.append({"step": "ncbi_gene.search_gene", "result": search_result})
            resolved_gene_id = str((search_result.get("ids") or [""])[0]).strip()
            if resolved_gene_id:
                notes.append(f"Resolved NCBI Gene ID {resolved_gene_id} from NCBI Gene search")

    if resolved_gene_id:
        fetched_gene = run_tool(trace, "ncbi_gene.fetch_gene", ncbi_gene_tools.fetch_gene, gene_id=resolved_gene_id)
        if is_error(fetched_gene):
            notes.append(f"NCBI Gene fetch failed: {fetched_gene['error']['message']}")
        else:
            ncbi_result = fetched_gene
            evidence.append({"step": "ncbi_gene.fetch_gene", "result": ncbi_result})

    aliases = _unique_strings(
        (ensembl_result.get("symbol") and [str(ensembl_result["symbol"])]) or []
        + [str(record.get("display_id") or "") for record in xref_records if record.get("dbname") == "HGNC"]
        + [str(alias) for alias in (ncbi_result.get("aliases") or [])]
    )
    combined_omim_ids = _unique_strings(omim_ids + [str(item) for item in (ncbi_result.get("mim_ids") or [])])

    return {
        "annotation": {
            "kind": "gene_cross_reference",
            "symbol": ncbi_result.get("symbol") or ensembl_result.get("symbol") or query,
            "species": ncbi_result.get("species") or ensembl_result.get("species"),
            "ensembl_gene_id": ensembl_gene_id,
            "ncbi_gene_id": ncbi_result.get("gene_id") or (entrez_ids[0] if entrez_ids else None),
            "canonical_transcript": ensembl_result.get("canonical_transcript"),
            "biotype": ensembl_result.get("biotype"),
            "chromosome": ncbi_result.get("chromosome") or ensembl_result.get("seq_region_name"),
            "map_location": ncbi_result.get("map_location"),
            "hgnc_ids": hgnc_ids,
            "omim_ids": combined_omim_ids,
        },
        "confidence": 0.91 if ncbi_result else 0.82,
        "notes": notes,
        "evidence": evidence,
        "ensembl_gene": ensembl_result,
        "ncbi_gene": ncbi_result,
        "cross_references": {
            "count": xrefs_result.get("count", 0),
            "hgnc_ids": hgnc_ids,
            "entrez_ids": entrez_ids,
            "omim_ids": combined_omim_ids,
            "aliases": aliases,
            "records": xref_records[:25],
        },
    }
