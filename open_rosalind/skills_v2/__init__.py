"""Skills v2 auto-discovery registry.

Scans skills_v2/ subdirectories and auto-registers skills.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..skills import Skill
from .specs import SkillMetadata


def discover_skills() -> dict[str, Skill]:
    """
    Auto-discover skills from subdirectories.

    Each skill directory must contain:
    - SKILL.md (documentation)
    - skill.json (metadata)
    - handler.py (with handler function)

    Returns:
        Dict mapping skill name to Skill object
    """
    skills = {}
    skills_dir = Path(__file__).parent

    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith('_'):
            continue

        skill_json = skill_dir / "skill.json"
        handler_py = skill_dir / "handler.py"

        if not skill_json.exists() or not handler_py.exists():
            continue

        try:
            # Load metadata
            meta = SkillMetadata.model_validate(json.loads(skill_json.read_text()))

            # Import handler
            module_name = f"open_rosalind.skills_v2.{skill_dir.name}.handler"
            handler_module = __import__(module_name, fromlist=["handler"])

            # Create Skill object
            skills[meta.name] = Skill(
                name=meta.name,
                description=meta.description,
                category=meta.category,
                input_schema=meta.input_schema,
                output_schema=meta.output_schema,
                handler=handler_module.handler,
                examples=[example.model_dump(exclude_none=True) for example in meta.examples],
                safety_level=meta.safety_level,
                tools_used=meta.tools_used,
            )
        except Exception as e:
            print(f"Warning: Failed to load skill {skill_dir.name}: {e}")
            continue

    return skills


# Auto-discover on import
SKILLS_V2 = discover_skills()

__all__ = ["SKILLS_V2", "discover_skills"]
