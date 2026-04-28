对，这一步就很关键了 👍
而且你的思路是对的：**基于已有 benchmark 思路 + 做一个轻量但“有你特色”的 BioBench**，不要从零造轮子。

我给你一套**可以直接落地的 Open-Rosalind BioBench 设计方案**👇

---

# 🧠 一句话目标

👉 **做一个“小而精”的 benchmark，专门衡量 Bio-Agent（而不是模型）能力**

---

# ⚠️ 先纠正一个关键点

👉 **你不是在做“更强的 benchmark”**

而是在做：

```text
适配 tool + workflow + trace 的 benchmark
```

---

👉 这是和现有 benchmark 最大区别

---

# 🚀 一、总体设计原则（必须遵守）

---

## ✅ 原则 1：任务要“可执行”

不要：

```text
What is p53?
```

要：

```text
Retrieve function of p53 using UniProt
```

---

👉 因为你测的是：

> ❗系统执行能力，而不是知识记忆

---

---

## ✅ 原则 2：必须能触发 tool

每个 task 都要：

```text
至少调用一个 skill
```

---

👉 否则就退化成 GPT benchmark

---

---

## ✅ 原则 3：必须能验证

每个任务要有：

```text
expected output / keyword / structure
```

---

👉 不要做主观题

---

---

## ✅ 原则 4：规模小但覆盖广

👉 不要 1000 题

建议：

```text
25–50 tasks（MVP够用）
```

---

# 🧬 二、BioBench 结构设计（推荐直接用）

---

## 🧩 4 大类任务

---

### 🧬 1️⃣ Sequence Tasks（8–10题）

👉 测基础生物计算能力

```text
- DNA / protein classification
- GC content
- translation
- reverse complement
```

---

👉 来源：

* Rosalind（非常适合）
* 你可以直接改写

---

---

### 🧬 2️⃣ Protein Annotation（6–8题）

👉 测 UniProt / annotation pipeline

```text
- 给 accession → 返回 function
- 给 sequence → 找相似蛋白
```

---

👉 来源：

* UniProt examples
* SwissProt

---

---

### 📚 3️⃣ Literature Tasks（6–8题）

👉 测 PubMed + summary

```text
- find papers on CRISPR
- summarize BRCA1 role
```

---

👉 来源：

* PubMed queries
* BioQA 数据集（可以参考）

---

---

### 🧪 4️⃣ Mutation Tasks（6–8题）

👉 测 reasoning + workflow

```text
- mutation diff
- classify severity（简单规则即可）
```

---

👉 可以自己构造（不用复杂）

---

---

# 📊 三、数据格式（建议直接用 JSONL）

---

```json
{
  "id": "seq_001",
  "category": "sequence",
  "input": "ATGGCC...",
  "expected_skill": "sequence_basic_analysis",
  "expected_keywords": ["protein", "length"],
  "must_have_evidence": true,
  "must_have_trace": true
}
```

---

👉 关键字段：

| 字段                 | 作用                 |
| ------------------ | ------------------ |
| expected_skill     | 测 tool correctness |
| expected_keywords  | 测答案                |
| must_have_evidence | 测 grounding        |
| must_have_trace    | 测 trace            |

---

---

# 📈 四、评测指标（你已经很接近了）

---

## ✅ 核心指标（保持）

```text
Accuracy
Tool correctness
Evidence rate
Trace completeness
Failure rate
```

---

## ➕ MVP2 建议新增

```text
Routing accuracy
Workflow success rate
```

---

---

# 🔥 五、借鉴现有 benchmark（但不要直接用）

---

## 可以参考：

👉 Rosalind（sequence tasks）
👉 BioQA / PubMedQA（literature）
👉 UniProt examples

---

👉 使用方式：

```text
改写成“必须调用工具”的形式
```

---

---

# 🚀 六、一个非常重要的升级（强烈建议）

👉 给每个 task 加：

```text
expected_workflow
```

---

例如：

```json
{
  "expected_workflow": [
    "sequence_basic_analysis",
    "uniprot_lookup"
  ]
}
```

---

👉 这样你可以测：

> ❗是否走对流程（这是你最大优势）

---

---

# 🧠 七、你这个 BioBench 的独特价值

---

## ❗传统 benchmark 测：

```text
answer 对不对
```

---

## ❗你这个测：

```text
怎么得到这个答案
```

---

👉 这是本质区别

---

# 😄 最后一句总结

👉 **你的 BioBench 不是“考知识”，而是“考系统执行能力”。**

---

# 🚀 如果你下一步要做

我可以帮你：

* 👉 直接生成一版 **30题 BioBench v0.1（可用数据）**
* 👉 或帮你写一个 **自动评测脚本（直接跑 API）**

你现在这一步，其实已经在做“论文 evaluation 核心”了 👍
