"""Sequence basic analysis skill.

Analyzes DNA/RNA/protein sequences and optionally probes UniProt for homology.
"""
import json
from pathlib import Path

from ...skills import Skill
from .skill import handler

# Load metadata from skill.json
_META = json.loads((Path(__file__).parent / "skill.json").read_text())

SEQUENCE_BASIC_ANALYSIS = Skill(
    name=_META["name"],
    description=_META["description"],
    category=_META["category"],
    input_schema=_META["input_schema"],
    output_schema=_META["output_schema"],
    handler=handler,
    examples=_META["examples"],
    safety_level=_META["safety_level"],
    tools_used=_META["tools_used"],
)

__all__ = ["SEQUENCE_BASIC_ANALYSIS"]
