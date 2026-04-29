"""Auto execution mode selector.

Decides between single-step (Agent) and multi-step (Harness) based on
user input heuristics. No user-visible toggle (per mvp3.2.md).
"""
from __future__ import annotations

import re

# Phrases that strongly suggest multi-step execution
HARNESS_KEYWORDS = [
    r"\band\s+find\s+(papers|literature|articles)",
    r"\band\s+look\s+up",
    r"\band\s+search\s+(for|the)",
    r"\bthen\s+(find|look|search|get)",
    r"\bafter\s+that",
    r"\bsubsequently",
    r"\balso\s+(find|search|look|get)",
    r"\bcompare\s+.+\s+(to|with|against)",
    r"\bassess\s+.+\s+(impact|effect)",
]

# Phrases that suggest research workflows
RESEARCH_PATTERNS = [
    r"analyze.+find.+papers",
    r"identify.+literature",
    r"workflow",
    r"pipeline",
    r"protein.+structure.+function",
]


def select_mode(user_input: str) -> tuple[str, str]:
    """
    Auto-select execution mode based on user input.

    Returns:
        (mode, reason) where:
            mode: "single_step" | "harness"
            reason: human-readable explanation
    """
    text = user_input.lower().strip()

    # Check for explicit harness keywords
    for pattern in HARNESS_KEYWORDS:
        if re.search(pattern, text):
            return "harness", f"detected multi-step intent: matches /{pattern}/"

    # Check for research workflow patterns
    for pattern in RESEARCH_PATTERNS:
        if re.search(pattern, text):
            return "harness", f"detected research workflow: /{pattern}/"

    # Long inputs with multiple verbs suggest multi-step
    verb_count = sum(1 for kw in ["analyze", "find", "search", "look", "compare", "identify", "summarize"]
                     if kw in text)
    if verb_count >= 2:
        return "harness", f"multiple action verbs ({verb_count}) suggest multi-step task"

    # Default: single step
    return "single_step", "single skill suffices"
