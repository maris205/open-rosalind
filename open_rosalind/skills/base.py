"""Bio Skills Registry — MVP2 Task 1.

A Skill is a higher-level pipeline that:
  - declares structured metadata (schema, examples, safety_level),
  - composes one or more atomic tools (`open_rosalind.tools`) with fallback
    and annotation logic,
  - returns a structured `evidence` dict that the agent feeds to the LLM.

Skills are the unit the AgentRunner will plan over (MVP2 Task 2). The
registry is the single place to discover what the agent can do, query its
shape (`open-rosalind skills list/inspect`), and dispatch by name.

Tools (`open_rosalind.tools`) remain atomic — one tool = one network call
or one local compute. Skills compose tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Skill:
    """A registered, composable pipeline.

    The agent dispatches by `name`. The LLM-assisted intent classifier picks
    one of these names. Schemas and examples are also surfaced via the CLI
    (`open-rosalind skills list / inspect`) and the API (`/api/skills`).
    """
    name: str
    description: str
    category: str                          # sequence | annotation | literature | mutation | meta
    input_schema: dict                     # JSON Schema for `payload` argument
    output_schema: dict                    # JSON Schema for the returned evidence dict
    handler: Callable[[dict, Any], dict]   # (payload, trace) -> evidence dict
    examples: list[dict] = field(default_factory=list)
    safety_level: str = "safe"             # safe | network | compute | exec
    tools_used: list[str] = field(default_factory=list)  # tool names this skill may call

    def to_card(self) -> dict:
        """Compact dict for /api/skills and `skills list`."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tools_used": self.tools_used,
            "safety_level": self.safety_level,
            "n_examples": len(self.examples),
        }

    def to_full(self) -> dict:
        """Verbose dict for `skills inspect <name>` and the API detail view."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tools_used": self.tools_used,
            "safety_level": self.safety_level,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "examples": self.examples,
        }
