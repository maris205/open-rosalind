"""Model-only answer routing evidence handler."""
from __future__ import annotations

from typing import Any

from ..runtime import ensure_trace


NO_TOOL_NOTE = "No external tools or database evidence were used for this answer."


def handler(payload: dict, trace: Any) -> dict:
    question = str(payload.get("question") or "").strip()
    trace = ensure_trace(trace)
    trace.log(
        "route_metadata",
        {
            "skill": "model_only",
            "source": "language_model",
            "scientific_tools_used": False,
            "external_database_evidence_used": False,
        },
    )

    return {
        "annotation": {
            "kind": "model_only",
            "source": "language_model",
            "question_type": "general_or_basic_education",
        },
        "confidence": 0.5,
        "notes": [NO_TOOL_NOTE],
        "route": {
            "question": question,
            "answer_source": "language_model",
            "scientific_tools_used": False,
            "external_database_evidence_used": False,
            "intended_scope": [
                "product_help",
                "conversation",
                "basic_education",
                "general_non_tool_question",
            ],
            "excluded_scope": [
                "gene_or_protein_lookup",
                "sequence_analysis",
                "mutation_assessment",
                "literature_search",
                "database_query",
                "similarity_search",
            ],
        },
    }

