对，**MVP1 先做 Web 服务更合理**，最快验证用户需求。

建议 MVP1 改成：

```text
MVP1 = Hosted Web Demo + 3 个 Bio Skills + Trace + Demo Pipeline
```

先不做：

```text
Docker 本地部署
离线数据库
本地 BLAST
复杂权限系统
```

## MVP1 Web 版架构

```text
Frontend
- Next.js / React
- 输入框 + Analyze 按钮 + Result / Evidence / Trace

Backend
- FastAPI
- /api/analyze
- rule-based router
- skill execution
- trace logger

Model
- 先接 Gemma 4 Instruct API / vLLM 服务 / 第三方推理端点
- 后续替换 OmniGene

Skills
- sequence_basic_analysis
- uniprot_lookup
- literature_search
```

## 用户流程

```text
用户打开网页
→ 粘贴蛋白/DNA序列或输入问题
→ 点击 Analyze
→ 返回 summary + evidence + trace
```

## MVP1 最小完成标准

```text
用户无需安装任何东西
打开网页就能试
3 个 demo 都能跑
每次结果都有 trace
```

这样传播也更快：你可以直接录 YouTube/B站 demo，GitHub 放在线体验链接。

本地化部署放到 MVP2：

```text
MVP2 = Docker + local UI + optional local model
```

一句话：**MVP1 先做“能让人马上试用的 Web Demo”，MVP2 再做你的核心本地化优势。**
