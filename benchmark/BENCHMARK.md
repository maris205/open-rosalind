# Open-Rosalind — Benchmark History

> Following [`gpt4.md`](../gpt4.md): the goal is **a stable score system, not SOTA**.
> Each Open-Rosalind release runs the same Mini BioBench (`benchmark/biobench_v0.jsonl`)
> against the same 32 tasks and reports five fixed metrics.
>
> Per-version raw output lives in `benchmark/results.{json,md}`; one row per run is
> appended to `benchmark/history.jsonl` so this table can be regenerated mechanically.

## Mini BioBench v0 (32 tasks)

Categories: `sequence_basic` (8) · `literature_search` (6) · `protein_annotation` (6) ·
`mutation_effect` (6) · `protocol_reasoning` (6).

| Version | Backend | Task accuracy | Tool correctness | Evidence rate | Trace completeness | Failure rate |
|---|---|---|---|---|---|---|
| **v0.1** | gemma-4-26b-a4b-it | 96.9% | 96.9% | 100% | 100% | 0% |
| **v0.2** | gemma-4-26b-a4b-it | 100.0% | 100.0% | 100% | 100% | 0% |
| **mvp2** | gemma-4-26b-a4b-it | **100.0%** | **100.0%** | 100% | 100% | 0% |

### v0.2 → mvp2 changes

- **Standardization** (mvp2-rec2.md): Trace now includes `latency_ms` + `status`
  per tool call; three specification documents added (`docs/DESIGN_PRINCIPLES.md`,
  `docs/SKILL_SPEC.md`, `docs/EXECUTION_PROTOCOL.md`) that formalize the
  architecture for reproducibility and extensibility.
- **React UI**: Session sidebar, collapsible trace, human-readable evidence view,
  confidence bar, follow-up support.
- **AgentRunner**: Follow-up queries can reference prior session evidence.
- **SessionMemory**: JSONL-backed session store with event stream.
- **Skills Registry**: All 4 skills now declare full metadata (schema, examples,
  safety_level, tools_used) and are exposed via `/api/skills` + CLI.

Zero regression: all 32 tasks pass with 100% across all 5 metrics.

## Metric definitions (per gpt4.md)

- **Task accuracy** — strict per-task pass/fail. A task passes only if all of the
  following hold: skill routed correctly, every expected tool was called, the
  semantic check on the structured output succeeds, ≥60% of expected keywords
  appear somewhere in the response, and the per-task `must_have_evidence` /
  `must_have_trace` flags are satisfied.
- **Tool correctness** — fraction of tasks where every expected tool was actually
  invoked (`expected_tools ⊆ trace_steps`).
- **Evidence rate** — fraction of tasks where the response carries non-empty
  evidence and respects the per-task `must_have_evidence` flag.
- **Trace completeness** — fraction of tasks with non-empty `trace_steps`
  satisfying `must_have_trace`.
- **Failure rate** — fraction of tasks that hit a hard error (HTTP 5xx, network
  exception, or every tool call errored).

## Why the early baseline is high

Open-Rosalind v0.1 already enforces three things that most LLM-only baselines
miss:
1. Every task is routed through a hand-written rule-based router → there is no
   "I forgot to call the tool" failure mode (cf. tool-correctness 96.9%).
2. Every step writes to a JSONL trace before returning → `trace completeness` is
   essentially a property of the framework, not the model (100%).
3. The LLM is forbidden from speaking outside the EVIDENCE blob, so failures
   surface as wrong **routing** or wrong **check value**, not as hallucinated
   facts. The single v0.1 miss (`pro-05`) is a routing failure: a free-text
   "Translate this DNA: …" prompt was classified as `uniprot_lookup` instead of
   `sequence_basic_analysis`. That is exactly the kind of issue an LLM-driven
   planner in v0.2 should fix.

## What v0.2 → v0.3 should improve

- **Routing** — already addressed in v0.2 via LLM-assisted intent classifier;
  pro-05 went from miss → pass.
- **Tool correctness** — keep at 100%; consider always calling
  `uniprot.search` for any protein ≥25 aa to densify homology hints.
- **Recall on mutation flags** — current rule-based heuristic flags charge /
  aromatic / disulfide changes; we will add Grantham distance + AlphaMissense
  lookup in v0.3.
- **Bench coverage** — current 32 tasks all have unambiguous gold answers.
  v0.3 should add ~10 open-ended protocol-reasoning tasks scored by
  pairwise LLM judging.

## How to reproduce

```bash
# 1. run the agent
python -m open_rosalind.cli serve --port 6006 &

# 2. run the bench (tags this run as v0.1, appends to history.jsonl)
python benchmark/run_biobench.py --version v0.1 \
    --tasks benchmark/biobench_v0.jsonl \
    --base-url http://127.0.0.1:6006 \
    --out benchmark/results.json \
    --summary benchmark/results.md \
    --history benchmark/history.jsonl
```

Each run appends one line to `benchmark/history.jsonl` — re-running this
script after a v0.2 release is enough to add a row to the table above.
