"""ConstrainedPlanner: Template-based planning for 3 task types.

MVP3 planner doesn't do free-form planning — it selects from predefined templates.
This ensures workflow stability and reproducibility.
"""
from __future__ import annotations

from .task import TaskStep


class ConstrainedPlanner:
    """Template-based planner for multi-step bio tasks."""

    TEMPLATES = {
        "protein_research": [
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

        # Detect task type from keywords
        if any(kw in goal_lower for kw in ["sequence", "protein", "analyze", "fasta"]):
            if any(kw in goal_lower for kw in ["papers", "literature", "pubmed"]):
                template_name = "protein_research"
            else:
                # Just protein annotation workflow, no literature
                template_name = "protein_research"
                max_steps = min(max_steps, 1)
        elif any(kw in goal_lower for kw in ["mutation", "wt", "mt", "p.", "variant"]):
            template_name = "mutation_assessment"
        elif any(kw in goal_lower for kw in ["papers", "literature", "pubmed", "review"]):
            template_name = "literature_review"
        else:
            # Default: assume protein research
            template_name = "protein_research"

        # Get template and truncate to max_steps
        template = self.TEMPLATES[template_name]
        return template[:max_steps]
