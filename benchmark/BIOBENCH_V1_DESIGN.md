# BioBench v1 Design

> **Benchmark for bio-agent execution capability, not knowledge recall**

BioBench v1 extends Mini BioBench v0 (32 tasks) with 18 new tasks that test Open-Rosalind's unique capabilities: workflow correctness, multi-step reasoning, fallback strategies, and session memory.

---

## Design Principles (per mvp2-benchmark.md)

1. **Executable tasks** — Every task must trigger at least one skill
2. **Tool-driven** — Tests system execution, not parametric knowledge
3. **Verifiable** — Expected output / keywords / structure, no subjective grading
4. **Small but broad** — 50 tasks total, covering 6 categories

---

## Task Categories

| Category | v0 | v1 (new) | Total | Focus |
|---|---|---|---|---|
| **sequence_basic** | 8 | 2 | 10 | DNA/protein classification, GC%, translation, RC |
| **protein_annotation** | 6 | 3 | 9 | UniProt lookup, homology search |
| **literature_search** | 6 | 2 | 8 | PubMed retrieval, query cleaning |
| **mutation_effect** | 6 | 2 | 8 | WT vs MT diff, HGVS parsing |
| **protocol_reasoning** | 6 | 3 | 9 | Mixed English + sequence/ID |
| **workflow** (new) | 0 | 6 | 6 | Multi-step, fallback, follow-up |

---

## New Task Types (v1)

### 1. Workflow Verification (6 tasks)

**Goal**: Test whether the agent follows the correct execution path, not just the final answer.

**New field**: `expected_workflow: [skill1, skill2, ...]`

**Examples**:
- `wf-01`: "Analyze this protein sequence and find similar proteins in UniProt"
  - Expected workflow: `sequence_basic_analysis` → `uniprot.search` (via probe)
  - Verifies: 2-step pipeline is triggered
  
- `wf-02`: "What is P38398 and find papers about it"
  - Expected workflow: `uniprot_lookup` → (manual follow-up) → `literature_search`
  - Verifies: Follow-up capability (requires 2 API calls with `follow_up_session`)

- `wf-03`: Empty query fallback
  - Input: "Find papers about xyznonexistentprotein123"
  - Expected workflow: `literature_search` with fallback (0 hits → retry without year)
  - Verifies: Fallback strategy is triggered, logged in `notes`

- `wf-04`: UniProt token fallback
  - Input: "What is asdfgh nonexistent protein"
  - Expected workflow: `uniprot_lookup` with token retry
  - Verifies: Per-token fallback, `notes` contains "used token ... (fallback)"

- `wf-05`: Sequence probe fallback
  - Input: 25aa protein with no UniProt match
  - Expected workflow: `sequence_basic_analysis` → probe 30aa → 20aa → 15aa
  - Verifies: Probe size reduction, `notes` contains "shorter probe"

- `wf-06`: Multi-step with error recovery
  - Input: Invalid FASTA + valid question
  - Expected workflow: `sequence_basic_analysis` (error) → fallback to `uniprot_lookup`
  - Verifies: Error handling + graceful degradation

---

### 2. Edge Cases (5 tasks)

**Goal**: Test robustness on boundary inputs.

- `edge-01`: Empty sequence → should return error or minimal stats
- `edge-02`: Very long sequence (10k nt) → should not timeout
- `edge-03`: Ambiguous sequence (all N's) → should classify as "unknown"
- `edge-04`: Invalid UniProt accession → should return 0 hits + confidence=0.0
- `edge-05`: PubMed query with special characters → should sanitize + search

---

### 3. Follow-Up Tasks (4 tasks)

**Goal**: Test session memory and context reuse.

- `followup-01`: 
  - Step 1: "P38398"
  - Step 2: "Find papers about this protein" (with `follow_up_session`)
  - Verifies: Summary mentions "BRCA1" even though step 2 didn't name it

- `followup-02`:
  - Step 1: ">seq MVKVGVNGFGRIGRLVTRA"
  - Step 2: "What organism is this from?" (with `follow_up_session`)
  - Verifies: Agent uses UniProt homology hint from step 1

- `followup-03`:
  - Step 1: "WT: MEEPQ... MT: p.R175H"
  - Step 2: "Is this mutation pathogenic?" (with `follow_up_session`)
  - Verifies: Agent references mutation diff from step 1

- `followup-04`:
  - Step 1: "Find papers about CRISPR"
  - Step 2: "Summarize the top result" (with `follow_up_session`)
  - Verifies: Agent extracts PMID from step 1 evidence

---

### 4. Stress Tests (3 tasks)

**Goal**: Test performance under load.

- `stress-01`: Batch query (5 sequences in one FASTA) → should process all
- `stress-02`: Concurrent API calls (simulate via rapid requests) → should not crash
- `stress-03`: Large evidence blob (UniProt entry with 5k aa sequence) → should truncate gracefully

---

## Evaluation Metrics (v1)

### Core Metrics (from v0)
- Task accuracy
- Tool correctness
- Evidence rate
- Trace completeness
- Failure rate

### New Metrics (v1)
- **Workflow correctness**: Fraction of tasks where `actual_workflow == expected_workflow`
- **Fallback trigger rate**: Fraction of fallback tasks where `notes` contains fallback message
- **Follow-up success rate**: Fraction of follow-up tasks where step 2 references step 1 evidence
- **Latency P95**: 95th percentile of `latency_ms` across all tool calls

---

## Data Format (JSONL)

```json
{
  "id": "wf-01",
  "category": "workflow",
  "mode": "auto",
  "input": "Analyze this protein and find similar ones: MVKVGVNGFGRIGRLVTRA",
  "expected_skill": "sequence_basic_analysis",
  "expected_workflow": ["sequence.analyze", "uniprot.search"],
  "expected_keywords": ["protein", "19", "UniProt"],
  "must_have_evidence": true,
  "must_have_trace": true,
  "checks": {
    "evidence_path": "uniprot_hint.hits",
    "min": 1
  }
}
```

**New field**: `expected_workflow` — list of tool names (not skill names) that should appear in `trace_steps`

---

## Comparison: v0 vs v1

| Aspect | v0 (Mini BioBench) | v1 (BioBench) |
|---|---|---|
| Tasks | 32 | 50 |
| Categories | 5 | 6 (+ workflow) |
| Workflow verification | ❌ | ✅ `expected_workflow` |
| Multi-step tasks | ❌ | ✅ Follow-up (4 tasks) |
| Fallback verification | Implicit | ✅ Explicit (3 tasks) |
| Edge cases | Minimal | ✅ 5 tasks |
| Stress tests | ❌ | ✅ 3 tasks |
| Metrics | 5 | 9 (+ 4 new) |

---

## Implementation Plan

1. **Extend `biobench_v0.jsonl` → `biobench_v1.jsonl`** (keep v0 tasks, add 18 new)
2. **Update `run_biobench.py`**:
   - Add `workflow_correctness` metric (compare `trace_steps` tools vs `expected_workflow`)
   - Add `fallback_trigger_rate` (check `notes` for fallback keywords)
   - Add `follow_up_success_rate` (for follow-up tasks, verify context reuse)
   - Add `latency_p95` (compute from `trace_steps[*].latency_ms`)
3. **Add follow-up test mode** to runner (2-step API calls with `follow_up_session`)
4. **Update `BENCHMARK.md`** with v1 results table

---

## Unique Value Proposition

**Traditional benchmarks** (BioQA, PubMedQA, Rosalind):
- Test: "Is the answer correct?"
- Focus: Knowledge recall, reasoning

**BioBench v1**:
- Test: "How did you get the answer?"
- Focus: Tool selection, workflow correctness, fallback strategies, trace completeness

**For paper**: BioBench v1 is the first benchmark designed specifically for **bio-agent execution capability**, not LLM knowledge.

---

## Next Steps

1. Generate `biobench_v1.jsonl` (50 tasks)
2. Extend `run_biobench.py` with new metrics
3. Run v1 on mvp2 → establish baseline
4. Document in `benchmark/BIOBENCH_V1.md`
