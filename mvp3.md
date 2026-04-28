下面是一版 **Open-Rosalind MVP3 设计文档**。定位很清楚：**参考 DeerFlow2 的 Harness 思路，但不采用自由 Agent 路线，严格保留 Open-Rosalind 的四大原则。**

---

# Open-Rosalind MVP3 设计：Lightweight Bio Harness

## 1. MVP3 定位

**MVP3 = 轻量级 Harness + Agent 解耦 + 任务级 Trace。**

不是做更复杂的通用 agent，而是把 MVP2 的单次 Agent 调用升级成可管理的多步任务系统。

```text
MVP2:
User input → Agent → MCP → Skills → Output

MVP3:
User task → Harness → AgentAdapter → Agent → MCP → Skills → Task Trace → Final Report
```

---

## 2. 核心原则不变

MVP3 必须继续遵守：

```text
1. Tool correctness
2. Evidence grounding
3. Trace completeness
4. Workflow stability
```

具体约束：

```text
Harness 不直接调用 tools
Harness 不自由规划无限步骤
Harness 不自动发现工具
Harness 不生成无 evidence 的结论
Harness 不绕过 MCP
```

---

## 3. 参考 DeerFlow2，但只借“骨架”

可以借鉴：

```text
- TaskRunner
- SessionState
- Memory abstraction
- Step execution loop
- Web + CLI 双入口
- Trace / observability
```

不要照搬：

```text
- multi-agent
- 自由规划
- 自动工具发现
- 长期记忆
- sandbox coding
- open-ended super agent
```

你的版本应该是：

```text
DeerFlow-like Harness structure
+
Open-Rosalind bio constraints
```

---

# 4. MVP3 模块结构

```text
open_rosalind/
├── agent/
│   ├── agent.py
│   ├── router.py
│   └── adapter.py          # AgentAdapter
├── harness/
│   ├── task.py             # Task / TaskStep schema
│   ├── runner.py           # TaskRunner
│   ├── planner.py          # constrained planner
│   ├── state.py            # SessionState / TaskState
│   └── report.py           # final report builder
├── skills/
│   ├── registry.py
│   ├── sequence_basic.py
│   ├── uniprot.py
│   ├── literature.py
│   └── mutation.py
├── mcp/
│   ├── protocol.py
│   └── workflows.py
├── trace/
│   ├── store.py
│   └── schema.py
├── benchmark/
└── web/
```

---

# 5. 核心架构

```text
User Task
   ↓
Harness TaskRunner
   ↓
Constrained Planner
   ↓
TaskStep
   ↓
AgentAdapter
   ↓
Open-Rosalind Agent
   ↓
MCP Workflow
   ↓
Skills
   ↓
Evidence + Trace
   ↓
Harness State Update
   ↓
Final Report
```

关键点：

> Harness 只管理“任务”，Agent 负责“执行一步”，Skills 负责“科学计算”。

---

# 6. 核心数据结构

## 6.1 Task

```json
{
  "task_id": "task_20260428_xxxx",
  "user_goal": "Analyze this protein sequence and find related papers.",
  "status": "running",
  "max_steps": 5,
  "created_at": "...",
  "steps": [],
  "final_report": null
}
```

## 6.2 TaskStep

```json
{
  "step_id": "step_001",
  "instruction": "Analyze the protein sequence.",
  "expected_workflow": "protein_annotation",
  "status": "pending",
  "agent_result": null,
  "evidence": [],
  "trace": []
}
```

## 6.3 TaskState

```json
{
  "task_id": "...",
  "current_step": 2,
  "known_entities": {
    "protein_sequence": "...",
    "uniprot_accession": "P69905",
    "protein_name": "Hemoglobin subunit alpha"
  },
  "evidence_pool": [],
  "trace_refs": []
}
```

---

# 7. AgentAdapter 设计

AgentAdapter 是 MVP3 最关键的解耦层。

## 作用

```text
Harness 不知道具体 tools
Harness 不知道具体 MCP workflow
Harness 只把子任务交给 Agent
```

## 接口

```python
class AgentAdapter:
    def run_step(self, instruction: str, context: dict) -> dict:
        """
        Calls Open-Rosalind Agent once.
        Returns structured result:
        - summary
        - evidence
        - trace
        - confidence
        - extracted_entities
        """
```

## 返回格式

```json
{
  "summary": "...",
  "evidence": [...],
  "trace": [...],
  "confidence": 0.82,
  "extracted_entities": {
    "uniprot_accession": "P69905"
  }
}
```

---

# 8. Constrained Planner 设计

MVP3 的 planner 不做自由规划，只做模板化规划。

## 支持 3 类长任务

### 1. Protein Research Task

```text
Input protein sequence
→ sequence analysis
→ protein annotation
→ literature search
→ final report
```

### 2. Literature Review Task

```text
Input biological topic
→ PubMed search
→ evidence aggregation
→ final summary
```

### 3. Mutation Assessment Task

```text
Input WT + mutation
→ mutation diff
→ annotation lookup
→ literature search
→ final report
```

## Planner 输出

```json
{
  "plan": [
    {
      "step": 1,
      "instruction": "Analyze the provided protein sequence.",
      "expected_workflow": "sequence_basic_analysis"
    },
    {
      "step": 2,
      "instruction": "Search protein annotation using UniProt.",
      "expected_workflow": "protein_annotation"
    },
    {
      "step": 3,
      "instruction": "Find related literature for the identified protein.",
      "expected_workflow": "literature_search"
    }
  ]
}
```

限制：

```text
max_steps = 3–5
planner 只能从 predefined templates 里选
不能自由生成无限任务
```

---

# 9. TaskRunner 执行逻辑

```python
class TaskRunner:
    def run(self, task: Task):
        plan = planner.create_plan(task.user_goal)

        for step in plan.steps[:task.max_steps]:
            result = agent_adapter.run_step(
                instruction=step.instruction,
                context=task.state
            )

            task.state.update(result.extracted_entities)
            task.evidence_pool.extend(result.evidence)
            task.trace_refs.extend(result.trace)

            if result.status == "failed":
                task.add_warning(step, result.error)
                continue

        task.final_report = report_builder.build(task)
        task.status = "completed"
        return task
```

原则：

```text
失败不中断整个任务
每一步必须有 trace
每一步必须记录 evidence
最终报告只能基于 evidence_pool
```

---

# 10. Memory 设计：只做轻量 Session Memory

MVP3 不做长期记忆。

## 只记录

```text
- 当前 task state
- 已识别 entities
- 已调用 steps
- evidence pool
- trace refs
```

## 不记录

```text
- 用户长期偏好
- 私有生物数据持久化学习
- 自动学习用户数据
```

原因：

> Bio/Med 场景里，memory 必须谨慎，默认不自动学习私有数据。

---

# 11. Trace 升级：从 Agent Trace 到 Task Trace

MVP2 trace 是单次执行。

MVP3 增加任务级 trace。

```json
{
  "task_id": "...",
  "task_goal": "...",
  "steps": [
    {
      "step_id": "step_001",
      "instruction": "...",
      "agent_trace": [...],
      "status": "success",
      "latency_ms": 1200
    }
  ],
  "final_report": "...",
  "reproducibility": {
    "all_steps_traced": true,
    "all_outputs_grounded": true
  }
}
```

---

# 12. Web UI 改进

MVP3 Web UI 增加：

```text
Task Mode
- Single Analysis
- Multi-step Task
```

## 页面结构

```text
Input
↓
Task Plan
↓
Step Results
↓
Final Report
↓
Evidence
↓
Trace
```

建议默认折叠：

```text
Trace 默认折叠
Evidence 默认展开
Task Plan 默认展示
```

---

# 13. CLI 接口

```bash
open-rosalind task run "Analyze this protein and find related papers"

open-rosalind task status <task_id>

open-rosalind task trace <task_id>

open-rosalind task report <task_id>
```

---

# 14. BioBench v0.3 扩展

MVP3 新增 Harness 任务评测。

## 新任务类型

```text
harness_protein_research
harness_literature_review
harness_mutation_assessment
```

## 新指标

```text
Task completion rate
Workflow success rate
Step trace completeness
Evidence aggregation rate
Final report grounding
```

继续保留：

```text
Accuracy
Tool correctness
Evidence rate
Trace completeness
Failure rate
```

---

# 15. MVP3 不做什么

明确不做：

```text
Local RAG
Local BLAST DB
Local OmniGene serving
multi-agent collaboration
auto tool discovery
long-term memory
unbounded planning
```

这些放后续版本。

---

# 16. Codex 任务拆分

可以直接丢给 Codex：

```text
Task 1:
Add harness module with Task, TaskStep, TaskState schemas.

Task 2:
Implement AgentAdapter that calls the existing Open-Rosalind Agent once per step.

Task 3:
Implement ConstrainedPlanner with three predefined templates:
- protein_research
- literature_review
- mutation_assessment

Task 4:
Implement TaskRunner:
- max_steps=5
- execute steps sequentially
- update task state
- aggregate evidence
- aggregate traces
- build final report

Task 5:
Add task-level trace schema and JSONL persistence.

Task 6:
Add Web UI Task Mode:
- show plan
- show step status
- show final report
- show evidence and trace

Task 7:
Add CLI commands:
- task run
- task status
- task trace
- task report

Task 8:
Extend BioBench with 10 harness tasks and report:
- task completion
- workflow success
- trace completeness
- grounding rate
```

---

# 17. MVP3 完成标准

```text
1. Harness 与 Agent 解耦
2. 支持 3 类多步任务
3. 每个 task 有 plan、steps、final report
4. 每一步调用 Agent，而不是直接调用 tools
5. 全流程有 task-level trace
6. final report 只基于 evidence_pool
7. BioBench v0.3 能评测 harness tasks
```

---

# 18. 最终定位

MVP3 完成后，Open-Rosalind 就不是单纯的 Bio-Agent，而是：

> **A lightweight, reproducible bio-agent harness built on standardized skills, MCP workflows, and evidence-grounded execution.**

一句话总结：

**参考 DeerFlow2 的工程骨架，但保持 Open-Rosalind 的科学约束。任务可以变长，原则不能变。**
