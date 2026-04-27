from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from .base import ChatResponse


class OpenRouterBackend:
    name = "openrouter"

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        reasoning_enabled: bool = False,
    ):
        self.model = model
        self.reasoning_enabled = reasoning_enabled
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY", ""),
        )

    def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ChatResponse:
        extra_body = {}
        if self.reasoning_enabled:
            extra_body["reasoning"] = {"enabled": True}
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body=extra_body or None,
        )
        msg = resp.choices[0].message
        content = (msg.content or "").strip()
        if not content:
            reasoning = getattr(msg, "reasoning", None) or ""
            if not reasoning:
                details = getattr(msg, "reasoning_details", None) or []
                if isinstance(details, list):
                    reasoning = "\n".join(
                        (d.get("text") or d.get("summary") or "") if isinstance(d, dict) else str(d)
                        for d in details
                    ).strip()
            content = reasoning.strip()
        return ChatResponse(content=content, raw=resp.model_dump() if hasattr(resp, "model_dump") else None)
