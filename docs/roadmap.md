# Roadmap

## v0.1

- 完成 OpenHands repository customization。
- 创建 `.openhands/AGENTS.md`。
- 创建 8 个基础 Edu Skills。
- 提供默认 prompts、examples 和 docs。
- 提供 Markdown 到 DOCX 的轻量导出脚本。
- 在 README 中说明 Qwen OpenAI-compatible 接入方式。

## v0.2

- 评估 OpenHands / Agent Canvas 实际加载 `.openhands` 和 skills 的效果。
- 增加更多真实论文测试样例。
- 增加 `graphical_abstract` Skill。
- 增加受控文献检索 TODO 设计，但不默认接入真实 PubMed API。
- 优化 DOCX 导出格式和中文字体。

## v0.3

- 评估是否开发独立 Next.js + Tailwind + shadcn/ui 前端。
- 增加 FastAPI wrapper。
- 增加可控文件上传、导出和任务模板。
- 引入更细粒度的安全权限策略。

## Later

- PostgreSQL / Redis / MinIO / Qdrant。
- 本地 Qwen via vLLM、Ollama 或 LMDeploy。
- 多模型 provider 支持。
- 受控引用管理和证据核验工作流。
