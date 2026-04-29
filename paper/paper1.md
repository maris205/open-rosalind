哈哈，可以开写了。按我们前面定的路线，论文主线应该是：

> **不是提出一个更强模型，而是提出一套可复现 Bio-Agent 标准，并用 Open-Rosalind 作为参考实现验证。**

下面给你一版可直接作为论文初稿骨架的 **标题 + 摘要 + 贡献 + 章节结构**。

---

# Title

**Open-Rosalind: A Reproducible Bio-Agent Framework with Standardized Skills, Execution Protocols, and Traceable Workflows**

备选更偏学术一点：

**Towards Reproducible Bio-Agent Systems: Standardized Skills, Execution Protocols, and Evidence-Grounded Workflows**

备选更偏产品/系统一点：

**Open-Rosalind: A Tool-Driven Bioinformatics Agent for Evidence-Grounded and Reproducible Scientific Workflows**

我最推荐第一版。

---

# Abstract

Recent advances in large language models have enabled the development of autonomous agents for scientific research. However, in biomedical and life-science domains, reliability, evidence grounding, and reproducibility are critical requirements that are not sufficiently addressed by existing general-purpose agent frameworks. Current agents often rely on unconstrained reasoning, loosely defined tool interfaces, and incomplete execution traces, making their outputs difficult to verify or reproduce in scientific workflows.

In this work, we propose **Open-Rosalind**, a reproducible bio-agent framework designed around standardized skills, structured execution protocols, and traceable workflows. Instead of treating the language model as the primary source of scientific knowledge, Open-Rosalind adopts a tool-first design in which biological analyses are performed through explicit skills such as sequence analysis, protein annotation, literature retrieval, and mutation assessment. We introduce three core components: a unified **Bio-Skill Schema** for defining tool interfaces, a constrained **Multi-step Control Protocol** for workflow execution, and a reproducibility-oriented **Trace Format** that records all intermediate steps, tool calls, evidence, and outputs.

We implement Open-Rosalind as a web-based bioinformatics agent powered by a general-purpose language model and a modular biological skill registry. The system supports both single-step analysis and lightweight harness-style multi-step tasks, while enforcing evidence-grounded summaries and complete execution traces. To evaluate the framework, we introduce **Open-Rosalind BioBench**, a lightweight benchmark that measures not only task accuracy but also tool correctness, evidence grounding, workflow success, and trace completeness.

Initial experiments demonstrate that Open-Rosalind achieves strong performance on structured bio-agent tasks while maintaining complete evidence and trace coverage. More importantly, our results show that standardization and workflow constraints are essential for building trustworthy biomedical agents. Open-Rosalind provides a reference implementation for reproducible, tool-driven bio-agent systems and highlights a practical path toward reliable AI-assisted life-science research.

---

# Contributions

**We make the following contributions:**

1. **A standardized framework for bio-agent systems.**
   We propose a principled design for biomedical agents based on four core requirements: tool correctness, evidence grounding, trace completeness, and workflow stability.

2. **A unified Bio-Skill Schema.**
   We define a structured interface for biological tools, including input/output schemas, categories, determinism, safety levels, examples, and versioning, enabling skills to be reused, tested, and composed across workflows.

3. **A constrained execution protocol for bio-agent workflows.**
   We introduce a Multi-step Control Protocol that formalizes how tasks are planned, executed, observed, and summarized, preventing unconstrained agent behavior while supporting both single-step and lightweight multi-step tasks.

4. **A reproducibility-oriented trace format.**
   We design a trace structure that records tool calls, inputs, outputs, evidence, latency, status, and execution metadata, allowing results to be inspected, replayed, and audited.

5. **Open-Rosalind as a reference implementation.**
   We implement the proposed framework in Open-Rosalind, a web-based bioinformatics agent that performs sequence analysis, protein annotation, literature retrieval, mutation assessment, and lightweight multi-step research workflows.

6. **Open-Rosalind BioBench.**
   We introduce a lightweight benchmark for bio-agent systems that evaluates task accuracy, tool correctness, evidence grounding, trace completeness, workflow success, and failure rate.

---

# 论文结构建议

## 1. Introduction

核心要讲：

* LLM agent 正在进入科研场景。
* 生物/医学领域和通用 agent 不一样，因为它需要证据、流程、复现。
* 通用 agent 太自由，缺少标准化 tool schema、workflow protocol、trace。
* Open-Rosalind 的目标不是最强模型，而是可信、可复现、可验证的 bio-agent framework。

可以用这句话作为主旨：

> In biomedical AI, the question is not only whether an agent can produce an answer, but whether the answer can be verified, reproduced, and trusted.

---

## 2. Design Principles

写四条核心原则：

### 2.1 Tool-first execution

科学事实和计算结果必须来自工具，而不是模型生成。

### 2.2 Evidence-grounded outputs

每个结论必须绑定证据来源，如 UniProt、PubMed、sequence statistics、mutation diff。

### 2.3 Trace completeness

每一步 tool call、输入、输出、状态都必须记录。

### 2.4 Workflow-constrained execution

任务必须在受控 workflow 中执行，而不是自由 agent loop。

---

## 3. Framework

这一节是论文核心。

### 3.1 Bio-Skill Schema

定义 skill 的标准结构：

```json
{
  "name": "uniprot_lookup",
  "description": "Retrieve protein annotation from UniProt.",
  "input_schema": {},
  "output_schema": {},
  "category": "protein_annotation",
  "deterministic": true,
  "requires_network": true,
  "safety_level": "low",
  "version": "v1"
}
```

### 3.2 Multi-step Control Protocol

描述：

```text
plan → execute → observe → summarize
```

但强调是 constrained planning，不是自由 planning。

### 3.3 Trace Format

定义 trace：

```json
{
  "step": 1,
  "skill": "uniprot_lookup",
  "input": {},
  "output": {},
  "status": "success",
  "latency_ms": 1205,
  "evidence_refs": []
}
```

### 3.4 Lightweight Harness

MVP3 的重点：

```text
task → plan → agent step → state update → final report
```

强调 harness 调用 agent，agent 调用 MCP + skills，harness 不绕过工具。

---

## 4. Open-Rosalind System

描述具体实现：

* Web chat interface
* Skill registry
* Agent runner
* Harness runner
* OpenRouter/Gemma 4 or OmniGene provider
* Trace store
* Session state
* BioBench evaluator

系统图可以这样：

```text
User
 ↓
Web UI
 ↓
Agent / Harness
 ↓
MCP
 ↓
Bio Skills
 ↓
Evidence + Trace
 ↓
Final Answer
```

---

## 5. Open-Rosalind BioBench

评测不要只看 accuracy。

### 任务类型

```text
sequence_basic
protein_annotation
literature_search
mutation_effect
protocol_reasoning
harness_task
```

### 指标

```text
Task accuracy
Tool correctness
Evidence rate
Trace completeness
Workflow success rate
Failure rate
```

重点写：

> BioBench evaluates not only whether the answer is correct, but also whether the system reached the answer through valid tools, evidence, and traceable workflows.

---

## 6. Experiments

先报告 MVP2/MVP3 初始结果即可，不追求 SOTA。

你现在可以放：

```text
Task accuracy: 96.9% / 97.9% 等
Tool correctness: 96.9%
Evidence rate: 100%
Trace completeness: 100%
Failure rate: 0%
```

然后分析唯一失败案例：

> mixed natural language + sequence input caused routing error.

这个非常适合作为 v0.2/v0.3 改进动机。

---

## 7. Discussion

重点讨论：

* 为什么 bio-agent 需要标准。
* 为什么通用 agent 不够。
* 为什么 reproducibility 在 wet-lab 场景尤其重要。
* Open-Rosalind 和 OpenBioMed / Claude-style agents 的差异。
* 当前局限：

  * benchmark 规模小
  * 检索仍依赖外部 API
  * harness 仍是轻量级
  * 没有完整本地 RAG / 本地 BLAST

---

## 8. Conclusion

一句话收束：

> Open-Rosalind demonstrates that reliable biomedical agents require not only capable language models, but also standardized skills, constrained workflows, and reproducible traces.

---

# 论文主线一句话

你后面所有内容都围绕这句展开：

> **Open-Rosalind shifts bio-agent design from free-form reasoning to reproducible workflow execution.**

这个就是你的核心观点。
