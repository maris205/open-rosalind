"""Harness schemas: Task, TaskStep, TaskState.

MVP3 extends MVP2's single-step agent with structured multi-step execution.
Harness manages tasks, Agent executes steps, Skills perform scientific computation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class TaskStep:
    """One step in a multi-step task."""
    step_id: str
    instruction: str
    expected_workflow: str  # skill name
    status: str = "pending"  # pending | running | success | failed
    agent_result: dict | None = None
    evidence: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    error: str | None = None
    latency_ms: int | None = None


@dataclass
class TaskState:
    """Runtime state for a task (entities, evidence, trace refs)."""
    task_id: str
    current_step: int = 0
    known_entities: dict[str, Any] = field(default_factory=dict)
    evidence_pool: list[dict] = field(default_factory=list)
    trace_refs: list[str] = field(default_factory=list)  # paths to step traces


@dataclass
class Task:
    """A multi-step task managed by the harness."""
    task_id: str
    user_goal: str
    status: str = "pending"  # pending | running | completed | failed
    max_steps: int = 5
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    steps: list[TaskStep] = field(default_factory=list)
    state: TaskState = field(default_factory=lambda: TaskState(task_id=""))
    final_report: str | None = None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.state.task_id:
            self.state.task_id = self.task_id

    def add_warning(self, step: TaskStep, message: str):
        self.warnings.append(f"[{step.step_id}] {message}")

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "user_goal": self.user_goal,
            "status": self.status,
            "max_steps": self.max_steps,
            "created_at": self.created_at,
            "steps": [
                {
                    "step_id": s.step_id,
                    "instruction": s.instruction,
                    "expected_workflow": s.expected_workflow,
                    "status": s.status,
                    "latency_ms": s.latency_ms,
                    "error": s.error,
                }
                for s in self.steps
            ],
            "state": {
                "current_step": self.state.current_step,
                "known_entities": self.state.known_entities,
                "n_evidence": len(self.state.evidence_pool),
                "n_traces": len(self.state.trace_refs),
            },
            "final_report": self.final_report,
            "warnings": self.warnings,
        }
