"""Conversation history utilities.

Industry-standard truncation for chat history (similar to OpenAI/Anthropic
default behavior):
- Keep most recent N turns (default 6 = 3 user + 3 assistant)
- Truncate each message body to MAX_CHARS (default 1500)
- Preserve role alternation (user → assistant → user → ...)

This is NOT long-term memory — just a sliding window of recent turns
passed to the LLM so it understands "this protein", "it", etc.
"""
from __future__ import annotations

# Defaults: tuned for cost/quality balance similar to ChatGPT default behavior
DEFAULT_MAX_TURNS = 6      # 3 round-trips (user + assistant pairs)
DEFAULT_MAX_CHARS = 1500   # per message — trims long tool outputs


def truncate_history(
    messages: list[dict],
    max_turns: int = DEFAULT_MAX_TURNS,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[dict]:
    """
    Truncate a conversation history to fit a budget.

    Args:
        messages: list of {"role": "user"|"assistant", "content": str, ...}
                  ordered chronologically (oldest first).
        max_turns: keep at most this many of the most recent messages.
        max_chars: truncate each message's content to this many characters.

    Returns:
        Truncated list, oldest-first, ready to insert into the LLM prompt.
    """
    if not messages:
        return []

    # Keep only the most recent N
    trimmed = messages[-max_turns:]

    out = []
    for m in trimmed:
        content = m.get("content") or ""
        if len(content) > max_chars:
            content = content[:max_chars] + "...[truncated]"
        out.append({
            "role": m.get("role", "user"),
            "content": content,
        })

    return out
