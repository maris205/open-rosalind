# Open-Rosalind

> Local-first, tool-driven life-science research agent.
> Model layer is **OmniGene-4** (default); agent is **model-agnostic** — any
> OpenAI-compatible chat endpoint works.

This repository hosts the **MVP1** of Open-Rosalind: a hosted web demo with
three biology skills, a trace logger, and a pluggable backend. See
[`open-rosalind.md`](./open-rosalind.md) for the full design doc and
[`gpt1.md`](./gpt1.md) for the MVP1 scope.

```
MVP1 = Hosted Web Demo + 3 Bio Skills + Trace + Demo Pipeline
```

## Layout

```
open_rosalind/
├── orchestrator/   # rule-based router, agent loop, JSONL trace
├── tools/          # sequence (local), uniprot, pubmed
├── skills/         # sequence_basic_analysis, uniprot_lookup, literature_search
├── backends/       # openrouter (default; pluggable)
├── server.py       # FastAPI app
└── cli.py          # `open-rosalind serve | ask`
web/                # plain HTML/JS frontend
configs/default.yaml
prompts/
traces/             # JSONL traces, one file per session
```

## Quick start

```bash
# 1. install deps (no requirements.txt by design — install manually)
pip install fastapi uvicorn openai requests pydantic biopython pyyaml

# 2. set the OpenRouter key (or copy .env.example → .env)
export OPENROUTER_API_KEY=sk-or-v1-...

# 3. run the web demo on port 6006
python -m open_rosalind.cli serve

# 4. or one-shot CLI
python -m open_rosalind.cli ask "What is BRCA1 and where is it located?"
```

Open `http://127.0.0.1:6006/` and try the demo prompts.

## Skills (MVP1)

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

## Mini BioBench v0

A small but real benchmark (26 tasks across sequence / literature /
annotation / mutation) ships with the repo:

```bash
python -m open_rosalind.cli serve &           # start the agent
python benchmark/run_biobench.py              # score it
```

Latest run on `google/gemma-4-26b-a4b-it`:

| Metric | Value |
|---|---|
| Accuracy (semantic check) | **100%** (26/26) |
| Skill routed correctly | 100% |
| Expected tools called | 100% |
| Has trace / has evidence | 100% / 100% |

Per-task breakdown lives in [`benchmark/results.md`](./benchmark/results.md);
the raw JSON in `benchmark/results.json`.

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
