from __future__ import annotations

import json
import re
from typing import Any

from ..backends import Backend
from ..session import SessionStore
from ..skills import SKILL_REGISTRY
from ..skills_v2 import SKILLS_V2
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
   or limitation honestly ("retried with shorter probe", "no UniProt match found", ...).
4. Preferred Markdown format:
   - Start with one short bold takeaway sentence.
   - If it helps readability, add a compact 2-column Markdown table with grounded
     fields such as accession, organism, length, hit count, mutation, or assessment.
   - Then add `## Key findings` with 2-4 concise bullets.
   - If there is ambiguity, no-hit output, fallback behavior, or missing data,
     add `## Limitations` with 1-2 concise bullets.
   - Do NOT add sections named `Evidence` or `Trace`.
   - Do NOT output raw JSON.
5. Be concise: aim for under ~220 words unless the question demands more.
6. Do not speculate about mechanisms, homology, or biological relevance unless
   that claim is explicitly supported in EVIDENCE.
"""


_SUMMARY_EVIDENCE_SECTION_RE = re.compile(
    r"(?:^|\n+)#{2,6}\s+Evidence\s*\n[\s\S]*$",
    re.IGNORECASE,
)


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

    @staticmethod
    def _intent_from_workflow(text: str, workflow: str, mode: str | None = None) -> Intent:
        workflow = workflow.strip()
        if not workflow:
            raise ValueError("workflow override must be non-empty")

        if workflow == "workflow_protein_annotation":
            return Intent(skill=workflow, payload={"sequence": text})
        if workflow == "workflow_mutation_assessment":
            base_intent = detect_intent(text)
            payload = dict(base_intent.payload)
            payload.setdefault("query", text)
            if base_intent.skill not in {"mutation_effect", workflow} and mode == "mutation":
                payload.setdefault("wild_type", text)
            return Intent(skill=workflow, payload=payload)
        return Intent(skill=workflow, payload={"query": text})

    def analyze(
        self,
        question: str,
        session_id: str | None = None,
        mode: str | None = None,
        conversation_history: list[dict] | None = None,
        workflow: str | None = None,
        payload_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        trace = Trace(self.trace_dir, session_id=session_id)
        trace.log("user_input", {"question": question, "mode": mode, "workflow": workflow})

        # Session event: start
        self.session_store.write_event(trace.session_id, "start", user_input=question, mode=mode, workflow=workflow)

        if workflow:
            intent = self._intent_from_workflow(question, workflow, mode=mode)
            if payload_override:
                intent = Intent(skill=intent.skill, payload=dict(payload_override))
            trace.log("router", {"path": "workflow-forced", "skill": intent.skill, "workflow": workflow})
        elif mode and mode not in (None, "", "auto"):
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

        skill_fn = self._resolve_skill_handler(intent.skill)
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
            summary = self._normalize_summary(resp.content)
            trace.log("model_response", {"content": summary})
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            trace.log("model_error", {"error": err})
            summary = self._evidence_fallback_summary(question, intent.skill, evidence)

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

    @staticmethod
    def _resolve_skill_handler(skill_name: str):
        skill_v2 = SKILLS_V2.get(skill_name)
        if skill_v2 is not None:
            return skill_v2.handler
        return SKILL_REGISTRY[skill_name]

    @staticmethod
    def _normalize_summary(summary: str) -> str:
        text = (summary or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if "\\n" in text and "\n" not in text:
            text = text.replace("\\n", "\n").strip()
        text = _SUMMARY_EVIDENCE_SECTION_RE.sub("", text).rstrip()
        return text

    @classmethod
    def _evidence_fallback_summary(cls, question: str, skill: str, evidence: dict[str, Any]) -> str:
        """Deterministic answer used when the model backend is unavailable.

        This keeps user-facing output grounded in structured tool evidence while
        preserving the backend error in trace as `model_error`.
        """
        annotation = evidence.get("annotation") or {}
        kind = annotation.get("kind")

        if skill == "ncbi_blast_search" or kind == "ncbi_blast":
            return cls._summarize_blast_evidence(evidence)
        if skill in {"uniprot_lookup", "protein_annotation_summary"} or kind == "protein":
            return cls._summarize_protein_evidence(evidence)
        if skill == "workflow_protein_annotation" or annotation.get("workflow") == "protein_annotation":
            return cls._summarize_protein_workflow_evidence(evidence)
        if skill in {"sequence_basic_analysis", "sequence_type_detect"} or kind in {"sequence", "sequence_type"}:
            return cls._summarize_sequence_evidence(evidence)
        if skill == "literature_search" or kind == "literature":
            return cls._summarize_literature_evidence(evidence)

        confidence = evidence.get("confidence")
        notes = evidence.get("notes") or []
        lines = ["**Tool evidence was collected, but model synthesis was unavailable.**"]
        rows = [
            ("Skill", skill),
            ("Evidence kind", kind or "not specified"),
            ("Confidence", confidence if confidence is not None else "not specified"),
        ]
        lines.extend(cls._markdown_table(rows))
        if notes:
            lines.append("\n## Limitations")
            lines.extend(f"- {note}" for note in notes[:3])
        else:
            lines.append("\n## Limitations")
            lines.append("- The available structured evidence does not include a specialized local formatter for this skill.")
        return "\n".join(lines)

    @classmethod
    def _summarize_blast_evidence(cls, evidence: dict[str, Any]) -> str:
        blast = evidence.get("blast") or {}
        annotation = evidence.get("annotation") or {}
        notes = evidence.get("notes") or []
        status = blast.get("status") or annotation.get("status") or "not specified"
        program = blast.get("program") or annotation.get("program") or "not specified"
        database = blast.get("database") or annotation.get("database") or "not specified"
        query_summaries = blast.get("query_summaries") or []
        top_query = query_summaries[0] if query_summaries else {}
        top_hits = top_query.get("top_hits") or []
        hit_count = top_query.get("hit_count_returned") or annotation.get("n_records") or 0

        if status == "READY" and top_hits:
            lines = ["**NCBI BLAST found similar proteins for the submitted sequence [tool:ncbi_blast.run_search].**"]
        elif status == "WAITING":
            lines = ["**NCBI BLAST accepted the sequence, but the search did not finish within the configured wait time [tool:ncbi_blast.run_search].**"]
        elif status == "ERROR":
            lines = ["**NCBI BLAST did not return usable results for this request [tool:ncbi_blast.run_search].**"]
        else:
            lines = ["**NCBI BLAST did not report returned similar-protein hits [tool:ncbi_blast.run_search].**"]

        lines.extend(cls._markdown_table([
            ("Program", program),
            ("Database", database),
            ("Status", status),
            ("Returned hits", hit_count),
            ("RID", blast.get("rid") or annotation.get("rid") or "not specified"),
        ]))

        if top_hits:
            lines.append("\n## Top similar proteins")
            lines.append("| Rank | Accession | Title | E-value | Bit score |")
            lines.append("| --- | --- | --- | --- | --- |")
            for hit in top_hits[:5]:
                accession = cls._safe_cell(hit.get("accession") or "not specified")
                title = cls._safe_cell(cls._truncate(hit.get("title") or "not specified", 80))
                evalue = cls._safe_cell(hit.get("evalue"))
                bit_score = cls._safe_cell(hit.get("bit_score"))
                rank = cls._safe_cell(hit.get("rank") or "")
                lines.append(f"| {rank} | {accession} | {title} | {evalue} | {bit_score} |")

        limitations = list(notes)
        if not top_hits and status != "WAITING":
            limitations.append("No top-hit table was available in the BLAST evidence.")
        if limitations:
            lines.append("\n## Limitations")
            lines.extend(f"- {note}" for note in limitations[:3])
        return "\n".join(lines)

    @classmethod
    def _summarize_protein_evidence(cls, evidence: dict[str, Any]) -> str:
        annotation = evidence.get("annotation") or {}
        entry = evidence.get("entry") or {}
        search = evidence.get("search") or {}
        notes = evidence.get("notes") or []
        source = entry or annotation
        accession = source.get("accession") or annotation.get("accession")
        name = source.get("name") or annotation.get("name")
        organism = source.get("organism") or annotation.get("organism")
        length = source.get("length")
        function = entry.get("function") or source.get("function")

        if accession or name:
            citation = f"[UniProt:{accession}]" if accession else "[tool:uniprot.search]"
            lines = [f"**The top UniProt-supported protein match is {name or accession} {citation}.**"]
        else:
            lines = ["**UniProt did not return a supported protein match for this request [tool:uniprot.search].**"]

        lines.extend(cls._markdown_table([
            ("Accession", accession or "not found"),
            ("Name", name or "not specified"),
            ("Organism", organism or "not specified"),
            ("Length", f"{length} aa" if length else "not specified"),
            ("Search hits", search.get("count", 0)),
        ]))

        if function:
            citation = f"[UniProt:{accession}]" if accession else "[tool:uniprot.search]"
            lines.append("\n## Key findings")
            lines.append(f"- Function evidence: {cls._truncate(function, 360)} {citation}")

        if notes:
            lines.append("\n## Limitations")
            lines.extend(f"- {note}" for note in notes[:3])
        return "\n".join(lines)

    @classmethod
    def _summarize_protein_workflow_evidence(cls, evidence: dict[str, Any]) -> str:
        annotation = evidence.get("annotation") or {}
        notes = evidence.get("notes") or []
        sequence_result = evidence.get("sequence_result") or {}
        protein_result = evidence.get("protein_result") or {}
        primary_type = annotation.get("primary_type")
        length = annotation.get("length")

        if primary_type == "protein" and protein_result:
            protein_summary = cls._summarize_protein_evidence(protein_result)
            workflow_rows = cls._markdown_table([
                ("Workflow", "protein_annotation"),
                ("Primary sequence type", primary_type),
                ("Length", f"{length} aa" if length else "not specified"),
            ])
            return "\n".join([
                "**The sequence was classified as protein and annotated through the constrained workflow [tool:sequence.analyze].**",
                *workflow_rows,
                "\n## Protein annotation",
                protein_summary,
            ])

        lines = ["**The constrained protein-annotation workflow did not produce a protein annotation [tool:sequence.analyze].**"]
        lines.extend(cls._markdown_table([
            ("Workflow", "protein_annotation"),
            ("Primary sequence type", primary_type or "unknown"),
            ("Length", f"{length} aa" if length else "not specified"),
            ("Confidence", evidence.get("confidence", "not specified")),
        ]))

        seq_stats = sequence_result.get("sequence_stats") or {}
        records = seq_stats.get("records") or []
        if records:
            record = records[0]
            lines.append("\n## Sequence check")
            lines.extend(cls._markdown_table([
                ("Detected type", record.get("type") or "unknown"),
                ("Length", record.get("length") or "not specified"),
            ]))

        if notes:
            lines.append("\n## Limitations")
            lines.extend(f"- {note}" for note in notes[:3])
        return "\n".join(lines)

    @classmethod
    def _summarize_sequence_evidence(cls, evidence: dict[str, Any]) -> str:
        annotation = evidence.get("annotation") or {}
        stats = evidence.get("sequence_stats") or evidence.get("sequence_type") or {}
        notes = evidence.get("notes") or []
        records = stats.get("records") or []
        record = records[0] if records else {}
        seq_type = annotation.get("primary_type") or record.get("type") or "unknown"
        length = annotation.get("length") or record.get("length")

        lines = [f"**The submitted sequence was classified as {seq_type} [tool:sequence.analyze].**"]
        lines.extend(cls._markdown_table([
            ("Detected type", seq_type),
            ("Length", length or "not specified"),
            ("Records", annotation.get("n_records") or stats.get("n_records") or len(records)),
            ("Confidence", evidence.get("confidence", "not specified")),
        ]))

        composition = record.get("composition") or {}
        if composition:
            top_items = sorted(composition.items(), key=lambda item: item[1], reverse=True)[:6]
            lines.append("\n## Composition")
            lines.append("| Residue/base | Count |")
            lines.append("| --- | --- |")
            for residue, count in top_items:
                lines.append(f"| {cls._safe_cell(residue)} | {cls._safe_cell(count)} |")

        if notes:
            lines.append("\n## Limitations")
            lines.extend(f"- {note}" for note in notes[:3])
        return "\n".join(lines)

    @classmethod
    def _summarize_literature_evidence(cls, evidence: dict[str, Any]) -> str:
        annotation = evidence.get("annotation") or {}
        pubmed = evidence.get("pubmed") or {}
        notes = evidence.get("notes") or []
        hits = pubmed.get("hits") or []
        n_hits = annotation.get("n_hits", pubmed.get("count", 0))
        query = annotation.get("query") or pubmed.get("query") or "not specified"

        lines = [f"**PubMed returned {n_hits} literature hit(s) for the query [tool:pubmed.search].**"]
        lines.extend(cls._markdown_table([
            ("Query", query),
            ("Hits", n_hits),
            ("Top PMIDs", ", ".join(annotation.get("top_pmids") or []) or "not specified"),
        ]))

        if hits:
            lines.append("\n## Top papers")
            lines.append("| PMID | Year | Title |")
            lines.append("| --- | --- | --- |")
            for hit in hits[:5]:
                pmid = cls._safe_cell(hit.get("pmid") or "")
                year = cls._safe_cell(hit.get("year") or "not specified")
                title = cls._safe_cell(cls._truncate(hit.get("title") or "not specified", 100))
                lines.append(f"| {pmid} | {year} | {title} |")

        if notes:
            lines.append("\n## Limitations")
            lines.extend(f"- {note}" for note in notes[:3])
        return "\n".join(lines)

    @staticmethod
    def _markdown_table(rows: list[tuple[str, Any]]) -> list[str]:
        lines = ["", "| Field | Value |", "| --- | --- |"]
        for key, value in rows:
            lines.append(f"| {Agent._safe_cell(key)} | {Agent._safe_cell(value)} |")
        return lines

    @staticmethod
    def _safe_cell(value: Any) -> str:
        text = "not specified" if value is None else str(value)
        text = text.replace("\r", " ").replace("\n", " ")
        return text.replace("|", "\\|").strip() or "not specified"

    @staticmethod
    def _truncate(value: Any, max_len: int) -> str:
        text = str(value or "").strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1].rstrip() + "…"


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
