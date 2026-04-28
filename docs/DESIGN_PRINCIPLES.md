# Open-Rosalind Design Principles

> **Core philosophy**: Tool-first, evidence-grounded, traceable, workflow-constrained

Open-Rosalind is designed as a **standardized bio-agent framework** that prioritizes reproducibility, extensibility, and scientific rigor over raw capability. These principles guide every architectural decision.

---

## 1. Tool-First Architecture

**Principle**: Every scientific claim must originate from an explicit tool call, not from the LLM's parametric knowledge.

**Implementation**:
- The agent **never** answers from memory alone
- Every query is routed to one or more registered skills
- Skills compose atomic tools (UniProt API, PubMed API, local compute)
- The LLM's role is **synthesis**, not fact generation

**Why**: Prevents hallucination; ensures auditability; enables tool-level caching and optimization.

---

## 2. Evidence-Grounded Outputs

**Principle**: The LLM summary must be strictly grounded in structured evidence returned by tools.

**Implementation**:
- System prompt forbids out-of-evidence claims
- Every factual statement must cite a source: `[UniProt:P38398]`, `[PMID:12345]`, `[tool:sequence.analyze]`
- Evidence is returned as a separate structured field alongside the summary
- If evidence is insufficient, the agent says so explicitly

**Why**: Scientific users need to verify claims; grounding enables trust and reproducibility.

---

## 3. Traceable Execution

**Principle**: Every agent run produces a complete, machine-readable trace that can be replayed or audited.

**Implementation**:
- One JSONL file per session under `traces/`
- Every tool call logs: `{kind: "tool_call", tool, args, timestamp}`
- Every tool result logs: `{kind: "tool_result", tool, status, latency_ms, result}`
- Trace is surfaced in the API response as `trace_steps: [{skill, input, output, latency_ms, status}]`

**Why**: Reproducibility is a first-class requirement in scientific computing; traces enable debugging, auditing, and benchmarking.

---

## 4. Workflow-Constrained Planning

**Principle**: The agent operates within explicit constraints to prevent unbounded exploration.

**Implementation**:
- Single-step execution by default (one skill per query)
- Multi-step planning (AgentRunner) is capped at `max_steps=3`
- No infinite loops; no autonomous tool invention
- Routing is deterministic (rule-based) with LLM fallback only for ambiguous cases

**Why**: Scientific workflows are goal-directed, not exploratory; constraints prevent wasted compute and ensure predictable behavior.

---

## 5. Fail-Safe Pipelines

**Principle**: Tool failures must not crash the agent; fallback strategies are mandatory.

**Implementation**:
- Every tool call is wrapped in error-safe `_run()` that returns `{error: ...}` on failure
- Pipelines detect empty results and retry with relaxed constraints (e.g., shorter probe, broader query)
- Fallback events are logged to trace and surfaced in `notes` field
- The agent always returns a response, even if degraded

**Why**: Real-world APIs are unreliable; scientific users need robustness over perfection.

---

## 6. Structured Skill Interface

**Principle**: All skills conform to a uniform schema for discoverability and composability.

**Implementation**:
- Every skill declares: `name`, `description`, `category`, `input_schema`, `output_schema`, `examples`, `safety_level`, `tools_used`
- Skills are registered in `SKILLS` dict and exposed via `/api/skills`
- CLI: `open-rosalind skills list / inspect <name>`
- Backward-compat: `SKILL_REGISTRY` (name → handler) for existing code

**Why**: Uniform interfaces enable programmatic composition, testing, and extension by third parties.

---

## 7. Confidence Scoring

**Principle**: Every response includes a rule-based confidence score to signal reliability.

**Implementation**:
- Confidence ∈ [0, 1] computed from:
  - Exact accession fetch → 0.95
  - Multiple search hits → 0.7–0.85
  - Fallback retry → 0.5–0.6
  - Empty result → 0.0
- Displayed as a gradient bar in the UI (red → yellow → green)

**Why**: Users need to calibrate trust; confidence scores enable downstream filtering and prioritization.

---

## 8. Session Memory for Follow-Up

**Principle**: Users should be able to reference prior results without re-stating context.

**Implementation**:
- Every session writes events to `sessions/<id>.jsonl`
- AgentRunner loads `last_evidence` from a prior session when `follow_up_session` is provided
- Prior evidence is injected into the LLM prompt as "PREVIOUS SESSION CONTEXT"
- Example: "P38398" → "Find papers about this protein" (no need to repeat "BRCA1")

**Why**: Natural scientific workflows involve iterative refinement; session memory reduces friction.

---

## Non-Goals

What Open-Rosalind intentionally does **not** do:

- ❌ **Autonomous exploration**: No unbounded tool chaining or self-directed research
- ❌ **Parametric answers**: The LLM never answers from training data alone
- ❌ **Black-box reasoning**: Every claim must be traceable to a tool call
- ❌ **Infinite context**: Multi-step planning is capped; sessions are finite
- ❌ **General-purpose chat**: This is a scientific agent, not a conversational assistant

---

## Summary

Open-Rosalind is a **principled bio-agent** that trades raw capability for reproducibility, auditability, and extensibility. These design principles are enforced at the code level (system prompts, error-safe wrappers, trace logging) and documented here for transparency.

**For paper**: These principles constitute a **standardized bio-agent design pattern** that can be adopted by other scientific domains.
