"""Protein structure summary handler."""
from __future__ import annotations

from typing import Any

from ...tools import alphafold as alphafold_tools
from ..runtime import ensure_trace, is_error, run_tool
from ..uniprot import tools as uniprot_tools


def _pick_best_hit(hits: list[dict[str, Any]]) -> dict[str, Any] | None:
    for hit in hits:
        if hit.get("organism") == "Homo sapiens":
            return hit
    return hits[0] if hits else None


def _pick_primary_model(models: list[dict[str, Any]], accession: str) -> dict[str, Any] | None:
    exact_matches = [model for model in models if model.get("uniprot_accession") == accession]
    candidates = exact_matches or models
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda model: (
            int(bool(model.get("is_reviewed"))),
            int(bool(model.get("is_reference_proteome"))),
            int(model.get("sequence_length") or 0),
            float(model.get("mean_plddt") or 0.0),
        ),
        reverse=True,
    )[0]


def _model_confidence(model: dict[str, Any] | None) -> float:
    if not model:
        return 0.0
    mean_plddt = float(model.get("mean_plddt") or 0.0)
    if mean_plddt <= 0:
        return 0.7
    return round(min(max(mean_plddt / 100.0, 0.35), 0.95), 2)


def handler(payload: dict[str, Any], trace: Any) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    accession = str(payload.get("accession") or "").strip()
    max_models = int(payload.get("max_models", 3) or 3)
    if not query and not accession:
        return {
            "annotation": {"kind": "protein_structure", "n_models": 0},
            "confidence": 0.0,
            "notes": ["Missing protein query or accession"],
            "entry": {},
            "search": {},
            "structure": {"count": 0, "models": []},
        }

    trace = ensure_trace(trace)
    notes: list[str] = []
    search: dict[str, Any] = {}
    entry: dict[str, Any] = {}
    resolved_accession = accession

    if not resolved_accession:
        search = run_tool(trace, "uniprot.search", uniprot_tools.search, query=query, max_results=5)
        if is_error(search):
            return {
                "annotation": {"kind": "protein_structure", "n_models": 0},
                "confidence": 0.0,
                "notes": [f"UniProt search failed: {search['error']['message']}"],
                "entry": {},
                "search": {},
                "structure": {"count": 0, "models": []},
            }

        top_hit = _pick_best_hit(search.get("hits") or [])
        if top_hit is None or not top_hit.get("accession"):
            return {
                "annotation": {"kind": "protein_structure", "n_models": 0, "query": query},
                "confidence": 0.0,
                "notes": [f"Could not resolve protein query {query!r} to a UniProt accession"],
                "entry": {},
                "search": search,
                "structure": {"count": 0, "models": []},
            }
        resolved_accession = str(top_hit["accession"])
        notes.append(f"Resolved query {query!r} to UniProt {resolved_accession}")

    fetch_result = run_tool(trace, "uniprot.fetch", uniprot_tools.fetch, accession=resolved_accession)
    if is_error(fetch_result):
        notes.append(f"UniProt fetch failed for {resolved_accession}: {fetch_result['error']['message']}")
    else:
        entry = fetch_result

    structure_result = run_tool(
        trace,
        "alphafold.fetch_prediction",
        alphafold_tools.fetch_prediction,
        accession=resolved_accession,
    )
    if is_error(structure_result):
        return {
            "annotation": {
                "kind": "protein_structure",
                "accession": resolved_accession,
                "name": entry.get("name"),
                "organism": entry.get("organism"),
                "n_models": 0,
            },
            "confidence": 0.0,
            "notes": notes + [f"AlphaFold lookup failed: {structure_result['error']['message']}"],
            "entry": entry,
            "search": search,
            "structure": {"count": 0, "models": []},
        }

    models = list(structure_result.get("models") or [])
    primary_model = _pick_primary_model(models, resolved_accession)
    if primary_model is None:
        notes.append(f"No AlphaFold structure models found for {resolved_accession}")

    limited_models = models[: max(max_models, 1)]
    return {
        "annotation": {
            "kind": "protein_structure",
            "accession": entry.get("accession") or resolved_accession,
            "name": entry.get("name"),
            "organism": entry.get("organism"),
            "length": entry.get("length"),
            "structure_source": "AlphaFold DB",
            "model_id": primary_model.get("entry_id") if primary_model else None,
            "mean_plddt": primary_model.get("mean_plddt") if primary_model else None,
            "high_confidence_fraction": (
                (primary_model.get("fractions") or {}).get("very_high") if primary_model else None
            ),
            "n_models": structure_result.get("count", 0),
        },
        "confidence": _model_confidence(primary_model),
        "notes": notes,
        "entry": entry,
        "search": search,
        "structure": {
            "accession": resolved_accession,
            "count": structure_result.get("count", 0),
            "primary_model": primary_model,
            "models": limited_models,
        },
    }
