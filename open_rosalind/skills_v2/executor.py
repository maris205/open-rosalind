"""Direct execution entrypoint for modular skills."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..orchestrator.trace import Trace


def execute_skill_v2(name: str, payload: dict[str, Any], trace: "Trace" | None = None) -> dict[str, Any]:
    from . import SKILLS_V2

    skill = SKILLS_V2.get(name)
    if skill is None:
        raise KeyError(f"unknown skill: {name}")
    return skill.handler(payload, trace)
