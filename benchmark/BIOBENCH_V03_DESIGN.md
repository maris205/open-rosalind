# BioBench v0.3: Harness Tasks

> **Tests multi-step task execution capability**

BioBench v0.3 extends v1 with 10 harness tasks that require multi-step execution.
These tasks test the Harness's ability to orchestrate Agent calls, propagate context,
aggregate evidence, and generate final reports.

---

## Task Categories

| Category | Tasks | Description |
|---|---|---|
| **harness_protein_research** | 4 | Sequence → annotation → literature |
| **harness_literature_review** | 3 | Topic → PubMed search → aggregation |
| **harness_mutation_assessment** | 3 | Mutation → annotation → literature |

---

## Evaluation Metrics

### Core Metrics (from v0/v1)
- Task accuracy
- Tool correctness
- Evidence rate
- Trace completeness
- Failure rate

### New Harness Metrics
- **Task completion rate**: Fraction of tasks that reach "completed" status
- **Workflow success rate**: Fraction of tasks where all steps succeed
- **Step trace completeness**: Fraction of steps with non-empty trace
- **Evidence aggregation rate**: Fraction of tasks with evidence_pool > 0
- **Final report grounding**: Fraction of reports that cite evidence

---

## Task Format

```json
{
  "id": "harness-protein-01",
  "category": "harness_protein_research",
  "mode": "task",
  "input": "Analyze this protein and find papers: MVKVGVNGFGRIGRLVTRA",
  "max_steps": 3,
  "expected_steps": 3,
  "expected_entities": ["protein_name", "uniprot_accession"],
  "expected_keywords": ["protein", "papers"],
  "must_have_evidence": true,
  "must_have_trace": true,
  "checks": {
    "task_status": "completed",
    "min_steps": 2,
    "evidence_pool_min": 1
  }
}
```

---

## Success Criteria (MVP3)

Per mvp3.md §17:
1. ✅ Harness与Agent解耦
2. ✅ 支持3类多步任务
3. ✅ 每个task有plan、steps、final report
4. ✅ 每一步调用Agent，而不是直接调用tools
5. ✅ 全流程有task-level trace
6. ✅ final report只基于evidence_pool
7. ✅ BioBench v0.3能评测harness tasks

Target scores:
- BioBench v0 (32 tasks): **100%** (no regression)
- BioBench v1 (49 tasks): **≥93.9%** (no regression)
- BioBench v0.3 (10 harness tasks): **≥80%** (new capability)
