"""Shared helpers for modular skills."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..orchestrator.trace import Trace


class NullTrace:
    """No-op trace for local/direct skill execution."""

    def __init__(self):
        self.events: list[dict[str, Any]] = []

    def log(self, kind: str, payload: dict[str, Any]) -> None:
        self.events.append({"kind": kind, **payload})


def ensure_trace(trace: "Trace" | None) -> "Trace" | NullTrace:
    return trace if trace is not None else NullTrace()


def run_tool(trace: "Trace" | NullTrace, name: str, fn: Callable[..., Any], **kwargs: Any) -> Any:
    """Run a tool with structured trace logging. Returns {'error': ...} on failure."""
    trace.log("tool_call", {"tool": name, "args": kwargs})
    t0 = time.time()
    try:
        result = fn(**kwargs)
        trace.log(
            "tool_result",
            {"tool": name, "status": "success", "latency_ms": int((time.time() - t0) * 1000), "result": result},
        )
        return result
    except Exception as e:
        trace.log(
            "tool_result",
            {
                "tool": name,
                "status": "error",
                "latency_ms": int((time.time() - t0) * 1000),
                "error": {"error": type(e).__name__, "message": str(e)},
            },
        )
        return {"error": {"error": type(e).__name__, "message": str(e)}}


def is_error(result: Any) -> bool:
    return isinstance(result, dict) and "error" in result and len(result) == 1
