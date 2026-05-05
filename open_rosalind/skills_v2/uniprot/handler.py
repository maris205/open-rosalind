"""UniProt lookup skill handler."""
from __future__ import annotations

import re
from typing import Any

from . import tools
from ..runtime import ensure_trace, is_error, run_tool

_STOPWORDS = {
    "find", "search", "lookup", "look", "up", "show", "list", "give", "me",
    "about", "on", "of", "for", "in", "the", "a", "an", "to",
    "please", "from", "regarding",
    "what", "which", "who", "where", "when", "how", "why",
    "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "tell", "explain", "describe", "summarize", "summary",
    "it", "its", "this", "that", "these", "those",
    "and", "or", "but", "with", "without",
    "located", "location", "cell", "function", "role",
    "information", "info", "details", "detail", "data", "knowledge",
    "characterize", "characterise", "analyze", "analyse", "analysis", "evaluate",
    "effect", "effects", "impact", "impacts", "consequences",
    "concerning", "related", "isoform", "variant", "form",
    "background", "context", "overview", "current", "available",
    "known", "reported", "characterization", "evaluation", "assessment",
    "mechanism", "mechanisms", "molecular", "humans",
}
_ACCESSION_RE = re.compile(
    r"\b([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})\b"
)
_GENE_SYMBOL_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,7})\b")


def _clean_query(text: str) -> str:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", text)
    keep = [token for token in tokens if token.lower() not in _STOPWORDS]
    return " ".join(keep) if keep else text.strip()


def _extract_gene_symbol(text: str) -> str | None:
    for token in _GENE_SYMBOL_RE.findall(text):
        if token not in {"WT", "MT", "DNA", "RNA", "AA", "NT"}:
            return token
    return None


def _mentions_human(text: str) -> bool:
    lowered = text.lower()
    return "human" in lowered or "humans" in lowered or "homo sapiens" in lowered


def _best_hit(hits: list[dict[str, Any]]) -> dict[str, Any] | None:
    for hit in hits:
        if hit.get("organism") == "Homo sapiens":
            return hit
    return hits[0] if hits else None


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
    trace = ensure_trace(trace)
    search: dict[str, Any] = {}
    entry: dict[str, Any] = {}

    # Direct accession fetch
    if accession or (query and _ACCESSION_RE.search(query)):
        acc = accession or query
        entry = run_tool(trace, "uniprot.fetch", tools.fetch, accession=acc)
        if is_error(entry):
            notes.append(f"Fetch failed: {entry['error']['message']}, trying search")
            entry = {}

    if query:
        cleaned_query = query if accession else _clean_query(query)
        if cleaned_query != query:
            trace.log("query_cleaned", {"raw": query, "cleaned": cleaned_query})
        search = run_tool(trace, "uniprot.search", tools.search, query=cleaned_query, max_results=5)
        if is_error(search):
            error = search["error"]["message"]
            search = {}
            notes.append(f"Search failed: {error}")

        gene_symbol = _extract_gene_symbol(cleaned_query)
        if gene_symbol and not accession:
            gene_query = f'gene_exact:{gene_symbol}'
            if _mentions_human(query):
                gene_query += ' AND organism_name:"Homo sapiens"'
            trace.log("fallback", {"reason": f"gene-specific UniProt search for {gene_symbol}"})
            gene_results = run_tool(trace, "uniprot.search", tools.search, query=gene_query, max_results=5)
            if not is_error(gene_results) and gene_results.get("hits"):
                search = gene_results
                notes.append(f"Used gene-specific search fallback for {gene_symbol}")

    hits = search.get("hits") or []

    if not entry and hits:
        top = _best_hit(hits)
        if top is not None:
            notes.append(f"Used search, top hit: {top['accession']}")
            fetched = run_tool(trace, "uniprot.fetch", tools.fetch, accession=top["accession"])
            if is_error(fetched):
                return {
                    "annotation": {"kind": "protein"},
                    "confidence": 0.0,
                    "notes": notes + [f"Top-hit fetch failed: {fetched['error']['message']}"],
                    "entry": {},
                    "search": search,
                }
            entry = fetched

    if not entry and not hits:
        return {
            "annotation": {"kind": "protein"},
            "confidence": 0.0,
            "notes": notes + ["No results found"],
            "entry": {},
            "search": search,
        }

    annotation_source = entry or _best_hit(hits) or {}
    return {
        "annotation": {
            "kind": "protein",
            "accession": annotation_source.get("accession"),
            "name": annotation_source.get("name"),
            "organism": annotation_source.get("organism"),
        },
        "confidence": 0.95 if entry and accession else (0.85 if entry else 0.6),
        "notes": notes,
        "entry": entry,
        "search": search,
    }
