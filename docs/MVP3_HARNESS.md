# MVP3: Multi-Step Harness Design

> **Goal**: Extend MVP2's single-step agent with structured multi-step execution for complex tasks

---

## Architecture Comparison

| 维度 | MVP2（当前） | MVP3（未来 Harness） |
|---|---|---|
| **执行模式** | 单步（one query → one skill） | 多步（one query → plan → N steps） |
| **适用场景** | 97.9% 的生物任务 | 复杂推理、多数据源综合 |
| **复杂度** | 低（可控、可预测） | 中等（结构化 planning + execution） |
| **评测** | 精确（deterministic） | 结构化（multi-path, verifiable） |
| **当前状态** | ✅ 已完成 | 🔜 MVP3 |

---

## Design Principles

1. **Harness wraps Agent** — Agent 保持单步不变，Harness 在外层编排
2. **Structured planning** — 不是无限循环，而是有限步骤（max_steps=3-5）
3. **Verifiable workflows** — 每个 plan 可以通过 `expected_workflow` 验证
4. **Error recovery** — 某一步失败 → 重试或跳过，不崩溃
5. **Context propagation** — 前一步的 evidence 传递给后一步

---

## Core Components

### 1. Planner

**Input**: User question  
**Output**: Structured plan (list of steps)

```python
@dataclass
class Step:
    step_id: int
    skill: str
    query: str
    depends_on: list[int]  # step_ids this step depends on

@dataclass
class Plan:
    steps: list[Step]
    max_steps: int = 3
```

**Example**:
```
User: "Analyze this protein sequence, find similar proteins, and get papers about them"

Plan:
  Step 1: skill=sequence_basic_analysis, query="MVKVGVNGFGRIGRLVTRA"
  Step 2: skill=uniprot_lookup, query="Find similar proteins to {step1.annotation.name}", depends_on=[1]
  Step 3: skill=literature_search, query="Papers about {step2.annotation.name}", depends_on=[2]
```

---

### 2. Executor

**Input**: Plan  
**Output**: Aggregated results

```python
class MultiStepHarness:
    def __init__(self, agent: Agent):
        self.agent = agent  # Reuse single-step agent
        self.planner = Planner()
    
    def run(self, question: str, max_steps: int = 3) -> dict:
        # 1. Generate plan
        plan = self.planner.decompose(question, max_steps)
        
        # 2. Execute steps sequentially
        context = {}
        for step in plan.steps:
            # Wait for dependencies
            if not self._dependencies_ready(step, context):
                continue
            
            # Resolve query template with prior results
            query = self._resolve_query(step.query, context)
            
            # Call single-step agent
            result = self.agent.analyze(query)
            context[step.step_id] = result
            
            # Early exit if high confidence
            if result["confidence"] > 0.9 and step.step_id == len(plan.steps):
                break
        
        # 3. Synthesize final answer
        return self._synthesize(context, question)
```

---

### 3. Context Manager

**Role**: Propagate evidence between steps

```python
def _resolve_query(self, template: str, context: dict) -> str:
    """Replace {step1.annotation.name} with actual value from context."""
    for step_id, result in context.items():
        template = template.replace(
            f"{{step{step_id}.annotation.name}}",
            result["annotation"].get("name", "")
        )
    return template
```

---

## Example Workflows

### Workflow 1: Sequence → Annotation → Literature

```
User: "What is this protein and what papers discuss it? MVKVGVNGFGRIGRLVTRA"

Plan:
  Step 1: sequence_basic_analysis("MVKVGVNGFGRIGRLVTRA")
    → annotation.name = "Glyceraldehyde-3-phosphate dehydrogenase"
  
  Step 2: literature_search("Papers about Glyceraldehyde-3-phosphate dehydrogenase")
    → pubmed.hits = [PMID:12345, PMID:67890, ...]

Synthesize:
  "This is a 19aa fragment of GAPDH [UniProt:P04406]. Recent papers include..."
```

### Workflow 2: Mutation → Annotation → Impact Assessment

```
User: "Is p.R175H in TP53 pathogenic?"

Plan:
  Step 1: uniprot_lookup("TP53")
    → annotation.accession = "P04637"
  
  Step 2: mutation_effect("WT: MEEPQ... MT: p.R175H")
    → mutation.severity = "high"
  
  Step 3: literature_search("TP53 R175H pathogenicity")
    → pubmed.hits = [PMID:...]

Synthesize:
  "R175H is a hotspot mutation in TP53 [UniProt:P04637], classified as likely pathogenic..."
```

---

## Error Recovery

**Strategy**: Fail gracefully, don't crash the entire workflow

```python
def run(self, question: str, max_steps: int = 3) -> dict:
    context = {}
    for step in plan.steps:
        try:
            result = self.agent.analyze(query)
            context[step.step_id] = result
        except Exception as e:
            # Log error, mark step as failed
            context[step.step_id] = {"error": str(e), "confidence": 0.0}
            # Continue to next step (if not dependent)
            continue
    
    # Synthesize with partial results
    return self._synthesize(context, question)
```

---

## Evaluation: BioBench v2

**New task type**: Multi-step tasks

```json
{
  "id": "multi-01",
  "category": "multi_step",
  "input": "Analyze this protein and find papers: MVKVGVNGFGRIGRLVTRA",
  "expected_workflow": [
    {"step": 1, "skill": "sequence_basic_analysis"},
    {"step": 2, "skill": "literature_search"}
  ],
  "expected_keywords": ["protein", "papers", "GAPDH"],
  "must_have_evidence": true,
  "must_have_trace": true
}
```

**New metric**: Workflow correctness

```python
def workflow_correctness(actual_steps, expected_workflow) -> float:
    """
    Check if actual execution matches expected workflow.
    Allow partial credit for correct subsequences.
    """
    actual_skills = [s["skill"] for s in actual_steps]
    expected_skills = [w["skill"] for w in expected_workflow]
    
    # Exact match
    if actual_skills == expected_skills:
        return 1.0
    
    # Partial credit: longest common subsequence
    lcs_len = longest_common_subsequence(actual_skills, expected_skills)
    return lcs_len / len(expected_skills)
```

---

## Implementation Plan

### Phase 1: Planner (Week 1)
- [ ] LLM-based planner (prompt engineering)
- [ ] Plan schema (Step, Plan dataclasses)
- [ ] Unit tests (5 example questions → expected plans)

### Phase 2: Executor (Week 2)
- [ ] MultiStepHarness class
- [ ] Context manager (query template resolution)
- [ ] Error recovery (try/except + partial results)
- [ ] Integration tests (end-to-end workflows)

### Phase 3: Evaluation (Week 3)
- [ ] BioBench v2 (10 multi-step tasks)
- [ ] Workflow correctness metric
- [ ] Baseline run (MVP3 vs MVP2 on v2 tasks)

---

## Non-Goals (MVP3)

What we intentionally **don't** do:
- ❌ **Infinite loops** — max_steps is hard-capped
- ❌ **Autonomous exploration** — plan is generated upfront, not dynamically
- ❌ **Tool invention** — only use registered skills
- ❌ **Black-box reasoning** — every step is logged to trace

---

## Success Criteria

MVP3 is successful if:
1. ✅ BioBench v0 (32 tasks): **100%** (no regression)
2. ✅ BioBench v1 (49 tasks): **≥93.9%** (no regression)
3. ✅ BioBench v2 (10 multi-step tasks): **≥80%** (new capability)
4. ✅ Workflow correctness: **≥90%** (structured execution)

---

## Summary

MVP3 extends MVP2 with **structured multi-step execution**:
- Harness wraps Agent (Agent stays single-step)
- Planner generates structured plans (not infinite loops)
- Executor runs N steps with context propagation
- Error recovery ensures graceful degradation
- BioBench v2 validates multi-step capability

**For paper**: MVP3 demonstrates that **structured planning + single-step agents** can handle complex tasks without sacrificing reproducibility.
