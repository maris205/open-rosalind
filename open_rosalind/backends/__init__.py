"""Backend abstractions. Agent code talks to `chat(messages, tools=...)` only."""
from .base import Backend, ChatResponse
from .openrouter import OpenRouterBackend
from .factory import build_backend

__all__ = ["Backend", "ChatResponse", "OpenRouterBackend", "build_backend"]
