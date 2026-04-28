对，这个策略很稳。

你现在要的不是 SOTA，而是一个 **baseline score**：

```text
Open-Rosalind v0.1 = 基础分数
Open-Rosalind v0.2 = workflow 提升后分数
Open-Rosalind v0.3 = tool / RAG / OmniGene 后分数
```

建议这样做：

## 1. 固定一个 Mini BioBench

先做 25–50 题，分 4 类：

```text
sequence_basic
protein_annotation
literature_search
mutation_effect
```

每题记录：

```json
{
  "id": "seq_001",
  "input": "...",
  "expected_skill": "sequence_basic_analysis",
  "expected_keywords": ["protein", "length", "333"],
  "must_have_evidence": true,
  "must_have_trace": true
}
```

## 2. 指标别复杂

MVP 阶段够用：

```text
Task accuracy
Tool correctness
Evidence rate
Trace completeness
Failure rate
```

最终汇总成：

```text
Open-Rosalind v0.1
Accuracy: 64%
Tool correctness: 88%
Evidence rate: 76%
Trace completeness: 100%
Failure rate: 8%
```

哪怕 accuracy 不高也没关系，**trace completeness / tool correctness 高就是你的特色**。

## 3. 保留版本对比

以后 README 可以放：

```text
Version   Accuracy   Tool Correct   Evidence   Trace
v0.1      64%        88%            76%        100%
v0.2      72%        93%            84%        100%
v0.3      ...
```

这会非常有说服力。

## 4. 加少量 GPT-Rosalind-style tasks

不用全跑，先做 10–20 个类似任务：

```text
literature retrieval
database lookup
sequence manipulation
simple protocol reasoning
```

目的不是证明超过谁，而是证明：

> Open-Rosalind already has measurable capability, and improves over versions.

一句话：**先把分数体系立起来，哪怕初始分不高，也比没有 benchmark 强很多。**
