"""Shared metadata and validation for modular skills."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


ALLOWED_SAFETY_LEVELS = {"safe", "network", "compute", "exec"}


class SkillExample(BaseModel):
    input: dict[str, Any]
    expects: str | None = None
    output_preview: dict[str, Any] | None = None


class SkillMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    description: str
    category: str
    version: str = "1.0.0"
    display_name: str | None = None
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    evidence_schema: dict[str, Any] | None = None
    deterministic: bool = True
    requires_network: bool = False
    local_available: bool = True
    safety_level: str = "safe"
    dependencies: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    examples: list[SkillExample] = Field(default_factory=list)
    mcp_compatible: bool = True
    author: str | None = None
    license: str | None = None

    @field_validator("safety_level")
    @classmethod
    def validate_safety_level(cls, value: str) -> str:
        if value not in ALLOWED_SAFETY_LEVELS:
            raise ValueError(f"invalid safety_level: {value!r}")
        return value

    @field_validator("name", "description", "category")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be non-empty")
        return value.strip()

    @property
    def effective_display_name(self) -> str:
        return self.display_name or self.name
