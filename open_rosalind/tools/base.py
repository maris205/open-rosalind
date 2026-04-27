from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolSpec:
    """Atomic tool: a single network/database/compute call."""
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    handler: Callable[..., Any]
    examples: list[dict] = field(default_factory=list)
    safety_level: str = "safe"  # safe | network | compute | exec
