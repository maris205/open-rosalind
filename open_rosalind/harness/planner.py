"""ConstrainedPlanner: Template-based planning for 3 task types.

MVP3 planner doesn't do free-form planning — it selects from predefined templates.
This ensures workflow stability and reproducibility.
"""
from __future__ import annotations

import re

from .task import TaskStep


class ConstrainedPlanner:
    """Template-based planner for multi-step bio tasks."""

    TEMPLATES = {
        "protein_research": [
            TaskStep(
                step_id="step_001",
                instruction="Resolve the target protein or gene using UniProt.",
                expected_workflow="uniprot_lookup",
            ),
            TaskStep(
                step_id="step_002",
                instruction="Find related literature for the target protein or gene.",
                expected_workflow="literature_search",
            ),
        ],
        "sequence_literature": [
            TaskStep(
                step_id="step_001",
                instruction="Analyze the provided protein sequence through the constrained protein annotation workflow.",
                expected_workflow="workflow_protein_annotation",
            ),
            TaskStep(
                step_id="step_002",
                instruction="Find related literature for {protein_name}.",
                expected_workflow="literature_search",
            ),
        ],
        "sequence_homology": [
            TaskStep(
                step_id="step_001",
                instruction="Analyze the provided protein sequence through the constrained protein annotation workflow.",
                expected_workflow="workflow_protein_annotation",
            ),
            TaskStep(
                step_id="step_002",
                instruction="Search for similar proteins using NCBI BLAST and the grounded sequence query.",
                expected_workflow="ncbi_blast_search",
            ),
        ],
        "literature_review": [
            TaskStep(
                step_id="step_001",
                instruction="Search PubMed for papers on the given topic.",
                expected_workflow="literature_search",
            ),
        ],
        "mutation_assessment": [
            TaskStep(
                step_id="step_001",
                instruction="Assess the mutation through the constrained mutation assessment workflow.",
                expected_workflow="workflow_mutation_assessment",
            ),
        ],
    }

    def create_plan(self, user_goal: str, max_steps: int = 5) -> list[TaskStep]:
        """
        Select a template based on user_goal keywords.

        Args:
            user_goal: Natural-language task description
            max_steps: Maximum number of steps to return

        Returns:
            List of TaskStep (from template)
        """
        goal_lower = user_goal.lower()

        extracted_sequence = self._extract_sequence(user_goal)
        mutation_payload = self._extract_mutation_payload(user_goal)

        # Detect task type from keywords
        query_target = self._extract_query_target(user_goal)

        if mutation_payload:
            template_name = "mutation_assessment"
        elif extracted_sequence or any(kw in goal_lower for kw in ["sequence", "protein", "analyze", "fasta"]):
            if any(kw in goal_lower for kw in ["papers", "literature", "pubmed"]):
                template_name = "sequence_literature" if extracted_sequence else "protein_research"
            elif any(kw in goal_lower for kw in ["similar proteins", "similar protein", "homolog", "homology", "blast"]):
                template_name = "sequence_homology"
            else:
                # Just protein annotation workflow, no literature
                template_name = "sequence_literature" if extracted_sequence else "protein_research"
                max_steps = min(max_steps, 1)
        elif query_target and any(kw in goal_lower for kw in ["papers", "literature", "pubmed"]):
            if re.search(r"\bwhat\s+is\b|\band\s+(find|search|look)\b", goal_lower):
                template_name = "protein_research"
            else:
                template_name = "literature_review"
        elif any(kw in goal_lower for kw in ["papers", "literature", "pubmed", "review"]):
            template_name = "literature_review"
        else:
            # Default: assume protein research
            template_name = "protein_research"

        # Get template and truncate to max_steps
        template = self.TEMPLATES[template_name][:max_steps]
        steps = [
            TaskStep(
                step_id=step.step_id,
                instruction=step.instruction,
                expected_workflow=step.expected_workflow,
                payload_hint=dict(step.payload_hint),
            )
            for step in template
        ]
        for step in steps:
            if step.expected_workflow == "workflow_protein_annotation" and extracted_sequence:
                step.payload_hint["sequence"] = extracted_sequence
            if step.expected_workflow == "uniprot_lookup" and query_target:
                step.payload_hint["query"] = query_target
            if step.expected_workflow == "ncbi_blast_search" and extracted_sequence:
                step.payload_hint["sequence"] = extracted_sequence
            if step.expected_workflow == "workflow_mutation_assessment":
                step.payload_hint.update(mutation_payload)
            if step.expected_workflow == "literature_search":
                if mutation_payload.get("gene_symbol"):
                    step.payload_hint["query"] = mutation_payload["gene_symbol"]
                elif extracted_sequence:
                    step.payload_hint["query"] = extracted_sequence
                elif query_target:
                    step.payload_hint["query"] = query_target
        return steps

    @staticmethod
    def _extract_sequence(text: str) -> str | None:
        candidates = re.findall(r"[A-Za-z]{10,}", text or "")
        alphabet = set("ACDEFGHIKLMNPQRSTVWYBXZacdefghiklmnpqrstvwybxz*")
        best = None
        best_len = 0
        for candidate in candidates:
            if set(candidate) <= alphabet and len(candidate) > best_len:
                best = candidate.upper()
                best_len = len(candidate)
        return best

    @staticmethod
    def _extract_mutation_payload(text: str) -> dict[str, str]:
        payload: dict[str, str] = {}
        raw_text = text or ""
        lowered = raw_text.lower()
        has_mutation_context = bool(
            re.search(r"\b(mutation|mutant|variant|substitution|polymorphism|allele|impact|effect)\b", lowered)
            or re.search(r"\b(?:wt|wild[-\s]*type)\s*:", lowered)
            or re.search(r"\b(?:mt|mutant)\s*:", lowered)
        )
        mutation_match = re.search(r"\b(?:p\.)?([A-Z])(\d{1,4})([A-Z\*])\b", text or "")
        if mutation_match:
            payload["mutation"] = f"p.{mutation_match.group(1)}{mutation_match.group(2)}{mutation_match.group(3)}"

        if not payload.get("mutation") and not has_mutation_context:
            return {}

        for token in re.findall(r"\b([A-Z][A-Z0-9]{1,7})\b", text or ""):
            if token not in {"WT", "MT", "DNA", "RNA", "AA", "NT"} and "gene_symbol" not in payload:
                payload["gene_symbol"] = token
                break

        return payload

    @staticmethod
    def _extract_query_target(text: str) -> str | None:
        tokens = re.findall(r"\b([A-Z][A-Z0-9]{1,15})\b", text or "")
        for token in tokens:
            if token not in {"WT", "MT", "DNA", "RNA", "AA", "NT"}:
                return token
        return None
