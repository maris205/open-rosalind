from __future__ import annotations

import json
from typing import Any

from ..backends import Backend
from ..skills import SKILL_REGISTRY
from .router import detect_intent, Intent
from .trace import Trace

SYSTEM_PROMPT = """You are Open-Rosalind, a local-first life-science research assistant.
You will be given a user question and structured EVIDENCE that was already fetched
from authoritative biological databases (UniProt, PubMed) or computed locally.

Rules:
- Ground every claim in the evidence. If the evidence is empty or insufficient, say so.
- Be concise and precise. Use scientific terminology when appropriate.
- If the evidence contains UniProt accessions or PubMed IDs, cite them inline like [UniProt:P38398] or [PMID:12345678].
- Output a short Markdown summary, then a brief "Evidence" section listing the key facts you used.
"""


class Agent:
    def __init__(self, backend: Backend, trace_dir: str = "./traces"):
        self.backend = backend
        self.trace_dir = trace_dir

    @staticmethod
    def _intent_from_mode(text: str, mode: str) -> Intent:
        mode = mode.lower()
        if mode == "sequence":
            return Intent(skill="sequence_basic_analysis", payload={"sequence": text})
        if mode == "uniprot":
            return Intent(skill="uniprot_lookup", payload={"query": text})
        if mode == "literature":
            return Intent(skill="literature_search", payload={"query": text})
        if mode == "mutation":
            # Reuse the auto-router's WT/MT parsing.
            return detect_intent(text) if "mutation_effect" == detect_intent(text).skill else Intent(
                skill="mutation_effect", payload={"wild_type": text}
            )
        return detect_intent(text)

    def analyze(self, question: str, session_id: str | None = None, mode: str | None = None) -> dict[str, Any]:
        trace = Trace(self.trace_dir, session_id=session_id)
        trace.log("user_input", {"question": question, "mode": mode})

        if mode and mode not in (None, "", "auto"):
            intent = self._intent_from_mode(question, mode)
        else:
            intent = detect_intent(question)
        trace.log("plan", {"skill": intent.skill, "payload": intent.payload})

        skill_fn = SKILL_REGISTRY[intent.skill]
        evidence = skill_fn(intent.payload, trace=trace)
        trace.log("evidence", {"skill": intent.skill, "evidence": evidence})

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"USER QUESTION:\n{question}\n\n"
                    f"SKILL: {intent.skill}\n"
                    f"EVIDENCE (JSON):\n{json.dumps(evidence, ensure_ascii=False, indent=2)[:8000]}\n\n"
                    "Write the answer now."
                ),
            },
        ]
        trace.log("model_request", {"messages": messages})
        try:
            resp = self.backend.chat(messages, temperature=0.2, max_tokens=1024)
            summary = resp.content
            trace.log("model_response", {"content": summary})
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            trace.log("model_error", {"error": err})
            summary = (
                f"_Model backend unavailable ({err}). "
                f"Showing tool evidence only — see Evidence panel below._"
            )

        return {
            "session_id": trace.session_id,
            "skill": intent.skill,
            "summary": summary,
            "evidence": evidence,
            "trace_path": str(trace.path),
            "trace": trace.events,
            "trace_steps": _structured_trace(trace.events),
        }


def _structured_trace(events: list[dict]) -> list[dict]:
    """Reduce the JSONL event log to the gpt2.md-style steps:
    [{skill, input, output}, ...] — one entry per tool invocation, in order.
    """
    pending: list[dict] = []
    steps: list[dict] = []
    for ev in events:
        if ev["kind"] == "tool_call":
            pending.append({"skill": ev.get("tool"), "input": ev.get("args", {})})
        elif ev["kind"] == "tool_result" and pending:
            step = pending.pop(0)
            step["output"] = ev.get("result") if ev.get("ok", True) else {"error": ev.get("error")}
            steps.append(step)
    return steps
