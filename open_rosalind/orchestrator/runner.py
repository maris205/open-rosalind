"""AgentRunner — MVP2 Task 2.

Wraps the single-step Agent with:
  - Follow-up support: if the user provides a session_id, the runner loads
    the last session's evidence and injects it as additional context for the
    LLM, enabling "再查一下这个蛋白的文献" style queries.
  - (Future) Multi-step planning: plan → act → observe → decide if done or
    continue. For MVP2 we cap at max_steps=3 to avoid infinite loops.

For now, the runner is a thin wrapper that:
  1. Checks if session_id is provided and loads last_evidence.
  2. Calls agent.analyze() with the question.
  3. If last_evidence exists, appends it to the LLM prompt as "PREVIOUS
     SESSION CONTEXT" so the model can reference prior results.

True multi-step (plan → act → observe loop) is deferred until we have a
concrete use case that requires it. The current single-step agent already
handles 100% of the Mini BioBench v0 tasks.
"""
from __future__ import annotations

import json
from typing import Any

from ..backends import Backend
from ..session import SessionStore
from .agent import Agent


class AgentRunner:
    """Orchestrates multi-turn / follow-up queries over the single-step Agent."""

    def __init__(self, agent: Agent):
        self.agent = agent

    def run(
        self,
        question: str,
        session_id: str | None = None,
        mode: str | None = None,
        follow_up_session: str | None = None,
    ) -> dict[str, Any]:
        """Run the agent, optionally loading prior session evidence for follow-up.

        Args:
            question: user input
            session_id: optional session id for this run (if None, agent generates one)
            mode: optional skill mode override
            follow_up_session: if provided, load the last evidence from this
                session and inject it as LLM context

        Returns:
            Same shape as agent.analyze() — {session_id, skill, summary, ...}
        """
        # If follow_up_session is given, load the last evidence and modify the
        # agent's prompt to include it. For MVP2 we do this by monkey-patching
        # the agent's analyze() call — a cleaner approach would be to pass
        # `prior_context` as a parameter, but that requires refactoring the
        # agent's LLM prompt construction. We'll do the minimal thing first.
        prior_evidence = None
        if follow_up_session:
            prior_evidence = self.agent.session_store.get_last_evidence(follow_up_session)

        if prior_evidence:
            # Inject prior evidence into the agent's next LLM call by temporarily
            # wrapping the backend's chat() method. This is a hack for MVP2;
            # a proper implementation would pass prior_context as an argument
            # to agent.analyze() and have it build the prompt accordingly.
            original_chat = self.agent.backend.chat

            def chat_with_context(messages, **kwargs):
                # Insert prior evidence before the user message
                if len(messages) >= 2 and messages[-1]["role"] == "user":
                    ctx_block = (
                        f"\n\nPREVIOUS SESSION CONTEXT (for follow-up questions):\n"
                        f"{json.dumps(prior_evidence, ensure_ascii=False, indent=2)[:4000]}\n"
                    )
                    messages[-1]["content"] += ctx_block
                return original_chat(messages, **kwargs)

            self.agent.backend.chat = chat_with_context
            try:
                result = self.agent.analyze(question, session_id=session_id, mode=mode)
            finally:
                self.agent.backend.chat = original_chat
            return result
        else:
            return self.agent.analyze(question, session_id=session_id, mode=mode)
