"""AgentAdapter: Decoupling layer between Harness and Agent.

Harness doesn't know about tools/MCP/workflows — it only calls AgentAdapter.
AgentAdapter wraps the single-step Agent and returns structured results.
"""
from __future__ import annotations

from typing import Any

from ..orchestrator import Agent


class AgentAdapter:
    """Wraps Open-Rosalind Agent for use by Harness."""

    def __init__(self, agent: Agent):
        self.agent = agent

    def run_step(self, instruction: str, context: dict) -> dict:
        """
        Execute one step by calling the single-step Agent.

        Args:
            instruction: Natural-language instruction for this step
            context: Known entities from prior steps (e.g., {"protein_name": "BRCA1"})

        Returns:
            {
                "summary": str,
                "evidence": dict,
                "trace": list[dict],
                "confidence": float,
                "extracted_entities": dict,  # e.g., {"uniprot_accession": "P38398"}
                "status": "success" | "failed",
                "error": str | None
            }
        """
        # Inject context into instruction if needed
        enriched_instruction = self._enrich_instruction(instruction, context)

        try:
            result = self.agent.analyze(enriched_instruction)
            entities = self._extract_entities(result)

            return {
                "summary": result["summary"],
                "evidence": result["evidence"],
                "trace": result.get("trace_steps", []),
                "confidence": result.get("confidence", 0.0),
                "extracted_entities": entities,
                "status": "success",
                "error": None,
            }
        except Exception as e:
            return {
                "summary": "",
                "evidence": {},
                "trace": [],
                "confidence": 0.0,
                "extracted_entities": {},
                "status": "failed",
                "error": f"{type(e).__name__}: {e}",
            }

    def _enrich_instruction(self, instruction: str, context: dict) -> str:
        """Replace {entity_name} placeholders with actual values from context."""
        enriched = instruction
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in enriched:
                enriched = enriched.replace(placeholder, str(value))
        return enriched

    def _extract_entities(self, result: dict) -> dict:
        """Extract structured entities from agent result for context propagation."""
        entities = {}
        annotation = result.get("annotation") or {}

        # Extract common entities
        if annotation.get("accession"):
            entities["uniprot_accession"] = annotation["accession"]
        if annotation.get("name"):
            entities["protein_name"] = annotation["name"]
        if annotation.get("organism"):
            entities["organism"] = annotation["organism"]
        if annotation.get("top_pmids"):
            entities["pmids"] = annotation["top_pmids"]

        return entities
