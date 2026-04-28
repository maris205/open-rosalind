# Execution Protocol (MCP-Inspired)

> **Structured multi-step workflow protocol for bio-agents**

Open-Rosalind implements a **lightweight execution protocol** inspired by Model Context Protocol (MCP) principles: structured tool interfaces, explicit planning, and reproducible traces.

---

## Protocol Overview

Every agent run follows this lifecycle:

```
User Input → Route → Plan → Execute → Observe → Summarize → Return
```

**Key properties**:
- **Deterministic routing**: Rule-based with LLM fallback
- **Explicit planning**: Skill selection is logged before execution
- **Bounded execution**: Max 1 skill per query (default); max 3 steps (AgentRunner)
- **Complete tracing**: Every tool call is logged with latency + status
- **Evidence-grounded**: LLM summary must cite tool outputs

---

## Phase 1: Routing

**Input**: User query (text)  
**Output**: `Intent(skill, payload)`

**Logic**:
1. **Rule-based detection** (fast path):
   - FASTA header → `sequence_basic_analysis`
   - UniProt accession → `uniprot_lookup`
   - "papers" / "literature" → `literature_search`
   - WT/MT block → `mutation_effect`

2. **LLM-assisted classification** (ambiguous cases):
   - Triggered when: `has_embedded_sequence(text) and looks_like_natural_language(text)`
   - LLM picks one of 4 skills + extracts payload
   - Falls back to rule-based on error

**Trace event**:
```json
{"kind": "router", "path": "rule_based" | "llm_classify_overrode", "skill": "..."}
```

---

## Phase 2: Planning

**Input**: `Intent(skill, payload)`  
**Output**: Execution plan (currently single-step)

**Current implementation** (MVP2):
```json
{
  "plan": [
    {"step": 1, "skill": "uniprot_lookup", "payload": {"query": "P38398"}}
  ]
}
```

**Future** (multi-step):
```json
{
  "plan": [
    {"step": 1, "skill": "sequence_basic_analysis", "payload": {...}},
    {"step": 2, "skill": "uniprot_lookup", "payload": {"query": "<from_step_1>"}},
    {"step": 3, "skill": "literature_search", "payload": {"query": "<from_step_2>"}}
  ],
  "max_steps": 3
}
```

**Trace event**:
```json
{"kind": "plan", "skill": "...", "payload": {...}}
```

---

## Phase 3: Execution

**Input**: Plan  
**Output**: Evidence dict

**Logic**:
1. For each step in plan:
   - Call `skill_handler(payload, trace)`
   - Handler composes atomic tools via `_run(tool_name, trace, **kwargs)`
   - `_run()` logs `tool_call` + `tool_result` with `latency_ms` + `status`
   - Handler returns `{annotation, confidence, notes, ...}`

2. If tool fails:
   - `_run()` returns `{error: ...}` (never raises)
   - Handler detects error, triggers fallback, logs to `notes`

**Trace events** (per tool call):
```json
{"kind": "tool_call", "tool": "uniprot.fetch", "args": {"accession": "P38398"}}
{"kind": "tool_result", "tool": "uniprot.fetch", "status": "success", "latency_ms": 120, "result": {...}}
```

**Structured trace** (API response):
```json
{
  "trace_steps": [
    {
      "skill": "uniprot.fetch",
      "input": {"accession": "P38398"},
      "output": {...},
      "status": "success",
      "latency_ms": 120
    }
  ]
}
```

---

## Phase 4: Observation

**Input**: Evidence dict  
**Output**: Decision (done | continue | retry)

**Current implementation** (single-step):
- Always `done` after one skill execution

**Future** (multi-step):
- Check if evidence is sufficient
- If `confidence < 0.5` and `steps < max_steps` → plan next step
- If `error` and retries available → retry with relaxed constraints
- Otherwise → `done`

---

## Phase 5: Summarization

**Input**: Evidence dict + user question  
**Output**: Natural-language summary

**LLM prompt structure**:
```
SYSTEM: You are Open-Rosalind. Use ONLY facts from EVIDENCE. Cite every claim.

USER:
USER QUESTION: <question>
SKILL: <skill_name>
EVIDENCE (JSON): <evidence>

[If follow-up] PREVIOUS SESSION CONTEXT: <last_evidence>

Write the answer now.
```

**Constraints** (enforced by system prompt):
- Summary must cite sources: `[UniProt:P38398]`, `[PMID:12345]`, `[tool:sequence.analyze]`
- No parametric knowledge allowed
- Must end with `### Evidence` section listing citations

**Trace event**:
```json
{"kind": "model_request", "messages": [...]}
{"kind": "model_response", "content": "..."}
```

---

## Phase 6: Return

**Output schema** (uniform across all skills):
```json
{
  "session_id": "20260428-123456-abc123",
  "skill": "uniprot_lookup",
  "summary": "P38398 is BRCA1 [UniProt:P38398]...",
  "annotation": {"kind": "protein", "accession": "P38398", ...},
  "confidence": 0.95,
  "notes": [],
  "evidence": {"entry": {...}, "search": {...}},
  "trace_path": "traces/20260428-123456-abc123.jsonl",
  "trace": [...],
  "trace_steps": [{"skill": "...", "input": {...}, "output": {...}, "latency_ms": 120, "status": "success"}]
}
```

---

## Session Memory (Follow-Up)

**Mechanism**:
1. Every session writes events to `sessions/<id>.jsonl`:
   ```json
   {"kind": "start", "ts": ..., "user_input": "..."}
   {"kind": "skill_call", "skill": "...", "payload": {...}}
   {"kind": "skill_result", "evidence": {...}, "annotation": {...}, "confidence": ...}
   {"kind": "summary", "text": "..."}
   ```

2. When `follow_up_session` is provided:
   - Load `last_evidence` from that session
   - Inject into LLM prompt as "PREVIOUS SESSION CONTEXT"
   - User can say "Find papers about this protein" without repeating "BRCA1"

**API**:
```bash
POST /api/analyze
{
  "input": "Find papers about this protein",
  "follow_up_session": "20260428-123456-abc123"
}
```

---

## Error Handling

**Tool-level**:
- `_run()` catches all exceptions → returns `{error: ...}`
- Handler detects error → triggers fallback → logs to `notes`
- Agent never crashes on tool failure

**Skill-level**:
- Empty results → fallback strategies (retry with relaxed constraints)
- All fallbacks exhausted → return `confidence=0.0` + explanatory `notes`

**LLM-level**:
- Backend unavailable → return degraded response with raw evidence
- Trace logs `model_error` event

---

## Constraints

**Bounded execution**:
- Default: 1 skill per query
- AgentRunner: max 3 steps
- No infinite loops; no autonomous exploration

**Deterministic routing**:
- Rule-based is preferred (fast, predictable)
- LLM fallback only for ambiguous cases
- Routing decision is always logged

**Evidence-grounded**:
- LLM cannot answer from parametric knowledge
- Every claim must cite a tool output
- System prompt enforces this constraint

---

## Trace Format

**JSONL file** (`traces/<session_id>.jsonl`):
```json
{"ts": 1777295590.0, "kind": "user_input", "question": "P38398", "mode": "auto"}
{"ts": 1777295590.1, "kind": "router", "path": "rule_based", "skill": "uniprot_lookup"}
{"ts": 1777295590.2, "kind": "plan", "skill": "uniprot_lookup", "payload": {"query": "P38398"}}
{"ts": 1777295590.3, "kind": "tool_call", "tool": "uniprot.fetch", "args": {"accession": "P38398"}}
{"ts": 1777295590.5, "kind": "tool_result", "tool": "uniprot.fetch", "status": "success", "latency_ms": 120, "result": {...}}
{"ts": 1777295590.6, "kind": "evidence", "skill": "uniprot_lookup", "evidence": {...}}
{"ts": 1777295590.7, "kind": "model_request", "messages": [...]}
{"ts": 1777295592.0, "kind": "model_response", "content": "..."}
```

**Replay**: Load JSONL → reconstruct execution → verify outputs

---

## Comparison to Standard MCP

| Feature | Standard MCP | Open-Rosalind |
|---|---|---|
| Tool registry | ✅ Server exposes tools | ✅ `SKILLS` dict + `/api/skills` |
| Structured I/O | ✅ JSON Schema | ✅ `input_schema` + `output_schema` |
| Client-server | ✅ Separate processes | ❌ Monolithic (for now) |
| Streaming | ✅ SSE | ❌ Batch only |
| Sampling | ✅ LLM calls tools | ✅ Agent calls skills |
| Prompts | ✅ Server provides | ✅ System prompt + skill descriptions |

**Why not full MCP**:
- MVP2 prioritizes simplicity over protocol compliance
- Monolithic deployment is easier for scientific users
- Future: MCP server mode for integration with Claude Desktop / other clients

---

## Summary

Open-Rosalind's execution protocol is:
- **Structured**: Explicit routing → planning → execution → summarization
- **Traceable**: Every tool call logged with latency + status
- **Bounded**: Max steps enforced; no infinite loops
- **Evidence-grounded**: LLM summary must cite tool outputs
- **MCP-inspired**: Uniform tool interfaces, but not full MCP compliance (yet)

**For paper**: This constitutes a **reproducible bio-agent execution protocol** that balances flexibility with scientific rigor.
