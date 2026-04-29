from __future__ import annotations

import json
from typing import Any

from ..backends import Backend
from ..session import SessionStore
from ..skills import SKILL_REGISTRY
from .intent_classifier import llm_classify, needs_llm_classification
from .router import detect_intent, Intent
from .trace import Trace

SYSTEM_PROMPT = """You are Open-Rosalind, a local-first life-science research assistant.

You receive a USER QUESTION plus structured EVIDENCE that has already been
fetched from authoritative biological databases (UniProt, PubMed) or computed
locally. EVIDENCE is the only source of truth.

Strict rules:
1. Use ONLY facts present in EVIDENCE. Do NOT add knowledge from training data.
   If a claim cannot be grounded in EVIDENCE, say "evidence does not specify".
2. Cite every factual claim inline:
   - UniProt facts → [UniProt:<accession>]   e.g. [UniProt:P38398]
   - PubMed facts  → [PMID:<id>]              e.g. [PMID:38308006]
   - Local compute → [tool:<name>]            e.g. [tool:sequence.analyze]
3. If EVIDENCE includes a `notes` field, mention any non-trivial fallback
   ("retried with shorter probe", "no UniProt match found", ...) honestly.
4. Format:
   - Start with a 1-2 sentence headline answer.
   - Then a short Markdown body.
   - End with a `### Evidence` section bullet-listing the citations used.
5. Be concise: aim for under ~250 words unless the question demands more.
"""


class Agent:
    def __init__(self, backend: Backend, trace_dir: str = "./traces", session_dir: str = "./sessions"):
        self.backend = backend
        self.trace_dir = trace_dir
        self.session_store = SessionStore(session_dir)

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

    def analyze(self, question: str, session_id: str | None = None, mode: str | None = None,
                conversation_history: list[dict] | None = None) -> dict[str, Any]:
        trace = Trace(self.trace_dir, session_id=session_id)
        trace.log("user_input", {"question": question, "mode": mode})

        # Session event: start
        self.session_store.write_event(trace.session_id, "start", user_input=question, mode=mode)

        if mode and mode not in (None, "", "auto"):
            intent = self._intent_from_mode(question, mode)
            trace.log("router", {"path": "mode-forced", "skill": intent.skill})
        else:
            rule_intent = detect_intent(question)
            if needs_llm_classification(question):
                trace.log("router", {"path": "llm_classify_requested",
                                     "rule_guess": rule_intent.skill,
                                     "reason": "embedded_sequence_in_natural_language"})
                llm_intent = llm_classify(question, self.backend)
                if llm_intent and llm_intent.skill != rule_intent.skill:
                    trace.log("router", {"path": "llm_classify_overrode",
                                         "from": rule_intent.skill,
                                         "to": llm_intent.skill})
                    intent = llm_intent
                elif llm_intent:
                    trace.log("router", {"path": "llm_classify_confirmed",
                                         "skill": llm_intent.skill})
                    intent = llm_intent
                else:
                    trace.log("router", {"path": "llm_classify_failed_fallback",
                                         "skill": rule_intent.skill})
                    intent = rule_intent
            else:
                trace.log("router", {"path": "rule_based", "skill": rule_intent.skill})
                intent = rule_intent
        trace.log("plan", {"skill": intent.skill, "payload": intent.payload})

        # Session event: skill_call
        self.session_store.write_event(trace.session_id, "skill_call", skill=intent.skill, payload=intent.payload)

        skill_fn = SKILL_REGISTRY[intent.skill]
        evidence = skill_fn(intent.payload, trace=trace)
        trace.log("evidence", {"skill": intent.skill, "evidence": evidence})

        # Session event: skill_result
        self.session_store.write_event(
            trace.session_id, "skill_result",
            evidence=evidence,
            annotation=evidence.get("annotation"),
            confidence=evidence.get("confidence"),
            notes=evidence.get("notes", []),
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        # Insert recent conversation history so the LLM understands references
        # like "this protein", "it", "再查一下文献", etc. (industry-standard
        # sliding-window truncation, not long-term memory).
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({
            "role": "user",
            "content": (
                f"USER QUESTION:\n{question}\n\n"
                f"SKILL: {intent.skill}\n"
                f"EVIDENCE (JSON):\n{json.dumps(evidence, ensure_ascii=False, indent=2)[:8000]}\n\n"
                "Write the answer now."
            ),
        })
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

        # Session event: summary
        self.session_store.write_event(trace.session_id, "summary", text=summary)

        return {
            "session_id": trace.session_id,
            "skill": intent.skill,
            "summary": summary,
            "annotation": evidence.get("annotation"),
            "confidence": evidence.get("confidence"),
            "notes": evidence.get("notes", []),
            "evidence": evidence,
            "trace_path": str(trace.path),
            "trace": trace.events,
            "trace_steps": _structured_trace(trace.events),
        }


def _structured_trace(events: list[dict]) -> list[dict]:
    """Reduce the JSONL event log to structured steps with latency + status.
    [{skill, input, output, latency_ms, status}, ...] — one entry per tool invocation.
    """
    pending: list[dict] = []
    steps: list[dict] = []
    for ev in events:
        if ev["kind"] == "tool_call":
            pending.append({"skill": ev.get("tool"), "input": ev.get("args", {})})
        elif ev["kind"] == "tool_result" and pending:
            step = pending.pop(0)
            step["status"] = ev.get("status", "unknown")
            step["latency_ms"] = ev.get("latency_ms")
            step["output"] = ev.get("result") if ev.get("status") == "success" else {"error": ev.get("error")}
            steps.append(step)
    return steps
