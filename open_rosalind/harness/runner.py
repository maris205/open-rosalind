"""TaskRunner: Executes multi-step tasks by orchestrating Agent calls.

Principles:
- Failure doesn't abort the entire task
- Every step must have trace
- Every step must record evidence
- Final report only based on evidence_pool
"""
from __future__ import annotations

import re
import time
from typing import Any

from .contracts import StepExecutor, StepResult
from .planner import ConstrainedPlanner
from .task import Task, TaskStep


class TaskRunner:
    """Orchestrates multi-step task execution."""

    def __init__(self, agent_adapter: StepExecutor):
        self.agent_adapter = agent_adapter
        self.planner = ConstrainedPlanner()

    def run(self, task: Task) -> Task:
        """
        Execute a multi-step task.

        Args:
            task: Task with user_goal and max_steps

        Returns:
            Completed task with steps, evidence, trace, final_report
        """
        task.status = "running"

        # 1. Generate plan
        plan = self.planner.create_plan(task.user_goal, task.max_steps)
        task.steps = plan

        # 2. Execute steps sequentially
        for i, step in enumerate(task.steps):
            task.state.current_step = i + 1
            step.status = "running"

            t0 = time.time()
            result = self.agent_adapter.run_step(
                instruction=step.instruction,
                context=task.state.known_entities,
                expected_workflow=step.expected_workflow,
                payload_hint=step.payload_hint,
            )
            step.latency_ms = int((time.time() - t0) * 1000)

            self._apply_step_result(task, step, result)

        # 3. Build final report
        task.final_report = self._build_report(task)
        task.status = "completed"
        return task

    def _apply_step_result(self, task: Task, step: TaskStep, result: StepResult) -> None:
        """Apply the adapter result to task/step state.

        TaskRunner only understands StepResult. It never reaches into skills or
        tools directly.
        """
        step.status = result.status
        step.agent_result = result.to_dict()
        step.evidence = [result.evidence]
        step.trace = result.trace
        step.error = result.error

        if result.status == "success":
            task.state.known_entities.update(result.extracted_entities)
            task.state.evidence_pool.extend(step.evidence)
            task.state.trace_refs.append(f"{task.task_id}/step_{step.step_id}")
        else:
            task.add_warning(step, result.error or "Unknown error")

    def _build_report(self, task: Task) -> str:
        """
        Synthesize final report from evidence_pool.

        Report structure:
        - User-facing summary first
        - Structured annotation
        - Evidence/source grounding
        - Workflow trace
        - Confidence
        """
        lines: list[str] = []

        lines.extend(["## Summary", self._summary_sentence(task), ""])

        annotation_rows = self._annotation_rows(task)
        if annotation_rows:
            lines.append("## Annotation")
            lines.extend(self._markdown_table(["Field", "Value"], annotation_rows))
            lines.append("")

        evidence_rows = self._evidence_rows(task)
        if evidence_rows:
            lines.append("## Evidence / Sources")
            lines.extend(self._markdown_table(["Source", "Record", "Supports"], evidence_rows))
            lines.append("")

        workflow_rows = self._workflow_rows(task)
        if workflow_rows:
            lines.append("## Workflow Trace")
            lines.extend(self._markdown_table(["Step", "Workflow", "Status", "Time"], workflow_rows))
            lines.append("")

        lines.extend(["## Confidence", self._confidence_sentence(task), ""])

        if task.warnings:
            lines.append("## Warnings")
            for warning in task.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines).strip()

    def _summary_sentence(self, task: Task) -> str:
        parts: list[str] = []

        protein = self._first_evidence(task, kind="protein")
        if protein:
            annotation = protein.get("annotation") or {}
            entry = protein.get("entry") or {}
            search = protein.get("search") or {}
            accession = entry.get("accession") or annotation.get("accession")
            name = entry.get("name") or annotation.get("name") or accession or "the target protein"
            organism = entry.get("organism") or annotation.get("organism")
            function = entry.get("function") or annotation.get("function")
            target = self._query_label(search.get("query")) or name
            citation = f"[UniProt:{accession}]" if accession else "[tool:uniprot.search]"
            if function:
                function_summary = self._strip_parenthetical_citations(function)
                parts.append(
                    f"{target} resolves to {name}"
                    f"{f' in {organism}' if organism else ''}; UniProt describes it as "
                    f"{self._truncate(function_summary, 260)} {citation}."
                )
            else:
                parts.append(
                    f"{target} resolves to {name}"
                    f"{f' in {organism}' if organism else ''} {citation}."
                )

        sequence = self._first_evidence(task, kind="sequence")
        if sequence and not parts:
            stats = sequence.get("sequence_stats") or {}
            records = stats.get("records") or []
            rec = records[0] if records else {}
            seq_type = rec.get("type") or "sequence"
            length = rec.get("length")
            detail = f"{seq_type}"
            if length:
                detail += f" sequence of length {length}"
            translation = rec.get("translation_preview")
            if translation:
                detail += f" with translation preview {translation}"
            parts.append(f"The input was analyzed as a {detail} [tool:sequence.analyze].")

        blast = self._first_evidence(task, kind="ncbi_blast")
        if blast:
            blast_result = blast.get("blast") or {}
            query_summaries = blast_result.get("query_summaries") or []
            top_query = query_summaries[0] if query_summaries else {}
            top_hits = top_query.get("top_hits") or []
            hit_count = top_query.get("hit_count_returned") or blast.get("annotation", {}).get("n_records") or 0
            if top_hits:
                top_hit = top_hits[0]
                title = top_hit.get("title") or top_hit.get("accession") or "top hit"
                parts.append(
                    f"NCBI BLAST returned {hit_count} similar-protein hit(s); the top hit was "
                    f"{self._truncate(title, 120)} [tool:ncbi_blast.run_search]."
                )
            else:
                status = blast_result.get("status") or "no returned hit table"
                parts.append(f"NCBI BLAST completed with status {status} [tool:ncbi_blast.run_search].")

        literature = self._first_evidence(task, kind="literature")
        if literature:
            pubmed = literature.get("pubmed") or {}
            metadata = literature.get("metadata") or {}
            records = metadata.get("records") or pubmed.get("hits") or []
            count = pubmed.get("count") or literature.get("annotation", {}).get("n_hits") or len(records)
            if records:
                top = records[0]
                pmid = top.get("pmid")
                title = top.get("title") or "top retrieved paper"
                citation = f"[PMID:{pmid}]" if pmid else "[tool:pubmed.search]"
                parts.append(
                    f"PubMed returned {count} related paper(s); the top retrieved paper was "
                    f"{self._truncate(title, 140)} {citation}."
                )
            else:
                parts.append(f"PubMed returned {count} related paper(s) [tool:pubmed.search].")

        mutation = self._first_evidence(task, kind="mutation")
        if mutation and not parts:
            annotation = mutation.get("annotation") or {}
            assessment = annotation.get("overall_assessment") or "mutation assessment completed"
            n_differences = annotation.get("n_differences")
            if n_differences is not None:
                parts.append(
                    f"The mutation workflow found {n_differences} sequence difference(s) and assessed the result as "
                    f"{assessment} [tool:mutation.diff]."
                )
            else:
                parts.append(f"The mutation workflow assessed the result as {assessment} [tool:mutation.diff].")

        if parts:
            return " ".join(parts)

        lead_summaries = [
            self._lead_summary(str((step.agent_result or {}).get("summary") or ""))
            for step in task.steps
            if step.agent_result and (step.agent_result or {}).get("summary")
        ]
        lead_summaries = [summary for summary in lead_summaries if summary]
        if lead_summaries:
            return " ".join(lead_summaries[:2])

        success_count = sum(1 for step in task.steps if step.status == "success")
        return (
            f"The workflow completed {success_count}/{len(task.steps)} step"
            f"{'' if len(task.steps) == 1 else 's'}, but no concise scientific summary was available."
        )

    def _annotation_rows(self, task: Task) -> list[list[Any]]:
        rows: list[list[Any]] = []

        protein = self._first_evidence(task, kind="protein")
        if protein:
            annotation = protein.get("annotation") or {}
            entry = protein.get("entry") or {}
            accession = entry.get("accession") or annotation.get("accession")
            rows.extend([
                ["Protein", entry.get("name") or annotation.get("name") or "not specified"],
                ["UniProt accession", accession or "not found"],
                ["Organism", entry.get("organism") or annotation.get("organism") or "not specified"],
                ["Length", f"{entry.get('length')} aa" if entry.get("length") else "not specified"],
            ])

        sequence = self._first_evidence(task, kind="sequence")
        if sequence:
            stats = sequence.get("sequence_stats") or {}
            records = stats.get("records") or []
            rec = records[0] if records else {}
            rows.extend([
                ["Sequence type", rec.get("type") or "not specified"],
                ["Sequence length", rec.get("length") or "not specified"],
            ])
            if rec.get("translation_preview"):
                rows.append(["Translation preview", rec.get("translation_preview")])

        literature = self._first_evidence(task, kind="literature")
        if literature:
            annotation = literature.get("annotation") or {}
            pmids = annotation.get("top_pmids") or []
            rows.extend([
                ["Literature query", annotation.get("query") or "not specified"],
                ["PubMed hits", annotation.get("n_hits") if annotation.get("n_hits") is not None else "not specified"],
            ])
            if pmids:
                rows.append(["Top PMIDs", ", ".join(str(pmid) for pmid in pmids[:5])])

        mutation = self._first_evidence(task, kind="mutation")
        if mutation:
            annotation = mutation.get("annotation") or {}
            rows.extend([
                ["Mutation", annotation.get("mutation") or "not specified"],
                ["Differences", annotation.get("n_differences") if annotation.get("n_differences") is not None else "not specified"],
                ["Assessment", annotation.get("overall_assessment") or "not specified"],
            ])

        blast = self._first_evidence(task, kind="ncbi_blast")
        if blast:
            blast_result = blast.get("blast") or {}
            rows.extend([
                ["BLAST program", blast_result.get("program") or blast.get("annotation", {}).get("program") or "not specified"],
                ["BLAST database", blast_result.get("database") or blast.get("annotation", {}).get("database") or "not specified"],
                ["BLAST status", blast_result.get("status") or "not specified"],
            ])

        return rows

    def _evidence_rows(self, task: Task) -> list[list[Any]]:
        rows: list[list[Any]] = []
        for step in task.steps:
            evidence = self._step_evidence(step)
            if not evidence:
                continue
            annotation = evidence.get("annotation") or {}
            kind = annotation.get("kind") or annotation.get("workflow") or step.expected_workflow
            source = self._workflow_label(kind)
            record = self._evidence_record(evidence)
            supports = self._lead_summary(str((step.agent_result or {}).get("summary") or ""), max_len=180)
            rows.append([source, record, supports or step.instruction])
        return rows

    def _workflow_rows(self, task: Task) -> list[list[Any]]:
        rows: list[list[Any]] = []
        for index, step in enumerate(task.steps, 1):
            executed = (step.agent_result or {}).get("extracted_entities", {}).get("workflow")
            workflow = executed or step.expected_workflow
            status = step.status
            if step.error:
                status = f"{status}: {step.error}"
            elapsed = f"{step.latency_ms} ms" if step.latency_ms is not None else "not recorded"
            rows.append([f"{index}. {step.step_id}", self._workflow_label(workflow), status, elapsed])
        return rows

    def _confidence_sentence(self, task: Task) -> str:
        values: list[float] = []
        for step in task.steps:
            confidence = (step.agent_result or {}).get("confidence")
            if isinstance(confidence, (int, float)):
                values.append(float(confidence))
        score = sum(values) / len(values) if values else 0.0
        if score >= 0.85:
            label = "High"
        elif score >= 0.6:
            label = "Medium"
        elif score >= 0.3:
            label = "Low"
        else:
            label = "Very low"
        success_count = sum(1 for step in task.steps if step.status == "success")
        trace_count = sum(1 for step in task.steps if step.trace)
        return (
            f"{label} confidence ({score:.2f}). This is based on {success_count}/{len(task.steps)} "
            f"successful workflow step(s), {len(task.state.evidence_pool)} structured evidence record(s), "
            f"and trace output for {trace_count}/{len(task.steps)} step(s)."
        )

    def _first_evidence(self, task: Task, kind: str) -> dict[str, Any] | None:
        for step in task.steps:
            evidence = self._step_evidence(step)
            annotation = evidence.get("annotation") or {}
            if annotation.get("kind") == kind:
                return evidence
            if kind == "sequence" and annotation.get("kind") in {"sequence", "sequence_type"}:
                return evidence
            if kind == "ncbi_blast" and (annotation.get("kind") == "ncbi_blast" or evidence.get("blast")):
                return evidence
        return None

    @staticmethod
    def _step_evidence(step: TaskStep) -> dict[str, Any]:
        if step.agent_result and isinstance(step.agent_result.get("evidence"), dict):
            return step.agent_result["evidence"]
        if step.evidence:
            return step.evidence[0]
        return {}

    @classmethod
    def _evidence_record(cls, evidence: dict[str, Any]) -> str:
        annotation = evidence.get("annotation") or {}
        kind = annotation.get("kind")

        if kind == "protein":
            accession = annotation.get("accession") or (evidence.get("entry") or {}).get("accession")
            return f"[UniProt:{accession}]" if accession else "[tool:uniprot.search]"

        if kind == "literature":
            pmids = annotation.get("top_pmids") or []
            if pmids:
                return ", ".join(f"[PMID:{pmid}]" for pmid in pmids[:5])
            return "[tool:pubmed.search]"

        if kind in {"sequence", "sequence_type"}:
            return "[tool:sequence.analyze]"

        if kind == "mutation":
            return "[tool:mutation.diff]"

        if kind == "ncbi_blast" or evidence.get("blast"):
            rid = (evidence.get("blast") or {}).get("rid") or annotation.get("rid")
            return f"RID {rid} [tool:ncbi_blast.run_search]" if rid else "[tool:ncbi_blast.run_search]"

        workflow = annotation.get("workflow")
        return f"[workflow:{workflow}]" if workflow else "[tool evidence]"

    @staticmethod
    def _workflow_label(value: Any) -> str:
        text = str(value or "workflow").strip()
        if not text:
            return "Workflow"
        return text.replace("workflow_", "").replace("_", " ").title()

    @staticmethod
    def _query_label(query: Any) -> str | None:
        if not query:
            return None
        text = str(query)
        if ":" in text:
            text = text.split(":", 1)[1]
        return text.strip() or None

    @classmethod
    def _markdown_table(cls, headers: list[str], rows: list[list[Any]]) -> list[str]:
        if not rows:
            return []
        lines = [
            "| " + " | ".join(cls._safe_cell(header) for header in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in rows:
            padded = list(row) + [""] * max(0, len(headers) - len(row))
            lines.append("| " + " | ".join(cls._safe_cell(value) for value in padded[:len(headers)]) + " |")
        return lines

    @staticmethod
    def _safe_cell(value: Any) -> str:
        if value is None:
            return "not specified"
        text = str(value).replace("\r\n", " ").replace("\n", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text.replace("|", "\\|") or "not specified"

    @staticmethod
    def _truncate(text: Any, max_len: int) -> str:
        clean = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(clean) <= max_len:
            return clean
        return clean[: max_len - 1].rstrip() + "..."

    @staticmethod
    def _strip_parenthetical_citations(text: Any) -> str:
        clean = str(text or "")
        clean = re.sub(r"\s*\((?:PubMed:\d+(?:,\s*)?)+\)", "", clean)
        return re.sub(r"\s+", " ", clean).strip()

    @staticmethod
    def _lead_summary(summary: str, max_len: int = 240) -> str:
        text = (summary or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            return ""

        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        preferred = ""
        for part in paragraphs:
            first_line = next((line.strip() for line in part.splitlines() if line.strip()), "")
            if first_line and not first_line.startswith("|") and not first_line.startswith("##"):
                preferred = first_line
                break
        if not preferred and paragraphs:
            preferred = paragraphs[0].splitlines()[0].strip()

        preferred = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", preferred)
        preferred = re.sub(r"[*`~]", "", preferred)
        preferred = re.sub(r"\s+", " ", preferred).strip()
        if not preferred:
            return ""
        return preferred[: max_len - 1].rstrip() + "…" if len(preferred) > max_len else preferred
