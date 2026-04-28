"""Task trace store: JSONL persistence for multi-step tasks.

Extends MVP2's single-step trace to task-level trace.
"""
from __future__ import annotations

import json
from pathlib import Path

from .task import Task


class TaskTraceStore:
    """Persist task-level traces to JSONL."""

    def __init__(self, base_dir: str = "./task_traces"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, task: Task):
        """Save task trace to JSONL file."""
        path = self.base_dir / f"{task.task_id}.jsonl"
        with path.open("w") as f:
            # Task metadata
            f.write(json.dumps({
                "kind": "task_start",
                "task_id": task.task_id,
                "user_goal": task.user_goal,
                "max_steps": task.max_steps,
                "created_at": task.created_at,
            }, ensure_ascii=False) + "\n")

            # Steps
            for step in task.steps:
                f.write(json.dumps({
                    "kind": "step",
                    "step_id": step.step_id,
                    "instruction": step.instruction,
                    "expected_workflow": step.expected_workflow,
                    "status": step.status,
                    "latency_ms": step.latency_ms,
                    "error": step.error,
                    "n_evidence": len(step.evidence),
                    "n_trace": len(step.trace),
                }, ensure_ascii=False) + "\n")

            # Final report
            f.write(json.dumps({
                "kind": "task_complete",
                "status": task.status,
                "final_report": task.final_report,
                "warnings": task.warnings,
                "reproducibility": {
                    "all_steps_traced": all(len(s.trace) > 0 for s in task.steps if s.status == "success"),
                    "all_outputs_grounded": len(task.state.evidence_pool) > 0,
                },
            }, ensure_ascii=False) + "\n")

    def load(self, task_id: str) -> list[dict]:
        """Load task trace from JSONL file."""
        path = self.base_dir / f"{task_id}.jsonl"
        if not path.exists():
            return []
        events = []
        for line in path.read_text().splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events
