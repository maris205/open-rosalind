"""AgentAdapter: Decoupling layer between Harness and Agent.

Harness doesn't know about tools/MCP/workflows — it only calls AgentAdapter.
AgentAdapter wraps the single-step Agent and returns structured results.
"""
from __future__ import annotations

import re
from typing import Any

from ..orchestrator import Agent
from .contracts import StepResult


class AgentAdapter:
    """Wraps Open-Rosalind Agent for use by Harness."""

    _WORKFLOW_MODE_MAP = {
        "sequence_basic_analysis": "sequence",
        "uniprot_lookup": "uniprot",
        "literature_search": "literature",
        "mutation_effect": "mutation",
    }
    _WORKFLOW_QUERY_MODE_MAP = {
        "workflow_protein_annotation": "sequence",
        "workflow_mutation_assessment": "mutation",
    }

    def __init__(self, agent: Agent):
        self.agent = agent

    def run_step(
        self,
        instruction: str,
        context: dict[str, Any],
        expected_workflow: str,
        payload_hint: dict[str, Any] | None = None,
    ) -> StepResult:
        """
        Execute one step by calling the single-step Agent.

        Args:
            instruction: Natural-language instruction for this step
            context: Known entities from prior steps (e.g., {"protein_name": "BRCA1"})
            expected_workflow: Constrained workflow/skill declared by the planner

        Returns:
            StepResult with summary/evidence/trace/confidence/entity extraction.
        """
        # Inject context into instruction if needed
        enriched_instruction = self._enrich_instruction(instruction, context)
        analyze_kwargs = self._build_analyze_kwargs(
            enriched_instruction,
            expected_workflow,
            payload_hint=payload_hint or {},
            context=context,
        )

        try:
            result = self.agent.analyze(**analyze_kwargs)
            entities = self._extract_entities(result)

            return StepResult(
                summary=result["summary"],
                evidence=result["evidence"],
                trace=result.get("trace_steps", []),
                confidence=result.get("confidence", 0.0),
                extracted_entities=entities,
                status="success",
                error=None,
            )
        except Exception as e:
            return StepResult(
                summary="",
                evidence={},
                trace=[],
                confidence=0.0,
                extracted_entities={},
                status="failed",
                error=f"{type(e).__name__}: {e}",
            )

    def _build_analyze_kwargs(
        self,
        instruction: str,
        expected_workflow: str,
        payload_hint: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        workflow_payload = self._build_workflow_payload(instruction, expected_workflow, payload_hint, context)
        workflow_mode = self._WORKFLOW_MODE_MAP.get(expected_workflow)
        if workflow_mode:
            question = str(workflow_payload.get("query") or workflow_payload.get("question") or instruction)
            return {"question": question, "mode": workflow_mode}

        workflow_query_mode = self._WORKFLOW_QUERY_MODE_MAP.get(expected_workflow)
        if workflow_query_mode:
            question = str(workflow_payload.get("question") or instruction)
            return {
                "question": question,
                "mode": workflow_query_mode,
                "workflow": expected_workflow,
                "payload_override": workflow_payload,
            }

        question = str(workflow_payload.get("question") or instruction)
        return {
            "question": question,
            "workflow": expected_workflow,
            "payload_override": workflow_payload,
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
        if annotation.get("gene_symbol"):
            entities["gene_symbol"] = annotation["gene_symbol"]
        if annotation.get("mutation"):
            entities["mutation"] = annotation["mutation"]
        if annotation.get("protein_name"):
            entities["protein_name"] = annotation["protein_name"]
        if annotation.get("workflow"):
            entities["workflow"] = annotation["workflow"]

        return entities

    def _build_workflow_payload(
        self,
        instruction: str,
        expected_workflow: str,
        payload_hint: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {k: v for k, v in (payload_hint or {}).items() if v not in (None, "", [], {})}
        if expected_workflow == "workflow_protein_annotation":
            sequence = self._extract_sequence_payload(payload, context, instruction)
            if sequence:
                return {"question": sequence, "sequence": sequence}
            return {"question": instruction}
        if expected_workflow == "workflow_mutation_assessment":
            mutation_payload = self._extract_mutation_payload(payload, context, instruction)
            if mutation_payload:
                mutation_payload.setdefault("question", instruction)
                return mutation_payload
            return {"question": instruction}
        return payload

    @staticmethod
    def _extract_sequence_payload(payload_hint: dict[str, Any], context: dict[str, Any], instruction: str) -> str:
        for candidate in (
            payload_hint.get("sequence"),
            context.get("sequence"),
            context.get("query_sequence"),
        ):
            text = str(candidate or "").strip()
            if text:
                return text
        return AgentAdapter._extract_embedded_sequence(instruction) or ""

    @staticmethod
    def _extract_mutation_payload(payload_hint: dict[str, Any], context: dict[str, Any], instruction: str) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key in ("gene_symbol", "mutation", "wild_type", "mutant", "wt", "mt", "query"):
            value = payload_hint.get(key)
            if value not in (None, "", [], {}):
                payload[key] = value

        if "query" not in payload:
            payload["query"] = instruction

        if "gene_symbol" not in payload:
            gene_symbol = str(context.get("gene_symbol") or "").strip()
            if gene_symbol:
                payload["gene_symbol"] = gene_symbol

        if "mutation" not in payload:
            mutation = AgentAdapter._extract_hgvs_mutation(instruction)
            if mutation:
                payload["mutation"] = mutation

        if "gene_symbol" not in payload:
            gene_symbol = AgentAdapter._extract_gene_symbol(instruction)
            if gene_symbol:
                payload["gene_symbol"] = gene_symbol

        return payload

    @staticmethod
    def _extract_embedded_sequence(text: str) -> str | None:
        candidates = re.findall(r"[A-Za-z]{10,}", text or "")
        best = None
        best_len = 0
        alphabet = set("ACDEFGHIKLMNPQRSTVWYBXZacdefghiklmnpqrstvwybxz*")
        for candidate in candidates:
            if set(candidate) <= alphabet and len(candidate) > best_len:
                best = candidate.upper()
                best_len = len(candidate)
        return best

    @staticmethod
    def _extract_hgvs_mutation(text: str) -> str | None:
        match = re.search(r"\b(?:p\.)?([A-Z])(\d{1,4})([A-Z\*])\b", text or "")
        if not match:
            return None
        return f"p.{match.group(1)}{match.group(2)}{match.group(3)}"

    @staticmethod
    def _extract_gene_symbol(text: str) -> str | None:
        for token in re.findall(r"\b([A-Z][A-Z0-9]{1,7})\b", text or ""):
            if token not in {"WT", "MT", "DNA", "RNA", "AA", "NT"}:
                return token
        return None
