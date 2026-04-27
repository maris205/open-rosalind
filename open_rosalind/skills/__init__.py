from __future__ import annotations

import re
from typing import Any, Callable

from ..tools import REGISTRY


_STOPWORDS = {
    "find", "search", "lookup", "look", "up", "show", "list", "give", "me",
    "recent", "latest", "new", "newest", "old", "some",
    "papers", "paper", "publications", "publication", "literature",
    "articles", "article", "studies", "study", "review", "reviews",
    "about", "on", "of", "for", "in", "the", "a", "an", "to",
    "please", "from", "regarding",
    "what", "which", "who", "where", "when", "how", "why",
    "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "tell", "explain", "describe", "summarize", "summary",
    "it", "its", "this", "that", "these", "those",
    "and", "or", "but", "with", "without",
    "located", "location", "cell", "function", "role",
}
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _clean_keywords(text: str) -> str:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", text)
    keep = [t for t in tokens if t.lower() not in _STOPWORDS]
    return " ".join(keep) if keep else text.strip()


def _clean_pubmed_query(text: str) -> str:
    year_match = _YEAR_RE.search(text)
    text_no_year = _YEAR_RE.sub(" ", text)
    q = _clean_keywords(text_no_year)
    if year_match:
        q = f"({q}) AND {year_match.group(0)}[dp]"
    return q


def _run(name: str, trace, **kwargs) -> Any:
    spec = REGISTRY[name]
    trace.log("tool_call", {"tool": name, "args": kwargs})
    try:
        result = spec.handler(**kwargs)
        trace.log("tool_result", {"tool": name, "ok": True, "result": result})
        return result
    except Exception as e:
        err = {"error": type(e).__name__, "message": str(e)}
        trace.log("tool_result", {"tool": name, "ok": False, "error": err})
        return {"error": err}


def sequence_basic_analysis(payload: dict, trace) -> dict:
    """Demo 1 pipeline: sequence → basic_analysis → (UniProt for proteins) → summary."""
    stats = _run("sequence.analyze", trace, sequence=payload["sequence"])
    out: dict[str, Any] = {"sequence_stats": stats}
    # If we got a single protein record, try to find a homolog via UniProt BLAST-lite
    # (a free-text search on a leading 30-mer is a cheap stand-in until we wire
    # a real BLAST tool in v0.2).
    recs = stats.get("records", []) if isinstance(stats, dict) else []
    if len(recs) == 1 and recs[0].get("type") == "protein" and recs[0].get("length", 0) >= 25:
        seq_text = payload["sequence"]
        first_record_seq = recs[0]
        probe = _extract_seq_for_probe(seq_text)[:30]
        if probe:
            out["uniprot_hint"] = _run("uniprot.search", trace, query=probe, size=3)
    return out


def mutation_effect(payload: dict, trace) -> dict:
    """Demo 2: compare WT vs mutant (or apply HGVS) and annotate differences."""
    return {
        "mutation": _run(
            "mutation.diff",
            trace,
            wild_type=payload["wild_type"],
            mutant=payload.get("mutant"),
            mutation=payload.get("mutation"),
        ),
    }


def _extract_seq_for_probe(text: str) -> str:
    """Strip FASTA header and whitespace to get a clean residue string."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    body = []
    for ln in lines:
        if ln.startswith(">"):
            parts = ln[1:].split(None, 1)
            if len(parts) == 2:
                body.append(parts[1])
            continue
        body.append(ln)
    return re.sub(r"[^A-Za-z]", "", "".join(body)).upper()


def uniprot_lookup(payload: dict, trace) -> dict:
    out: dict[str, Any] = {}
    if "accession" in payload:
        out["entry"] = _run("uniprot.fetch", trace, accession=payload["accession"])
    raw = payload["query"]
    cleaned = _clean_keywords(raw) if not payload.get("accession") else raw
    if cleaned != raw:
        trace.log("query_cleaned", {"raw": raw, "cleaned": cleaned})
    out["search"] = _run("uniprot.search", trace, query=cleaned, size=5)
    return out


def literature_search(payload: dict, trace) -> dict:
    raw = payload["query"]
    cleaned = _clean_pubmed_query(raw)
    trace.log("query_cleaned", {"raw": raw, "cleaned": cleaned})
    return {
        "pubmed": _run("pubmed.search", trace, query=cleaned, max_results=5),
    }


SKILL_REGISTRY: dict[str, Callable[[dict, Any], dict]] = {
    "sequence_basic_analysis": sequence_basic_analysis,
    "uniprot_lookup": uniprot_lookup,
    "literature_search": literature_search,
    "mutation_effect": mutation_effect,
}
