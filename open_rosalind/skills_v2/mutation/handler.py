"""Mutation effect handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace, is_error, run_tool
from ..uniprot import tools as uniprot_tools
from . import tools


def _mutation_confidence(diff: dict[str, Any]) -> float:
    n_differences = diff.get("n_differences", 0)
    if n_differences == 0:
        return 0.5
    has_high = any(item.get("severity") == "high" for item in diff.get("differences", []))
    return 0.85 if has_high else 0.7


def _notable_flags(differences: list[dict[str, Any]]) -> list[str]:
    flags: list[str] = []
    for difference in differences:
        for flag in difference.get("flags", []):
            if flag not in flags:
                flags.append(flag)
    return flags


def _pick_best_hit(hits: list[dict[str, Any]]) -> dict[str, Any] | None:
    for hit in hits:
        if hit.get("organism") == "Homo sapiens":
            return hit
    return hits[0] if hits else None


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    trace = ensure_trace(trace)
    notes: list[str] = []

    wild_type = str(payload.get("wt") or payload.get("wild_type") or "").strip()
    mutant = str(payload.get("mt") or payload.get("mutant") or "").strip() or None
    mutation = str(payload.get("mutation") or "").strip() or None
    gene_symbol = str(payload.get("gene_symbol") or "").strip()

    search: dict[str, Any] = {}
    entry: dict[str, Any] = {}
    accession: str | None = None

    if not wild_type and gene_symbol:
        search = run_tool(trace, "uniprot.search", uniprot_tools.search, query=gene_symbol, max_results=5)
        if is_error(search):
            return {
                "annotation": {"kind": "mutation", "gene_symbol": gene_symbol},
                "confidence": 0.0,
                "notes": [f"Gene resolution failed: {search['error']['message']}"],
                "mutation": {},
                "protein_context": {"gene_symbol": gene_symbol, "search": {}},
            }

        top_hit = _pick_best_hit(search.get("hits") or [])
        if top_hit is None or not top_hit.get("accession"):
            return {
                "annotation": {"kind": "mutation", "gene_symbol": gene_symbol},
                "confidence": 0.0,
                "notes": [f"Could not resolve gene symbol {gene_symbol!r} to a UniProt entry"],
                "mutation": {},
                "protein_context": {"gene_symbol": gene_symbol, "search": search},
            }

        accession = top_hit["accession"]
        entry = run_tool(trace, "uniprot.fetch", uniprot_tools.fetch, accession=accession)
        if is_error(entry):
            return {
                "annotation": {"kind": "mutation", "gene_symbol": gene_symbol, "accession": accession},
                "confidence": 0.0,
                "notes": [f"UniProt fetch failed for {accession}: {entry['error']['message']}"],
                "mutation": {},
                "protein_context": {"gene_symbol": gene_symbol, "accession": accession, "search": search},
            }

        wild_type = str(entry.get("sequence") or "").strip()
        if not wild_type:
            return {
                "annotation": {"kind": "mutation", "gene_symbol": gene_symbol, "accession": accession},
                "confidence": 0.0,
                "notes": [f"UniProt entry {accession} did not include a canonical sequence"],
                "mutation": {},
                "protein_context": {
                    "gene_symbol": gene_symbol,
                    "accession": accession,
                    "search": search,
                    "entry": entry,
                },
            }

        resolved_name = entry.get("name") or top_hit.get("name") or accession
        resolved_organism = entry.get("organism") or top_hit.get("organism")
        organism_note = f", {resolved_organism}" if resolved_organism else ""
        notes.append(f"Resolved gene symbol {gene_symbol!r} to UniProt {accession} ({resolved_name}{organism_note})")

    if not wild_type:
        return {
            "annotation": {"kind": "mutation", "gene_symbol": gene_symbol or None},
            "confidence": 0.0,
            "notes": ["Missing wild-type sequence or resolvable gene_symbol"],
            "mutation": {},
            "protein_context": {"gene_symbol": gene_symbol or None},
        }

    if not mutant and not mutation:
        return {
            "annotation": {"kind": "mutation", "gene_symbol": gene_symbol or None, "accession": accession},
            "confidence": 0.0,
            "notes": ["Missing mutant sequence or HGVS mutation"],
            "mutation": {},
            "protein_context": {
                "gene_symbol": gene_symbol or None,
                "accession": accession,
                "search": search,
                "entry": entry,
            },
        }

    diff = run_tool(
        trace,
        "mutation.diff",
        tools.diff,
        wild_type=wild_type,
        mutant=mutant,
        mutation=mutation,
    )
    if is_error(diff):
        return {
            "annotation": {"kind": "mutation", "gene_symbol": gene_symbol or None, "accession": accession},
            "confidence": 0.0,
            "notes": [f"Mutation diff failed: {diff['error']['message']}"],
            "mutation": {},
            "protein_context": {
                "gene_symbol": gene_symbol or None,
                "accession": accession,
                "search": search,
                "entry": entry,
            },
        }

    if diff.get("n_differences") == 0:
        notes.append("Wild-type and mutant inputs are identical")

    protein_context = {
        "gene_symbol": gene_symbol or None,
        "accession": entry.get("accession") or accession,
        "name": entry.get("name"),
        "organism": entry.get("organism"),
        "search": search,
        "entry": entry,
    }

    return {
        "annotation": {
            "kind": "mutation",
            "gene_symbol": gene_symbol or None,
            "accession": protein_context["accession"],
            "n_differences": diff.get("n_differences", 0),
            "overall_assessment": diff.get("overall_assessment"),
            "notable_flags": _notable_flags(diff.get("differences", [])),
        },
        "confidence": _mutation_confidence(diff),
        "notes": notes,
        "mutation": diff,
        "protein_context": protein_context,
    }
