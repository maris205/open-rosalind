"""Mutation analysis tools."""
from __future__ import annotations

from ...tools import mutation as base_mutation


def diff(
    wild_type: str | None = None,
    mutant: str | None = None,
    mutation: str | None = None,
    wt: str | None = None,
    mt: str | None = None,
) -> dict:
    """Compare WT and MT sequences via the canonical mutation tool."""
    resolved_wild_type = (wild_type or wt or "").strip()
    resolved_mutant = (mutant or mt or None)
    return base_mutation.diff_sequences(
        wild_type=resolved_wild_type,
        mutant=resolved_mutant,
        mutation=mutation,
    )
