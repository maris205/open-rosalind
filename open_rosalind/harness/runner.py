"""TaskRunner: Executes multi-step tasks by orchestrating Agent calls.

Principles:
- Failure doesn't abort the entire task
- Every step must have trace
- Every step must record evidence
- Final report only based on evidence_pool
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from .adapter import AgentAdapter
from .planner import ConstrainedPlanner
from .task import Task, TaskStep


class TaskRunner:
    """Orchestrates multi-step task execution."""

    def __init__(self, agent_adapter: AgentAdapter):
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
            )
            step.latency_ms = int((time.time() - t0) * 1000)

            # Update step
            step.status = result["status"]
            step.agent_result = result
            step.evidence = [result["evidence"]]
            step.trace = result["trace"]
            step.error = result["error"]

            # Update task state
            if result["status"] == "success":
                task.state.known_entities.update(result["extracted_entities"])
                task.state.evidence_pool.extend(step.evidence)
                task.state.trace_refs.append(f"{task.task_id}/step_{step.step_id}")
            else:
                task.add_warning(step, result["error"] or "Unknown error")

        # 3. Build final report
        task.final_report = self._build_report(task)
        task.status = "completed"
        return task

    def _build_report(self, task: Task) -> str:
        """
        Synthesize final report from evidence_pool.

        Report structure:
        - Summary of task goal
        - Key findings from each step
        - Evidence citations
        - Warnings (if any)
        """
        lines = [f"# Task Report: {task.user_goal}\n"]

        # Step summaries
        lines.append("## Steps Executed\n")
        for step in task.steps:
            status_icon = "✅" if step.status == "success" else "❌"
            lines.append(f"{status_icon} **{step.step_id}**: {step.instruction}")
            if step.agent_result and step.agent_result.get("summary"):
                lines.append(f"   - {step.agent_result['summary'][:200]}...")
            lines.append("")

        # Key entities
        if task.state.known_entities:
            lines.append("## Key Entities\n")
            for key, value in task.state.known_entities.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        # Evidence summary
        lines.append(f"## Evidence\n")
        lines.append(f"- Total evidence records: {len(task.state.evidence_pool)}")
        lines.append(f"- Trace references: {len(task.state.trace_refs)}")
        lines.append("")

        # Warnings
        if task.warnings:
            lines.append("## Warnings\n")
            for w in task.warnings:
                lines.append(f"- {w}")
            lines.append("")

        return "\n".join(lines)
