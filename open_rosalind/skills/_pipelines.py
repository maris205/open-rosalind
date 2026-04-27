from __future__ import annotations

import re
from typing import Any, Callable

from ..tools import REGISTRY


# --------- text cleaning helpers (shared by uniprot / pubmed pipelines) ----------

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


# --------- error-safe tool runner --------------------------------------------------

def _run(name: str, trace, **kwargs) -> Any:
    """Call a tool. Always returns a dict; never raises. On failure, returns
    {'error': {...}} so pipelines can detect it and fall back / continue."""
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


def _is_error(result: Any) -> bool:
    return isinstance(result, dict) and "error" in result and len(result) == 1


# --------- pipelines ---------------------------------------------------------------

def sequence_basic_analysis(payload: dict, trace) -> dict:
    """Pipeline:
        sequence.analyze
        → (if single protein ≥25aa) uniprot.search on first 30aa probe
        → (if 0 hits) retry with 20aa, then 15aa
        → aggregate annotation + confidence
    """
    notes: list[str] = []
    stats = _run("sequence.analyze", trace, sequence=payload["sequence"])
    out: dict[str, Any] = {"sequence_stats": stats}
    if _is_error(stats):
        notes.append(f"sequence.analyze failed: {stats['error']['message']}")
        out["notes"] = notes
        out["annotation"] = _empty_annotation()
        out["confidence"] = 0.0
        return out

    recs = stats.get("records", [])
    rec = recs[0] if len(recs) == 1 else None
    is_protein = rec and rec.get("type") == "protein" and rec.get("length", 0) >= 25

    hint_hits: list[dict] = []
    if is_protein:
        probe_full = _extract_seq_for_probe(payload["sequence"])
        for size in (30, 20, 15):
            probe = probe_full[:size]
            if not probe:
                break
            hint = _run("uniprot.search", trace, query=probe, size=3)
            if _is_error(hint):
                notes.append(f"uniprot.search failed: {hint['error']['message']}")
                break
            out["uniprot_hint"] = hint
            hint_hits = hint.get("hits", [])
            if hint_hits:
                if size != 30:
                    notes.append(f"used shorter {size}aa probe after empty 30aa probe (fallback)")
                break
            else:
                trace.log("fallback", {"reason": f"uniprot.search empty for {size}aa probe"})
        if not hint_hits and "uniprot_hint" in out:
            notes.append("no UniProt match for any probe length (30/20/15 aa)")

    out["annotation"] = _build_protein_annotation(rec, hint_hits)
    out["confidence"] = _protein_confidence(rec, hint_hits, payload["sequence"])
    if notes:
        out["notes"] = notes
    return out


def uniprot_lookup(payload: dict, trace) -> dict:
    """Pipeline:
        (if accession) uniprot.fetch
        + uniprot.search (cleaned query)
        → if 0 hits and query has multiple words, retry with each token
        → annotation from primary entry / first hit, with confidence
    """
    notes: list[str] = []
    out: dict[str, Any] = {}

    if "accession" in payload:
        entry = _run("uniprot.fetch", trace, accession=payload["accession"])
        out["entry"] = entry
        if _is_error(entry):
            notes.append(f"uniprot.fetch failed for {payload['accession']}: {entry['error']['message']}")

    raw = payload["query"]
    cleaned = _clean_keywords(raw) if not payload.get("accession") else raw
    if cleaned != raw:
        trace.log("query_cleaned", {"raw": raw, "cleaned": cleaned})
    search = _run("uniprot.search", trace, query=cleaned, size=5)
    out["search"] = search

    if _is_error(search):
        notes.append(f"uniprot.search failed: {search['error']['message']}")
    elif search.get("count", 0) == 0:
        # fallback: try each significant token individually
        tokens = [t for t in cleaned.split() if len(t) >= 3]
        for tok in tokens[:3]:
            if tok == cleaned:
                continue
            trace.log("fallback", {"reason": f"uniprot.search empty, retry with token {tok!r}"})
            retry = _run("uniprot.search", trace, query=tok, size=5)
            if not _is_error(retry) and retry.get("count", 0) > 0:
                out["search"] = retry
                notes.append(f"original query had 0 hits, used token {tok!r} (fallback)")
                break
        else:
            notes.append("no UniProt match found for any single token")

    primary_entry = out.get("entry") if isinstance(out.get("entry"), dict) and not _is_error(out.get("entry")) else None
    hits = out["search"].get("hits", []) if not _is_error(out["search"]) else []
    out["annotation"] = _build_protein_annotation(primary_entry, hits)
    out["confidence"] = _lookup_confidence(primary_entry, hits)
    if notes:
        out["notes"] = notes
    return out


def literature_search(payload: dict, trace) -> dict:
    """Pipeline:
        pubmed.search (cleaned query, e.g. 'CRISPR base editing AND 2024[dp]')
        → if 0 hits, drop year constraint and retry
        → if still 0, try keywords-only
    """
    notes: list[str] = []
    raw = payload["query"]
    cleaned = _clean_pubmed_query(raw)
    trace.log("query_cleaned", {"raw": raw, "cleaned": cleaned})

    res = _run("pubmed.search", trace, query=cleaned, max_results=5)
    if _is_error(res):
        notes.append(f"pubmed.search failed: {res['error']['message']}")
    elif res.get("count", 0) == 0 and "[dp]" in cleaned:
        # drop the year filter
        no_year = re.sub(r"\s*AND\s*\d{4}\[dp\]", "", cleaned).strip(" ()")
        trace.log("fallback", {"reason": "pubmed empty with year filter; dropping year"})
        retry = _run("pubmed.search", trace, query=no_year, max_results=5)
        if not _is_error(retry) and retry.get("count", 0) > 0:
            res = retry
            notes.append(f"original year filter returned 0; relaxed query to {no_year!r}")
    out = {"pubmed": res}
    out["annotation"] = _build_literature_annotation(res if not _is_error(res) else {})
    out["confidence"] = _literature_confidence(res if not _is_error(res) else {})
    if notes:
        out["notes"] = notes
    return out


def mutation_effect(payload: dict, trace) -> dict:
    notes: list[str] = []
    res = _run(
        "mutation.diff",
        trace,
        wild_type=payload["wild_type"],
        mutant=payload.get("mutant"),
        mutation=payload.get("mutation"),
    )
    out = {"mutation": res}
    if _is_error(res):
        notes.append(f"mutation.diff failed: {res['error']['message']}")
        out["annotation"] = _empty_annotation()
        out["confidence"] = 0.0
    else:
        out["annotation"] = {
            "kind": "mutation",
            "n_differences": res.get("n_differences", 0),
            "overall_assessment": res.get("overall_assessment"),
            "notable_flags": _gather_notable_flags(res.get("differences", [])),
        }
        out["confidence"] = _mutation_confidence(res)
    if notes:
        out["notes"] = notes
    return out


# --------- annotation + confidence -----------------------------------------------

def _empty_annotation() -> dict:
    return {"kind": "unknown", "function": None, "organism": None, "homology_hint": None}


def _build_protein_annotation(primary: dict | None, hits: list[dict]) -> dict:
    """Combine a primary UniProt entry (full record) with search hits.

    `primary` is the dict returned by uniprot.fetch (has `function`, `sequence`).
    `hits` is the list of compact records from uniprot.search.
    """
    ann = {"kind": "protein"}
    src = None
    if primary and primary.get("name"):
        src = primary
    elif hits:
        src = hits[0]
    if src:
        ann["accession"] = src.get("accession")
        ann["name"] = src.get("name")
        ann["organism"] = src.get("organism")
        ann["function"] = src.get("function")
        ann["length"] = src.get("length")
    else:
        ann["accession"] = ann["name"] = ann["organism"] = ann["function"] = ann["length"] = None
    if hits:
        ann["homology_hint"] = [
            {"accession": h.get("accession"), "id": h.get("id"), "organism": h.get("organism")}
            for h in hits[:3]
        ]
    else:
        ann["homology_hint"] = []
    return ann


def _build_literature_annotation(res: dict) -> dict:
    hits = res.get("hits", []) if isinstance(res, dict) else []
    return {
        "kind": "literature",
        "n_hits": len(hits),
        "top_pmids": [h.get("pmid") for h in hits[:5]],
        "query_used": res.get("query"),
    }


def _gather_notable_flags(diffs: list[dict]) -> list[str]:
    flags = []
    for d in diffs:
        for f in d.get("flags", []):
            if f not in flags:
                flags.append(f)
    return flags


def _protein_confidence(rec: dict | None, hits: list[dict], raw_seq_text: str) -> float:
    """Confidence for sequence_basic_analysis on a protein input."""
    if rec is None:
        return 0.1  # got stats but ambiguous record set
    score = 0.0
    if rec.get("type") in {"protein", "dna", "rna"}:
        score += 0.2  # we know what we're looking at
    if hits:
        score += 0.5
        if len(hits) >= 3:
            score += 0.1
        # exact sequence match on the probe is the strongest signal we have
        probe = _extract_seq_for_probe(raw_seq_text)
        for h in hits:
            # we don't have full sequence in the compact hit; treat name == 'demo' etc. as no boost
            if h.get("length") and rec.get("length") and abs(h["length"] - rec["length"]) <= 5:
                score += 0.15
                break
    return round(min(score, 1.0), 2)


def _lookup_confidence(primary: dict | None, hits: list[dict]) -> float:
    if primary and primary.get("name") and not _is_error(primary):
        return 0.95  # exact accession fetch
    if not hits:
        return 0.0
    score = 0.4
    if len(hits) >= 3:
        score += 0.2
    # check if any hit is from H. sapiens (often what users want)
    if any(h.get("organism") == "Homo sapiens" for h in hits):
        score += 0.2
    if hits[0].get("function"):
        score += 0.15
    return round(min(score, 1.0), 2)


def _literature_confidence(res: dict) -> float:
    n = len(res.get("hits", [])) if isinstance(res, dict) else 0
    if n == 0:
        return 0.0
    if n >= 5:
        return 0.85
    return round(0.4 + 0.1 * n, 2)


def _mutation_confidence(res: dict) -> float:
    """Heuristic only: we trust position math but the impact prediction is rule-based."""
    n = res.get("n_differences", 0)
    if n == 0:
        return 0.5  # identical sequences — not really a "result"
    has_severe = any(d.get("severity") == "high" for d in res.get("differences", []))
    return 0.85 if has_severe else 0.7


_HANDLERS: dict[str, Callable[[dict, Any], dict]] = {
    "sequence_basic_analysis": sequence_basic_analysis,
    "uniprot_lookup": uniprot_lookup,
    "literature_search": literature_search,
    "mutation_effect": mutation_effect,
}


__all__ = [
    "sequence_basic_analysis",
    "uniprot_lookup",
    "literature_search",
    "mutation_effect",
    "_HANDLERS",
]
