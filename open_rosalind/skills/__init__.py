"""Bio Skills Registry — public API.

Four skills are registered out of the box. They share a uniform shape so
the AgentRunner (MVP2 Task 2) and the CLI (`open-rosalind skills list`)
can discover and dispatch them without special-casing.

Backward-compat: `SKILL_REGISTRY` (name → handler) is preserved so existing
code in the agent / tests keeps working unchanged.
"""
from __future__ import annotations

from typing import Callable, Any

from . import _pipelines
from .base import Skill

# --- skill specs -----------------------------------------------------------------

SEQUENCE_BASIC_ANALYSIS = Skill(
    name="sequence_basic_analysis",
    category="sequence",
    description=(
        "Compute basic stats on a DNA / RNA / protein sequence: length, type, "
        "composition, GC%, translation, reverse complement, approximate MW. "
        "For single proteins ≥25 aa, also runs a UniProt homology probe."
    ),
    input_schema={
        "type": "object",
        "properties": {"sequence": {"type": "string", "description": "FASTA or raw residues"}},
        "required": ["sequence"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "sequence_stats": {"type": "object"},
            "uniprot_hint": {"type": "object"},
            "annotation": {"type": "object"},
            "confidence": {"type": "number"},
            "notes": {"type": "array"},
        },
    },
    examples=[
        {"input": {"sequence": ">demo MVKVGVNGFGRIGRLVTRA"}, "expects": "type=protein, length=19"},
        {"input": {"sequence": ">x ATGCGTACGTAA"}, "expects": "type=dna, translation_preview=MRT*"},
    ],
    safety_level="network",   # may call UniProt for the homology probe
    tools_used=["sequence.analyze", "uniprot.search"],
    handler=_pipelines.sequence_basic_analysis,
)

UNIPROT_LOOKUP = Skill(
    name="uniprot_lookup",
    category="annotation",
    description=(
        "Resolve a UniProt accession or a free-text protein/gene question to "
        "structured annotation. Falls back to per-token retry when a multi-word "
        "query returns no hits."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "accession": {"type": "string", "description": "Optional explicit UniProt id"},
        },
        "required": ["query"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "entry": {"type": "object"},
            "search": {"type": "object"},
            "annotation": {"type": "object"},
            "confidence": {"type": "number"},
            "notes": {"type": "array"},
        },
    },
    examples=[
        {"input": {"query": "P38398", "accession": "P38398"}, "expects": "BRCA1_HUMAN"},
        {"input": {"query": "What is hemoglobin?"}, "expects": "search hits including HBA_HUMAN"},
    ],
    safety_level="network",
    tools_used=["uniprot.fetch", "uniprot.search"],
    handler=_pipelines.uniprot_lookup,
)

LITERATURE_SEARCH = Skill(
    name="literature_search",
    category="literature",
    description=(
        "Retrieve relevant PubMed articles for a topic. Cleans natural-language "
        "questions into PubMed query syntax (incl. year filters); on empty year-"
        "filtered result, retries without the year constraint."
    ),
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "pubmed": {"type": "object"},
            "annotation": {"type": "object"},
            "confidence": {"type": "number"},
            "notes": {"type": "array"},
        },
    },
    examples=[
        {"input": {"query": "Find papers about CRISPR base editing in 2024"},
         "expects": "5 PubMed hits with year=2024"},
    ],
    safety_level="network",
    tools_used=["pubmed.search"],
    handler=_pipelines.literature_search,
)

MUTATION_EFFECT = Skill(
    name="mutation_effect",
    category="mutation",
    description=(
        "Compare a wild-type sequence to a mutant (or apply an HGVS-style point "
        "mutation like p.R175H) and annotate each difference with a rule-based "
        "physico-chemical impact heuristic. Not a substitute for PolyPhen/SIFT."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "wild_type": {"type": "string"},
            "mutant": {"type": "string"},
            "mutation": {"type": "string", "description": "e.g. p.R175H"},
        },
        "required": ["wild_type"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "mutation": {"type": "object"},
            "annotation": {"type": "object"},
            "confidence": {"type": "number"},
            "notes": {"type": "array"},
        },
    },
    examples=[
        {"input": {"wild_type": "MEEPQ...", "mutation": "p.R175H"},
         "expects": "n_differences=1, severity=medium"},
    ],
    safety_level="safe",
    tools_used=["mutation.diff"],
    handler=_pipelines.mutation_effect,
)


SKILLS: dict[str, Skill] = {
    s.name: s for s in (
        SEQUENCE_BASIC_ANALYSIS, UNIPROT_LOOKUP, LITERATURE_SEARCH, MUTATION_EFFECT,
    )
}

# Backward compatibility — agent and tests still import this.
SKILL_REGISTRY: dict[str, Callable[[dict, Any], dict]] = {
    name: skill.handler for name, skill in SKILLS.items()
}


def list_cards() -> list[dict]:
    return [s.to_card() for s in SKILLS.values()]


def get_skill(name: str) -> Skill | None:
    return SKILLS.get(name)


__all__ = ["Skill", "SKILLS", "SKILL_REGISTRY", "list_cards", "get_skill"]
