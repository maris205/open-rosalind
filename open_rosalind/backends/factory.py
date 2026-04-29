from __future__ import annotations

import os

from .base import Backend
from .openrouter import OpenRouterBackend


def build_backend(cfg: dict) -> Backend:
    provider = cfg.get("provider", "openrouter")
    if provider == "openrouter":
        # Env vars override config values — friendly to docker-style deployments
        return OpenRouterBackend(
            model=os.environ.get("OPENROUTER_MODEL") or cfg["model"],
            api_key=os.environ.get("OPENROUTER_API_KEY"),
            base_url=os.environ.get("OPENROUTER_BASE_URL") or cfg.get("base_url", "https://openrouter.ai/api/v1"),
            reasoning_enabled=cfg.get("reasoning_enabled", False),
        )
    raise ValueError(f"Unknown backend provider: {provider}")
