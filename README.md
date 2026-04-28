# Open-Rosalind

> **Local-first, tool-driven bioinformatics agent**

A standardized bio-agent framework that prioritizes reproducibility, extensibility, and scientific rigor. Built on tool-first architecture with evidence-grounded outputs and complete execution traces.

**Current release**: MVP2 (tag `mvp2`)

```
MVP2 = Skills Registry + React UI + SessionMemory + AgentRunner + Standardization
```

## Features

- **4 Bio Skills**: sequence analysis, UniProt lookup, PubMed search, mutation effect
- **Skills Registry**: Uniform interface (schema, examples, safety_level) for extensibility
- **React UI**: Session sidebar, collapsible trace, human-readable evidence, confidence bar
- **Session Memory**: JSONL-backed history with follow-up support
- **Trace-First**: Every tool call logged with latency + status for reproducibility
- **Evidence-Grounded**: LLM summary must cite tool outputs (`[UniProt:P38398]`, `[PMID:12345]`)
- **Pluggable Backend**: OpenRouter (default), any OpenAI-compatible endpoint
- **BioBench**: 49-task evaluation suite (93.9% accuracy on MVP2)

## Quick Start

```bash
# 1. Install deps
pip install fastapi uvicorn openai requests pydantic biopython pyyaml

# 2. Set OpenRouter key
export OPENROUTER_API_KEY=sk-or-v1-...

# 3. Run web demo (React UI on port 6006)
python -m open_rosalind.cli serve

# 4. Or one-shot CLI
python -m open_rosalind.cli ask "What is BRCA1?"

# 5. List skills
python -m open_rosalind.cli skills list
```

Open `http://127.0.0.1:6006/` — try the demo prompts in the dropdown.

## Architecture

```
open_rosalind/
├── orchestrator/   # Router, AgentRunner, trace, intent classifier
├── tools/          # Atomic tools (sequence, uniprot, pubmed, mutation)
├── skills/         # Pipelines with fallback (4 registered skills)
├── backends/       # OpenRouter (default), pluggable
├── session.py      # JSONL session store
├── server.py       # FastAPI app
└── cli.py          # CLI (serve | ask | skills list/inspect)
web-react/          # Vite + React 18 frontend
web/dist/           # Production build (served by FastAPI)
docs/               # DESIGN_PRINCIPLES, SKILL_SPEC, EXECUTION_PROTOCOL
benchmark/          # BioBench v0 (32 tasks) + v1 (49 tasks)
traces/             # JSONL traces (one per session)
sessions/           # JSONL session events
```

## Skills (MVP2)

| Skill | Triggers | Tools used |
|---|---|---|
| `sequence_basic_analysis` | FASTA / raw DNA / protein sequence | `sequence.analyze` (local) → optional `uniprot.search` probe |
| `uniprot_lookup` | UniProt accession or generic protein/gene question | `uniprot.fetch`, `uniprot.search` |
| `literature_search` | "papers / pubmed / literature / cite ..." | `pubmed.search` |
| `mutation_effect` | `WT: ... / MT: p.R175H` block, or two FASTA records | `mutation.diff` (local rule-based) |

See [`docs/DEMOS.md`](./docs/DEMOS.md) for fully-worked end-to-end runs of all four demos
(question → routing → tool calls → evidence → LLM summary).

## API response shape

Every `POST /api/analyze` returns the same five top-level fields, so a UI or
an evaluator never has to special-case skills:

```json
{
  "summary":    "Markdown answer with [UniProt:...] / [PMID:...] inline citations",
  "annotation": { "kind": "protein|literature|mutation", "...": "..." },
  "confidence": 0.0,
  "notes":      ["original query had 0 hits, used token 'BRCA1' (fallback)"],
  "evidence":   { "...raw tool outputs..." },
  "trace_steps":[ {"skill": "uniprot.search", "input": {...}, "output": {...}} ]
}
```

`notes` is non-empty whenever the pipeline took a non-trivial path (retry,
fallback, partial failure) — these are surfaced to the user, not hidden.

## Evaluation

**BioBench v0** (Mini BioBench, 32 tasks):

```bash
python -m open_rosalind.cli serve &
python benchmark/run_biobench.py --version mvp2
```

| Version | Task accuracy | Tool correctness | Evidence | Trace | Failure |
|---|---|---|---|---|---|
| v0.1 (rule router) | 96.9% | 96.9% | 100% | 100% | 0% |
| v0.2 (+ LLM classifier) | 100.0% | 100.0% | 100% | 100% | 0% |
| **mvp2** (standardized) | **100.0%** | **100.0%** | 100% | 100% | 0% |

**BioBench v1** (49 tasks, workflow + fallback + edge cases):

| Version | Task accuracy | Tool correctness | Evidence | Trace | Failure |
|---|---|---|---|---|---|
| **mvp2** | **93.9%** (46/49) | 100.0% | 100.0% | 100.0% | 0.0% |

See [`benchmark/BENCHMARK.md`](./benchmark/BENCHMARK.md) and [`benchmark/BIOBENCH_V1_DESIGN.md`](./benchmark/BIOBENCH_V1_DESIGN.md).

Per-run details live in [`benchmark/results.md`](./benchmark/results.md);
the cross-version comparison table in [`benchmark/BENCHMARK.md`](./benchmark/BENCHMARK.md);
each run also appends one line to `benchmark/history.jsonl` for mechanical
re-aggregation.

## Backend

Default: OpenRouter `google/gemma-4-26b-a4b-it`. Swap by editing
`configs/default.yaml` — the agent only depends on a `chat(messages)` interface.

## Trace

Every session writes one JSONL file under `traces/`. One line per event:
`user_input`, `plan`, `tool_call`, `tool_result`, `fallback`, `evidence`,
`model_request`, `model_response`. Replaying the trace re-creates the run.

## Roadmap

This is **v0.1**. v0.2+ adds BLAST / Foldseek / PDB tools, a code executor,
LLM-driven planner, OmniGene-4 backend, and the full BixBench harness.

---

## Documentation

- [`docs/DESIGN_PRINCIPLES.md`](./docs/DESIGN_PRINCIPLES.md) — 8 core principles (tool-first, evidence-grounded, traceable, workflow-constrained, ...)
- [`docs/SKILL_SPEC.md`](./docs/SKILL_SPEC.md) — Standard skill interface (schema, examples, safety_level, handler contract)
- [`docs/EXECUTION_PROTOCOL.md`](./docs/EXECUTION_PROTOCOL.md) — MCP-inspired workflow (route → plan → execute → observe → summarize → return)
- [`benchmark/BIOBENCH_V1_DESIGN.md`](./benchmark/BIOBENCH_V1_DESIGN.md) — BioBench v1 specification (workflow verification, multi-step, fallback)

---

## Releases

- **mvp1** (tag `mvp1`) — Baseline: 4 skills + trace + Mini BioBench v0.2 (100%)
- **mvp2** (tag `mvp2`) — Standardized framework: Skills Registry + React UI + SessionMemory + AgentRunner + BioBench v1 (93.9%)

---

## Citation

```bibtex
@software{open_rosalind_2026,
  title = {Open-Rosalind: A Standardized Bio-Agent Framework},
  author = {Wang, Liang},
  year = {2026},
  url = {https://github.com/maris205/open-rosalind},
  note = {Tool-first, evidence-grounded, traceable bio-agent with 100\% on Mini BioBench}
}
```
