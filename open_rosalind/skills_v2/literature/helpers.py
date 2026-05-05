"""Higher-level literature helpers."""
from __future__ import annotations

import re

from . import tools

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
    "information", "info", "details", "detail", "data", "knowledge",
    "characterize", "characterise", "analyze", "analyse", "analysis", "evaluate",
    "effect", "effects", "impact", "impacts", "consequences",
    "concerning", "related", "isoform", "variant", "form",
    "background", "context", "overview", "current", "available",
    "known", "reported", "characterization", "evaluation", "assessment",
    "mechanism", "mechanisms",
}
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def clean_keywords(text: str) -> str:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", text)
    keep = [token for token in tokens if token.lower() not in _STOPWORDS]
    return " ".join(keep) if keep else text.strip()


def clean_pubmed_query(text: str) -> str:
    year_match = _YEAR_RE.search(text)
    text_no_year = _YEAR_RE.sub(" ", text)
    query = clean_keywords(text_no_year)
    if year_match:
        query = f"({query}) AND {year_match.group(0)}[dp]"
    return query


def fetch_metadata(pmids: list[str] | str) -> dict:
    return tools.fetch_metadata(pmids=pmids)


def fetch_abstract(pmids: list[str] | str) -> dict:
    return tools.fetch_abstract(pmids=pmids)
