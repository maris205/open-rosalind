对，这个方向我支持：**核心原则不变，MVP2 借鉴 Claude Code 类框架的“执行框架 + skills + memory + session”，但产品入口仍然是 Web UI。**

我建议你别直接 fork 一个很重的项目，而是**轻量借鉴/改造**。可以参考三类：

1. **OpenBioMed 的 skillset 思路**
   它明确是 biomedical discovery toolkit，并提供 45 个 skills，覆盖药物发现、蛋白分析、单细胞组学、数据检索等方向。([GitHub][1])

2. **VoltAgent 这类 agent framework**
   它有 tool registry、MCP、模型可替换、durable memory adapter 等设计，适合参考架构，不一定要直接引入。([GitHub][2])

3. **Opcode / OpenClaw 类 Claude Code UI 项目**
   Opcode 提供 GUI、custom agents、session 管理等 Claude Code 风格能力；OpenClaw 也强调 self-hosted、skills、memory 和执行控制。([GitHub][3])

## MVP2 推荐架构

```text
Open-Rosalind v0.2
├── Web UI                    # 主入口
├── Agent Runner              # 类 Claude Code 执行器
├── Bio Skills Registry       # 所有生物工具注册
├── Memory / Session Store    # 会话、历史、偏好、trace
├── LLM Provider              # Gemma 4 / OmniGene / OpenRouter
└── Eval / BioBench           # 自动评测
```

## 保持你的核心原则

```text
1. Web UI 是主入口，不要求用户会 Claude Code / Codex
2. Gemma 4 / OmniGene 是基座，不绑定 Claude
3. Skills 是核心能力，所有科学计算必须走工具
4. Trace 是一等公民
5. Memory 只记任务上下文，不自动记敏感生物数据
6. Agent Runner 最多 3–5 步，MVP2 不做无限循环
```

## Codex 可以直接做的任务

```text
Task 1:
Refactor current tools into a Bio Skills Registry.
Each skill must include:
- name
- description
- input_schema
- output_schema
- handler
- examples
- safety_level

Task 2:
Implement AgentRunner:
- plan
- call_skill
- observe
- summarize
- write_trace
Limit max_steps=3 for MVP2.

Task 3:
Implement SessionMemory:
- session_id
- user_input
- selected_workflow
- skill_outputs
- final_summary
- trace_path
Use SQLite or JSONL first.

Task 4:
Keep Web UI as primary interface:
- input panel
- result panel
- evidence panel
- trace panel
- session history sidebar

Task 5:
Add CLI compatibility:
open-rosalind skills list
open-rosalind skills inspect uniprot_lookup
open-rosalind run "Analyze this protein..."
```

## 最小可用实现

MVP2 不要一上来做复杂 memory，先做：

```text
短期 memory:
- 当前 session 内记住上一步结果
- 支持 follow-up，例如 “再查一下这个蛋白的文献”

长期 memory:
- 暂时只保存 trace/history
- 不自动学习用户私有数据
```

## 最重要的取舍

**不要让 Open-Rosalind 变成“Claude Code 生物插件”。**
它应该是：

> 一个 Claude Code-like 的独立生物科研 agent，基于 Gemma 4 / OmniGene，面向 Web 用户。

这样既能借成熟框架的执行思路，又不会丢掉你自己的产品定位。

[1]: https://github.com/BioFM/OpenBioMed/blob/main/README.md?utm_source=chatgpt.com "OpenBioMed/README.md at main"
[2]: https://github.com/VoltAgent/voltagent?utm_source=chatgpt.com "VoltAgent/voltagent: AI Agent Engineering Platform built on ..."
[3]: https://github.com/winfunc/opcode?utm_source=chatgpt.com "winfunc/opcode: A powerful GUI app and Toolkit for Claude ..."
