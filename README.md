# 🧬 Open-Rosalind

> **A chat-based bioinformatics agent that grounds every answer in real database evidence.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![BioBench v0](https://img.shields.io/badge/BioBench_v0-100%25-brightgreen)](benchmark/BENCHMARK.md)
[![BioBench v1](https://img.shields.io/badge/BioBench_v1-93.9%25-green)](benchmark/BENCHMARK.md)
[![BioBench v0.3](https://img.shields.io/badge/BioBench_v0.3_(harness)-90%25-green)](benchmark/BENCHMARK.md)

Ask in natural language → get a structured scientific answer backed by UniProt, PubMed, and local computation. **No hallucinations** — every claim cites a tool output.

```
You: What is BRCA1?
Open-Rosalind: P38398 is the Breast cancer type 1 susceptibility protein
                in Homo sapiens [UniProt:P38398]. It functions as an
                E3 ubiquitin-protein ligase... [+ confidence + trace]

You: find papers about this protein
Open-Rosalind: 🔗 Multi-step auto-detected.
               → uniprot.fetch → literature_search
               → 5 PubMed papers about BRCA1 [PMID:...]
```

---

## ✨ Why Open-Rosalind

| Most LLM-bio assistants | Open-Rosalind |
|---|---|
| ❌ Hallucinate accessions, PMIDs | ✅ Every claim cites a real tool output |
| ❌ "Black box" reasoning | ✅ Full execution trace per turn |
| ❌ One-shot prompts | ✅ Multi-step task harness with planner |
| ❌ Closed-source SaaS | ✅ MIT, self-hostable, model-agnostic |
| ❌ No benchmark | ✅ BioBench v0/v1/v0.3 with 5 standard metrics |

**Design principles** (see [`docs/DESIGN_PRINCIPLES.md`](./docs/DESIGN_PRINCIPLES.md)):
- **Tool-first** — every fact comes from a registered tool, never from LLM memory
- **Evidence-grounded** — LLM may only synthesize what tools return
- **Traceable** — every tool call is logged with input/output/latency
- **Workflow-constrained** — bounded planner (max 5 steps), no free-form recursion

---

## 🚀 Quick Start

```bash
# 1. Install Python deps
pip install fastapi uvicorn openai requests pydantic biopython pyyaml

# 2. Set the OpenRouter key (or any OpenAI-compatible endpoint)
export OPENROUTER_API_KEY=sk-or-v1-...

# 3. Build the React UI (one-time)
cd web-react && npm install && npm run build && cd ..

# 4. Run the agent
python -m open_rosalind.cli serve

# Open http://127.0.0.1:6006/ — try a demo prompt!
```

**No signup needed** to try — anonymous users get one free session. To save more conversations, sign up with email + password (no email verification).

### CLI alternative

```bash
# Single question
python -m open_rosalind.cli ask "What is BRCA1?"

# Multi-step task
python -m open_rosalind.cli task run "Analyze sequence MVKVGVNGFGRIGRLVTRA and find similar proteins"

# List/inspect skills
python -m open_rosalind.cli skills list
python -m open_rosalind.cli skills inspect uniprot_lookup
```

---

## 🧩 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  React Chat UI (web-react/)                  │
│       chat timeline · sessions · evidence + trace cards      │
└────────────────────────────┬─────────────────────────────────┘
                             │ /api/chat (auto-mode select)
┌────────────────────────────▼─────────────────────────────────┐
│                    Mode Selector                             │
│   "Find papers AND ..." → harness · single sequence → agent  │
└─────────┬────────────────────────────────────┬───────────────┘
          │                                    │
┌─────────▼─────────┐              ┌───────────▼─────────────┐
│  Single-step      │              │   Multi-step Harness    │
│  Agent + Router   │              │   ConstrainedPlanner    │
│  + LLM-classify   │              │   (max 5 steps)         │
└─────────┬─────────┘              └───────────┬─────────────┘
          │                                    │
          └────────────┬───────────────────────┘
                       │
            ┌──────────▼──────────────┐
            │   Skills (skills_v2/)   │
            │  sequence · uniprot     │
            │  literature · mutation  │
            └──────────┬──────────────┘
                       │
            ┌──────────▼──────────────┐
            │   Tools (atomic API)    │
            │  UniProt · PubMed       │
            │  BioPython · diff       │
            └──────────┬──────────────┘
                       │
            ┌──────────▼──────────────┐
            │ SQLite + JSONL traces   │
            │ users · sessions ·      │
            │ messages · traces       │
            └─────────────────────────┘
```

### Skills are modular

Each skill is a self-contained directory with standard structure (inspired by [Claude skills](https://docs.claude.com/en/docs/build-with-claude/skills) and [DeerFlow skills](https://github.com/bytedance/deerflow)):

```
skills_v2/uniprot/
├── SKILL.md         # frontmatter + workflow + examples
├── skill.json       # schema + safety_level + tools_used
├── handler.py       # pipeline logic
├── tools.py         # API client
└── examples/        # test cases
```

Add a new skill = drop a directory. Auto-discovery picks it up. See [`docs/SKILL_SPEC.md`](./docs/SKILL_SPEC.md).

---

## 📊 Benchmarks

Open-Rosalind ships with **BioBench**, a benchmark suite specifically for bio-agents (not LLM knowledge). Tasks must trigger tool calls — pure-knowledge prompts don't count.

| Benchmark | Tasks | Latest score (gemma-4-26b-a4b-it) |
|---|---|---|
| **BioBench v0** (basic skills) | 32 | **100.0%** |
| **BioBench v1** (workflow + edge cases + follow-up) | 49 | **93.9%** |
| **BioBench v0.3** (multi-step harness) | 10 | **90.0%** |

Five standard metrics (see [`develop/gpt4.md`](./develop/gpt4.md) and [`benchmark/BENCHMARK.md`](./benchmark/BENCHMARK.md)):
- Task accuracy
- Tool correctness
- Evidence rate
- Trace completeness
- Failure rate

```bash
# Reproduce
python -m open_rosalind.cli serve &
python benchmark/run_biobench.py --version mine
```

---

## 🛠️ Built-in Skills

| Skill | What it does | Tools used |
|---|---|---|
| `sequence_basic_analysis` | DNA/RNA/protein stats, GC%, translation, MW; auto-probes UniProt for protein homology | BioPython · `uniprot.search` |
| `uniprot_lookup` | Resolve accession or free-text query → structured annotation | `uniprot.fetch` · `uniprot.search` |
| `literature_search` | PubMed search with query cleaning + year-filter fallback | `pubmed.search` |
| `mutation_effect` | WT vs MT diff, HGVS parsing, physico-chemical impact heuristic | `mutation.diff` (local) |

---

## 🔄 Multi-Step Harness

For tasks that need multiple tools, the **Constrained Planner** picks one of 3 hard-coded templates:

| Template | Steps |
|---|---|
| `protein_research` | sequence_basic_analysis → uniprot_lookup → literature_search |
| `literature_review` | literature_search |
| `mutation_assessment` | mutation_effect → uniprot_lookup → literature_search |

No free-form planning — bounded `max_steps`, no infinite loops, no autonomous tool invention. See [`docs/EXECUTION_PROTOCOL.md`](./docs/EXECUTION_PROTOCOL.md) and [`docs/MVP3_HARNESS.md`](./docs/MVP3_HARNESS.md).

---

## 🧪 In-session Context

Multi-turn conversations carry context automatically:

```
Turn 1:  介绍下 Q9H3P7
Turn 2:  这个蛋白质在别的物种中也有吗     ← agent knows it's still Q9H3P7
Turn 3:  它的功能是什么                   ← still Q9H3P7
```

Implementation: industry-standard sliding-window history (last 6 turns, 1.5K chars per turn) + entity injection from prior annotation. See `orchestrator/history.py`.

**Not** long-term memory — context window only. Cleared on new conversation.

---

## 🔌 API

```
POST /api/chat                     # main entrypoint (auto mode select)
POST /api/auth/signup              # email + password (no verification)
POST /api/auth/login
GET  /api/auth/me

GET  /api/chat/sessions            # user's sessions (sidebar)
GET  /api/chat/sessions/{id}       # full message history (replay)
GET  /api/chat/sessions/{id}/traces  # tool-call analytics

GET  /api/skills                   # list registered skills
GET  /api/skills/{name}            # full schema + examples
GET  /api/skillsv2                 # auto-discovered modular skills

GET  /api/stats                    # n_users, n_traces, top_skills, avg_latency
```

Anonymous users get a single sticky session via `anon_token` (returned on first call, sent on subsequent calls).

---

## 📦 Repository Layout

```
open_rosalind/
├── orchestrator/      router · agent · runner · history
├── harness/           Task · Planner · Runner · TaskTrace
├── skills/            (legacy) flat-file skills
├── skills_v2/         modular skills (SKILL.md + handler.py + tools.py)
├── tools/             atomic API clients (UniProt · PubMed · sequence · mutation)
├── backends/          OpenRouter (default) · pluggable
├── storage.py         SQLite (users · sessions · messages · traces)
├── server.py          FastAPI app
└── cli.py             open-rosalind serve | ask | task | skills

web-react/             Vite + React 18 chat UI
benchmark/             BioBench v0/v1/v0.3 + run_biobench.py
docs/                  design + skill spec + execution protocol
develop/               development notes (gpt*.md, mvp*.md)
traces/                JSONL trace audit log
sessions/              JSONL session events
task_traces/           JSONL multi-step task traces
```

---

## 📚 Documentation

| Document | What it covers |
|---|---|
| [`docs/DESIGN_PRINCIPLES.md`](./docs/DESIGN_PRINCIPLES.md) | The 8 core principles (tool-first, evidence-grounded, …) |
| [`docs/SKILL_SPEC.md`](./docs/SKILL_SPEC.md) | How skills are structured + how to add one |
| [`docs/EXECUTION_PROTOCOL.md`](./docs/EXECUTION_PROTOCOL.md) | MCP-inspired execution model |
| [`docs/MVP3_HARNESS.md`](./docs/MVP3_HARNESS.md) | Multi-step planning + execution |
| [`docs/SKILLS_V2_DESIGN.md`](./docs/SKILLS_V2_DESIGN.md) | Modular skills architecture |
| [`benchmark/BENCHMARK.md`](./benchmark/BENCHMARK.md) | Bench history + metric definitions |
| [`benchmark/BIOBENCH_V1_DESIGN.md`](./benchmark/BIOBENCH_V1_DESIGN.md) | Bench task format + scoring |

---

## 🗺️ Roadmap

- ✅ **mvp1** — minimal CLI agent + 4 skills + JSONL traces
- ✅ **mvp2** — Skills Registry + React UI + Standardization + BioBench v1
- ✅ **mvp3** — Multi-step Harness (Planner + AgentAdapter + TaskRunner)
- ✅ **mvp3.1** — Modular `skills_v2/` directory layout + auto-discovery
- ✅ **mvp3.2** — Chat UI · Email auth · SQLite · in-session context · analytics
- 🔜 **mvp4** — homology search (BLAST) · OAuth · admin dashboard · paper export

---

## 🤝 Contributing

PRs welcome — especially new skills! See [`docs/SKILL_SPEC.md`](./docs/SKILL_SPEC.md) for the contract. A new skill is just a directory with `SKILL.md` + `skill.json` + `handler.py` + `tools.py`.

Bug reports / feature ideas: [open an issue](https://github.com/maris205/open-rosalind/issues).

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 📖 Citation

```bibtex
@software{open_rosalind_2026,
  title  = {Open-Rosalind: A Chat-Based Bio-Agent with Evidence-Grounded Outputs},
  author = {Wang, Liang},
  year   = {2026},
  url    = {https://github.com/maris205/open-rosalind},
  note   = {Tool-first, traceable, model-agnostic. 100% on Mini BioBench v0.}
}
```
