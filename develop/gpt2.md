下面是一份**可以直接开工用的 MVP1 设计文档（Web 版）**，已经把你前面讨论的关键原则、架构、skills 和 demo 都整合进来。目标是：**3–5 天做出一个“能用、能演示、能拉用户”的 Open-Rosalind v0.1**。

---

# 🧬 Open-Rosalind MVP1 设计文档（v0.1）

## 0. 目标与范围

### 🎯 目标

* 提供一个**在线 Web 服务**，用户无需安装即可使用
* 支持：

  * 序列分析（基础）
  * 蛋白注释（UniProt）
  * 简单文献检索（RAG stub）
* 输出：

  * **Summary（结论）**
  * **Evidence（证据）**
  * **Trace（可复现步骤）**

### 🚫 不在 MVP1 范围

* 本地部署（Docker）👉 MVP2
* 本地 BLAST 数据库 👉 MVP2
* 复杂 agent 规划 👉 MVP2
* 大规模向量库 👉 MVP2

---

# 🧠 1. 最关键设计原则（必须遵守）

## ❗P1：LLM 只负责“想”，不负责“算”

* 所有科学计算必须通过 tools
* LLM 只做：

  * 分类任务
  * 解释结果
  * 生成总结

---

## ❗P2：Tool-first，而不是 LLM-first

* 结果来自工具，而不是模型“猜”
* LLM 只是 orchestrator

---

## ❗P3：Trace 是一等公民（核心卖点）

每次请求必须输出：

```json
{
  "trace": [
    {"skill": "...", "input": {...}, "output": {...}}
  ]
}
```

---

## ❗P4：单请求完成（MVP1）

```text
1 request → 1 pipeline → 1 response
```

避免复杂 agent loop

---

## ❗P5：5 秒内给结果（体验优先）

* 避免多次 LLM 调用
* 避免复杂外部依赖

---

## ❗P6：LLM provider 可替换

必须支持未来切换：

* OpenRouter（现在）
* 本地 Gemma / OmniGene（未来）

---

# 🏗️ 2. 系统架构（MVP1）

```text
Frontend (Web)
    ↓
FastAPI Backend
    ↓
Router (rule-based)
    ↓
Skills (BioPython / UniProt / RAG)
    ↓
LLM (Gemma 4 via OpenRouter)
    ↓
Trace Logger
    ↓
Response
```

---

## 🧩 分层说明

### 🧠 LLM Layer

* Gemma 4 Instruct（OpenRouter）
* 负责：

  * task classification
  * summary generation

---

### ⚙️ Tool Layer（核心能力）

* BioPython
* UniProt API
* 简单文献检索

---

### 🔁 Workflow Layer（MVP1 简化版）

* rule-based routing
* 固定 pipeline

---

### 🧪 Eval / Trace Layer

* JSON trace
* request logging

---

# 🗂️ 3. Repo 结构

```text
open-rosalind/
├── backend/
│   ├── app.py
│   ├── router.py
│   ├── llm/
│   │   └── provider.py
│   ├── skills/
│   │   ├── sequence_basic.py
│   │   ├── uniprot.py
│   │   ├── literature.py
│   │   └── schema.py
│   ├── traces/
│   │   └── logger.py
│   └── tests/
├── frontend/
│   └── simple-ui/
├── examples/
├── README.md
```

---

# ⚙️ 4. MVP1 必做 3 个 Skills

---

## 🧬 Skill 1：sequence_basic_analysis

### 功能

* 检测 DNA / protein
* 长度
* GC content（DNA）
* 翻译（DNA→protein）
* reverse complement

---

### 输入

```json
{
  "sequence": "ATGCGT..."
}
```

---

### 输出

```json
{
  "type": "DNA",
  "length": 1200,
  "gc_content": 0.52,
  "translated": "MRT..."
}
```

---

---

## 🧬 Skill 2：uniprot_lookup

### 功能

* 查询蛋白功能信息

---

### 输入

```json
{
  "query": "P69905"
}
```

---

### 输出

```json
{
  "protein_name": "Hemoglobin subunit alpha",
  "organism": "Homo sapiens",
  "function": "...",
  "length": 141
}
```

---

---

## 📚 Skill 3：literature_search_stub（MVP版）

### 功能

* 返回简单文献摘要（先 mock 或轻量实现）

---

### 输入

```json
{
  "query": "BRCA1 function"
}
```

---

### 输出

```json
{
  "summary": "...",
  "sources": ["PMID:xxxx"]
}
```

---

# 🧠 5. Router（MVP1 规则版）

```text
if input looks like FASTA / sequence:
    → sequence pipeline

elif looks like UniProt ID:
    → uniprot_lookup

else:
    → literature_search
```

---

# 📡 6. API 设计

## POST /api/analyze

### Request

```json
{
  "input": "...",
  "mode": "auto"
}
```

---

### Response

```json
{
  "summary": "...",
  "evidence": [...],
  "trace": [
    {
      "skill": "sequence_basic_analysis",
      "input": {...},
      "output": {...}
    }
  ]
}
```

---

# 🎬 7. 三个 Demo（必须实现）

---

## 🧬 Demo 1：蛋白分析（主打）

### 输入

蛋白序列

### 流程

```text
sequence → basic_analysis → uniprot → summary
```

---

### 输出

* 功能预测
* 同源提示
* trace

---

---

## 🧪 Demo 2：突变分析（简化版）

### 输入

```text
Original + Mutation
```

---

### 流程

```text
sequence analysis → simple rule → summary
```

---

### 输出

* “可能有影响”
* 简单 reasoning
* trace

---

---

## 📚 Demo 3：文献问答

### 输入

```text
"What is BRCA1?"
```

---

### 流程

```text
literature → summary
```

---

### 输出

* 解释
* PMID
* trace

---

# 🎨 8. UI（极简版）

```text
[ 输入框 ]

Paste sequence or ask a biology question

[ Analyze 按钮 ]

----------------------

Result
Evidence
Trace（展开）
```

---

# 🚀 9. 开发顺序（配合 Codex）

```text
1. FastAPI skeleton
2. /api/analyze + router
3. sequence skill
4. uniprot skill
5. trace logger
6. minimal UI
7. demo script
```

---

# ✅ 10. MVP1 完成标准

```text
打开网页
→ 粘贴序列
→ 点击 Analyze
→ 5 秒内得到结果
→ 包含 trace
```

---

# 🧠 最后一条（最重要）

👉 **MVP1 不是证明你模型多强，而是证明：**

> 一个非AI专家也能用 AI 完成生物分析

---

# 😄 一句话总结

👉 **MVP1 = 一个能跑的“生物分析助手”，而不是一个完美的 Rosalind。**

---

如果你下一步要继续，我可以帮你：

* 👉 直接生成 FastAPI + skills 初始代码（可跑）
* 👉 或写一版 README（开源爆款风格）

你现在已经可以开干了 🚀
