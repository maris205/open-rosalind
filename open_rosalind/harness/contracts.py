"""Harness execution contracts.

The harness must execute scientific work exclusively through AgentAdapter.
These contracts make that boundary explicit and keep TaskRunner isolated from
skills/tools internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


StepStatus = Literal["success", "failed"]


@dataclass(frozen=True)
class StepResult:
    """Normalized adapter response consumed by the harness."""

    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    extracted_entities: dict[str, Any] = field(default_factory=dict)
    status: StepStatus = "success"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "evidence": self.evidence,
            "trace": self.trace,
            "confidence": self.confidence,
            "extracted_entities": self.extracted_entities,
            "status": self.status,
            "error": self.error,
        }


class StepExecutor(Protocol):
    """Single execution boundary used by the harness."""

    def run_step(self, instruction: str, context: dict[str, Any], expected_workflow: str) -> StepResult:
        """Execute exactly one step and return normalized results."""
