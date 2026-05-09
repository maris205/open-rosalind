"""TaskRunner: Executes multi-step tasks by orchestrating Agent calls.

Principles:
- Failure doesn't abort the entire task
- Every step must have trace
- Every step must record evidence
- Final report only based on evidence_pool
"""
from __future__ import annotations

import re
import time

from .contracts import StepExecutor, StepResult
from .planner import ConstrainedPlanner
from .task import Task, TaskStep


class TaskRunner:
    """Orchestrates multi-step task execution."""

    def __init__(self, agent_adapter: StepExecutor):
        self.agent_adapter = agent_adapter
        self.planner = ConstrainedPlanner()

    def run(self, task: Task) -> Task:
        """
        Execute a multi-step task.

        Args:
            task: Task with user_goal and max_steps

        Returns:
            Completed task with steps, evidence, trace, final_report
        """
        task.status = "running"

        # 1. Generate plan
        plan = self.planner.create_plan(task.user_goal, task.max_steps)
        task.steps = plan

        # 2. Execute steps sequentially
        for i, step in enumerate(task.steps):
            task.state.current_step = i + 1
            step.status = "running"

            t0 = time.time()
            result = self.agent_adapter.run_step(
                instruction=step.instruction,
                context=task.state.known_entities,
                expected_workflow=step.expected_workflow,
                payload_hint=step.payload_hint,
            )
            step.latency_ms = int((time.time() - t0) * 1000)

            self._apply_step_result(task, step, result)

        # 3. Build final report
        task.final_report = self._build_report(task)
        task.status = "completed"
        return task

    def _apply_step_result(self, task: Task, step: TaskStep, result: StepResult) -> None:
        """Apply the adapter result to task/step state.

        TaskRunner only understands StepResult. It never reaches into skills or
        tools directly.
        """
        step.status = result.status
        step.agent_result = result.to_dict()
        step.evidence = [result.evidence]
        step.trace = result.trace
        step.error = result.error

        if result.status == "success":
            task.state.known_entities.update(result.extracted_entities)
            task.state.evidence_pool.extend(step.evidence)
            task.state.trace_refs.append(f"{task.task_id}/step_{step.step_id}")
        else:
            task.add_warning(step, result.error or "Unknown error")

    def _build_report(self, task: Task) -> str:
        """
        Synthesize final report from evidence_pool.

        Report structure:
        - Summary of task goal
        - Key findings from each step
        - Evidence citations
        - Warnings (if any)
        """
        success_count = sum(1 for step in task.steps if step.status == "success")
        lines = [
            f"Task completed with {success_count}/{len(task.steps)} successful step"
            f"{'' if len(task.steps) == 1 else 's'}.\n"
        ]

        for step in task.steps:
            status_icon = "✅" if step.status == "success" else "❌"
            lines.append(f"{status_icon} **{step.step_id}**: {step.instruction}")
            if step.agent_result and step.agent_result.get("summary"):
                summary = self._lead_summary(str(step.agent_result["summary"]))
                if summary:
                    lines.append(f"   - {summary}")
            lines.append("")

        # Key entities
        if task.state.known_entities:
            lines.append("Key entities:\n")
            for key, value in task.state.known_entities.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        # Warnings
        if task.warnings:
            lines.append("Warnings:\n")
            for w in task.warnings:
                lines.append(f"- {w}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _lead_summary(summary: str, max_len: int = 240) -> str:
        text = (summary or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            return ""

        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        preferred = ""
        for part in paragraphs:
            first_line = next((line.strip() for line in part.splitlines() if line.strip()), "")
            if first_line and not first_line.startswith("|") and not first_line.startswith("##"):
                preferred = first_line
                break
        if not preferred and paragraphs:
            preferred = paragraphs[0].splitlines()[0].strip()

        preferred = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", preferred)
        preferred = re.sub(r"[*`~]", "", preferred)
        preferred = re.sub(r"\s+", " ", preferred).strip()
        if not preferred:
            return ""
        return preferred[: max_len - 1].rstrip() + "…" if len(preferred) > max_len else preferred
