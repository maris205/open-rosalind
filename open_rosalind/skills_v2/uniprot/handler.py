"""UniProt lookup skill handler."""
from __future__ import annotations

from typing import Any

from . import tools


def handler(payload: dict, trace: Any) -> dict:
    """
    Query UniProt for protein information.

    Args:
        payload: {"query": str} or {"accession": str}
        trace: Trace logger

    Returns:
        {annotation, confidence, notes, entry}
    """
    query = payload.get("query", "").strip()
    accession = payload.get("accession", "").strip()

    if not query and not accession:
        return {
            "annotation": {"kind": "protein"},
            "confidence": 0.0,
            "notes": ["Empty query"],
            "entry": {},
        }

    notes = []

    # Direct accession fetch
    if accession or (query and query.isupper() and len(query) <= 10):
        acc = accession or query
        try:
            entry = tools.fetch(accession=acc)
            return {
                "annotation": {
                    "kind": "protein",
                    "accession": entry["accession"],
                    "name": entry["name"],
                    "organism": entry["organism"],
                },
                "confidence": 0.9,
                "notes": notes,
                "entry": entry,
            }
        except Exception as e:
            notes.append(f"Fetch failed: {e}, trying search")

    # Fallback: search by name
    try:
        results = tools.search(query=query, max_results=5)
        if not results["hits"]:
            return {
                "annotation": {"kind": "protein"},
                "confidence": 0.0,
                "notes": ["No results found"],
                "entry": {},
            }

        top = results["hits"][0]
        notes.append(f"Used search, top hit: {top['accession']}")

        # Fetch full entry for top hit
        entry = tools.fetch(accession=top["accession"])

        return {
            "annotation": {
                "kind": "protein",
                "accession": entry["accession"],
                "name": entry["name"],
                "organism": entry["organism"],
            },
            "confidence": 0.7,
            "notes": notes,
            "entry": entry,
        }
    except Exception as e:
        return {
            "annotation": {"kind": "protein"},
            "confidence": 0.0,
            "notes": [f"Search failed: {e}"],
            "entry": {},
        }
