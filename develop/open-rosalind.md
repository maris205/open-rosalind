# Open-Rosalind: Local-First 生命科学研究助手

> Open-Rosalind 是一个开源的、本地优先的、工具驱动的生命科学研究 agent。
> 模型层由 OmniGene 系列基座模型支撑（默认 OmniGene-4），但 **agent 与模型解耦**，可换接 Gemma-4 Instruct、Qwen-3、GPT API 等任意 LLM。

---

## 1. 定位与角色分工

Open-Rosalind 是 OpenAI GPT-Rosalind 的**开源、可私有化部署、本地优先**的对应物。

整体架构按"模型层 / 系统层"分离：

| 层 | 名字 | 角色 | 说明 |
|----|------|------|------|
| Model | **OmniGene-4** | "聪明" | 生物基座模型（MoE + 词表扩容 + CPT + Bio-SFT） |
| System | **Open-Rosalind** | "有用" | Agent + Tools + Skills + Workflows |

设计原则：
- **模型层负责：** 序列理解、结构推理、生物知识问答、跨模态对齐
- **系统层负责：** 工具调用、数据库检索、代码执行、多步工作流、可复现性
- **解耦：** Open-Rosalind 是"模型无关"的，可以挂任意 LLM
- **本地优先：** 默认走本地模型，可选挂在线 API

一句话定位：

> **OmniGene-4** is a biology-specialized foundation model.
> **Open-Rosalind** is a local, tool-driven bioinformatics agent built on top of OmniGene-4 (or any compatible LLM).

---

## 2. 为什么做这个

巨头不做：
- OpenAI 的 GPT-Rosalind 是闭源 API，药企/药厂不敢把私有数据传上去
- Google/Meta 都在卷 coding/office 等大市场，生物市场太小没人盯
- 现有开源生物 LLM（BioMedGPT 系列、ESM 等）**都没有 agent / tool / workflow** 层

我们的差异化：
- **本地可部署**（Q4_K_M GGUF + 单卡 4090）
- **数据不出内网**（药企刚需）
- **MoE 基座 + 3Di/DSSP 结构 token**（OmniGene-4 独家）
- **开源 + 可商业化**

参考实现：
- [OpenAI life-science-research plugin](https://github.com/openai/plugins/tree/main/plugins/life-science-research)
- BixBench / LABBench2 评测体系

---

## 3. 评测目标

Agent 评测和模型评测完全不同：模型只看准确率，agent 看**端到端能不能把活干完**。

直接对标行业标准：

| Benchmark | 评测内容 | 当前对照 |
|-----------|---------|---------|
| **BixBench (full)** | 多步生物信息分析（差异表达、代码执行、文献串联） | Gemini 3.1 Pro 0.55 / OmniGene-4 v1 知识子集 0.639 / Rosalind 0.751 |
| **LABBench2** | 生物科研工作流任务 (~1900 条) | Rosalind 已公布最高分 |
| (扩展) **OmniGene-Bench** | 我们自己的多模态序列+知识评测 | 论文用 |

Open-Rosalind 的目标就是把 BixBench 完整版分数追到 Rosalind 0.751 这一档。

---

## 4. 系统架构（v0）

```
┌──────────────────────────────────────────────────┐
│                Open-Rosalind                     │
│                                                  │
│   ┌──────────┐    ┌──────────────┐               │
│   │   CLI    │    │   Web UI     │  (后续)        │
│   └────┬─────┘    └──────┬───────┘               │
│        │                 │                       │
│        ▼                 ▼                       │
│   ┌──────────────────────────────────┐           │
│   │       Orchestrator / Planner     │           │
│   │  - 任务分解                      │           │
│   │  - 工具选择                      │           │
│   │  - 多步推理                      │           │
│   │  - trace 记录 / 可复现           │           │
│   └────┬───────────────────┬─────────┘           │
│        │                   │                     │
│        ▼                   ▼                     │
│   ┌────────────┐    ┌──────────────────────┐     │
│   │   Skills   │    │       Tools          │     │
│   │ (生信任务) │    │ (DB / 算法 / 代码)   │     │
│   └────────────┘    └──────────────────────┘     │
│        │                   │                     │
│        ▼                   ▼                     │
│   ┌──────────────────────────────────┐           │
│   │     Model Backend (LLM)          │           │
│   │  - OmniGene-4 (default, local)   │           │
│   │  - Gemma-4 Instruct (fallback)   │           │
│   │  - 任意 OpenAI 兼容 API          │           │
│   └──────────────────────────────────┘           │
└──────────────────────────────────────────────────┘
```

关键模块：

### Orchestrator
- function calling / MCP 风格的工具路由
- 多步任务规划（Plan → Act → Observe → Reflect）
- 全程 trace（输入、输出、调用、结果都落盘，方便复现）

### Tools（最小可用集，先做这些）
- **UniProt**：蛋白序列、功能、定位、家族查询
- **PDB**：结构条目元信息
- **Foldseek / 3Di**：结构相似度检索
- **BLAST**：序列同源搜索
- **PubMed / PMC**：文献检索（可调本地 S2ORC 子集）
- **AlphaFold DB**：预测结构查询
- **Code executor**：本地 sandbox 运行 R / Python（DESeq2 / clusterProfiler / pandas / biopython）
- **File / Table tools**：处理用户上传的 fasta / csv / h5ad

### Skills（典型工作流）
- **同源搜索与解读**：序列 → BLAST/Foldseek → 拉相关文献 → 给结论
- **突变效应分析**：序列+突变 → 结构相似度 → 文献搜索 → 解释影响
- **RNA-seq 差异表达**：count matrix → DESeq2 → enrichGO → 报告
- **靶点候选筛选**：基因列表 → 表达/突变/通路 → 排序
- **结构语义解释**：3Di / DSSP → 文字结构描述

### Model Backend
- 默认指向我们的 OmniGene-4 v2（vLLM 或 llama.cpp 部署）
- 通过简单 adapter 切换到 Gemma-4 Instruct / GPT API / Qwen API
- agent 不依赖具体模型权重，只依赖一个 chat completions 接口

---

## 5. 目录结构（建议）

放在主项目目录下：

```
/root/autodl-tmp/dnagpt/open-rosalind/
├── README.md
├── pyproject.toml
├── open_rosalind/
│   ├── __init__.py
│   ├── orchestrator/        # 任务规划、工具路由、trace
│   ├── tools/               # 各种工具实现 (uniprot, blast, pdb, foldseek, ...)
│   ├── skills/              # 典型生信工作流
│   ├── backends/            # 模型后端: omnigene / gemma / openai_compat
│   ├── runtime/             # sandbox 代码执行
│   └── cli.py               # 命令行入口
├── prompts/                 # system prompt / planner prompt
├── configs/                 # 工具/模型/skills 配置
├── tests/
└── examples/                # 端到端示例任务
```

---

## 6. 路线图（按周排期，粗略）

### v0.1（雏形，目标 1-2 周）
- 跑通最小闭环：CLI → 模型后端 → 一个工具 → 输出
- 接 1 个工具：UniProt
- 接 1 个 skill：蛋白质功能问答
- 接 1 个后端：Gemma-4 Instruct 或 OpenAI 兼容 API（先不强求 OmniGene-4）

### v0.2（核心工具集，目标 2-3 周）
- 工具：UniProt + PDB + BLAST + PubMed + Foldseek
- skill：同源搜索、突变效应解释
- 加入 trace 系统，所有调用可复现
- 接 OmniGene-4 v2 backend（vLLM 部署）

### v0.3（评测对标，目标 3-4 周）
- 接入 **BixBench 完整版** 评测脚本
- 接入 **LABBench2** 评测脚本
- 加 **code executor**（Python sandbox + DESeq2 + clusterProfiler）
- 目标：BixBench 跑出第一组数

### v0.4（产品化）
- Web UI（chat + trace 可视化 + 文件上传）
- Docker 镜像 + 单机部署文档
- 私有化部署示例（药企内网）

---

## 7. 开发约定

### 模型无关
- 所有调用 LLM 的地方走统一接口 `chat(messages, tools=...)`，不能直接绑定 OmniGene-4
- 切换 backend 只改配置，不改业务代码

### Trace-first
- 每一步 (planner thought, tool call, tool result, model output) 全部写入 jsonl trace
- 复现一个任务 = 重放 trace
- 这是后期对标 BixBench 复现性要求的关键

### 工具规范
所有 tool 统一 schema：

```python
class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict   # JSON Schema
    output_schema: dict
    handler: Callable    # 同步/异步实现
```

### 安全
- 默认所有代码执行在 sandbox（资源限额、网络隔离可选）
- 默认禁外网，只放白名单数据库 API

---

## 8. 与 OmniGene-4 训练分工

| 项目 | 负责 |
|------|------|
| OmniGene-4 v2 训练 | 在另一个 session / GPU 节点上训练（CPT → SFT → eval） |
| Open-Rosalind | 在 CPU/小 GPU 机器上即可开发，不依赖训练完成 |

也就是说：
- **Open-Rosalind 可以现在立刻开发**，先用 Gemma-4 Instruct 或 OpenAI 兼容 API 顶上
- 等 OmniGene-4 v2 训完，**直接换 backend** 就行，不需要重写 agent

---

## 9. 第一步要做的事

1. 在 `/root/autodl-tmp/dnagpt/open-rosalind/` 下建项目骨架
2. 选 backend：先用现成的 Gemma-4 Instruct 或 DeepSeek/Qwen API
3. 实现最小闭环：
   - `cli.py` 接收一个生物问题
   - `orchestrator` 调 LLM
   - LLM 决定要不要调 `uniprot.search`
   - tool 返回结果，LLM 总结
   - 输出答案 + trace
4. 在 `examples/` 下放 1-2 个能跑的脚本

只要这一步通了，后面就是不断加 tool / skill / backend 的事，框架不用大改。

---

## 10. 一句话总结

> Open-Rosalind = 开源版 GPT-Rosalind + 可私有化部署 + 模型可换 + 默认绑 OmniGene-4 基座。
> OmniGene 负责"聪明"，Open-Rosalind 负责"有用"。
