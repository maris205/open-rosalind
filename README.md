# Open-Rosalind Agent

Open-Rosalind Agent is a traceable biomedical research workbench built around planning, memory, evidence, tool audit, reference verification, and reproducible reports.

Edu remains a separate beginner-facing branch for paper reading and writing scaffolds. This `agent` branch is the research-execution product.

## Positioning

Open-Rosalind Agent helps biomedical researchers and research trainees with:

- task planning with permission levels
- structured project memory
- evidence extraction from uploaded materials
- reference verification and fabricated-citation risk screening
- tool-call audit and reproducibility checks
- traceable research reports
- future RAG and sequence-resource integration

## Important Disclaimer

Open-Rosalind Agent is designed for research planning, evidence organization, tool auditing, and report drafting. It does not guarantee scientific reproducibility, citation accuracy, statistical validity, or clinical correctness. Users must verify original literature, data, tool logs, and references before submission, publication, or research decisions. It does not provide clinical diagnosis or treatment advice.

## File Tree

```text
.
├── .env.example
├── .gitignore
├── .openhands/
│   ├── AGENTS.md
│   ├── setup.sh
│   └── skills/
│       ├── citation_check/SKILL.md
│       ├── discussion_draft/SKILL.md
│       ├── homework_tutor/SKILL.md
│       ├── introduction_draft/SKILL.md
│       ├── literature_review/SKILL.md
│       ├── manuscript_polish/SKILL.md
│       ├── paper_summary/SKILL.md
│       └── thesis_proposal/SKILL.md
├── docs/
│   ├── product.md
│   ├── roadmap.md
│   ├── safety.md
│   └── skill_spec.md
├── examples/
│   ├── paper_summary_example.md
│   ├── polish_example.md
│   ├── review_outline_example.md
│   └── thesis_proposal_example.md
├── exports/
│   └── README.md
├── prompts/
│   ├── citation_policy.md
│   ├── disclaimer.md
│   ├── system_edu.md
│   └── writing_policy.md
├── scripts/
│   └── md_to_docx.py
├── product.txt
├── README.md
└── requirements.txt
```

## File Roles

| Path | Role |
| --- | --- |
| `.openhands/AGENTS.md` | OpenHands repository customization entrypoint and Edu Mode behavior rules |
| `.openhands/setup.sh` | Lightweight setup hint for OpenHands environments |
| `.openhands/skills/*/SKILL.md` | Eight domain skills for biomedical reading, writing, polishing, proposals, citation checks, and tutoring |
| `prompts/system_edu.md` | Reusable system prompt for Edu Mode |
| `prompts/disclaimer.md` | Standard disclaimer appended to substantial outputs |
| `prompts/writing_policy.md` | Writing and academic integrity policy |
| `prompts/citation_policy.md` | Citation and evidence verification policy |
| `docs/product.md` | Product scope and v0.1 goals |
| `docs/safety.md` | Safety boundaries and recommended permission limits |
| `docs/skill_spec.md` | Skill list, structure, and shared rules |
| `docs/roadmap.md` | v0.1 through later-phase roadmap |
| `docs/agent.md` | Agent branch positioning, memory/planning/tool-audit architecture, and permission levels |
| `docs/agent_examples.md` | Demonstration inputs and expected outputs for Agent workflows |
| `docs/positioning.md` | Agent product-line positioning, workbench modules, and roadmap |
| `docs/competitive_notes/openscience.md` | OpenScience reference note and differentiation guidance |
| `docs/competitive_notes/biomni.md` | Biomni reference note and biomedical-agent differentiation guidance |
| `examples/*.md` | Copyable test prompts |
| `examples/reference_verification_example.bib` | BibTeX upload and reference verification example |
| `exports/README.md` | Export workflow notes |
| `scripts/md_to_docx.py` | Simple Markdown to DOCX converter |
| `requirements.txt` | Python dependencies for DOCX export and document upload parsing |
| `schemas/agent/*.json` | Agent memory, task plan, tool-call, and evidence schemas |
| `examples/agent_*` | Agent workflow examples with demonstration outputs |
| `.env.example` | Qwen / DashScope environment variable template |

## Local Start

### Lightweight Local Web UI

This repository includes a dependency-free local web UI for quick testing before OpenHands is installed.

Start it on Windows PowerShell:

```powershell
.\scripts\start_web.ps1
```

Or start it directly:

```bash
python web_app/server.py --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

The page can work in prompt-only mode without an API key. To call Qwen, either paste the API key into the local page for the current session, or set `DASHSCOPE_API_KEY` before starting the server. The key is not written to project files.

Document upload is available in the sidebar. Supported formats:

- `.txt`, `.md`, `.csv`, `.tsv`, `.json` and other plain-text files
- `.docx`
- `.pdf`

The local server extracts text and inserts it into the input box. PDF uploads are routed to paper reading; BibTeX uploads are routed to reference verification. Uploads are limited to 12 MB, and extracted text is capped at 120,000 characters. Scanned PDFs require OCR first.

### OpenHands / Agent Canvas

1. Start OpenHands / Agent Canvas according to your OpenHands installation.
2. Open this repository in OpenHands.
3. Confirm OpenHands can read `.openhands/AGENTS.md`.
4. Start a new conversation and ask: `你是谁？`
5. Expected behavior: the agent identifies itself as Open-Rosalind Edu, answers in Chinese, and explains Edu Mode boundaries.

If your OpenHands version supports the `agent-canvas` command:

```bash
agent-canvas
```

Then open the local Web UI, usually:

```text
http://localhost:8000
```

## Qwen Configuration

Use Qwen through an OpenAI-compatible endpoint.

Environment variables:

```bash
export DASHSCOPE_API_KEY="your_api_key"
export QWEN_BASE_URL="https://llm-jl24o09ebj303z4e.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
export QWEN_MODEL="qwen3.7-max"
```

OpenHands LLM settings:

```text
Provider: OpenAI-compatible / Custom
Custom Model: openai/qwen3.7-max
Base URL: https://llm-jl24o09ebj303z4e.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
API Key: ${DASHSCOPE_API_KEY}
```

Recommended models:

- `qwen3.7-max` for the current recommended high-quality writing model
- `qwen-plus` for default use when available
- `qwen-max` for higher-quality writing when available
- `qwen-long` for long document reading
- `qwen-turbo` for lower-cost quick drafting

Optional LiteLLM proxy configuration:

```yaml
model_list:
  - model_name: qwen3.7-max
    litellm_params:
      model: openai/qwen3.7-max
      api_key: os.environ/DASHSCOPE_API_KEY
```

Then configure OpenHands:

```text
Custom Model: litellm_proxy/qwen3.7-max
Base URL: http://localhost:4000
API Key: any-non-empty-key
```




## Open-Rosalind Agent

The `agent` branch starts the independent Agent version. Edu remains the beginner product; Agent is for research execution workflows with memory, task planning, tool audit, and traceable reports.

Current Agent modules:

- Task Planner Agent
- Memory Agent
- Tool Audit Agent
- Traceable Report Agent

Current contracts:

- `schemas/agent/memory.schema.json`
- `schemas/agent/task_plan.schema.json`
- `schemas/agent/tool_call.schema.json`
- `schemas/agent/evidence.schema.json`

Claude Code / Agent Skills-compatible files live under `.claude/skills/`.

## Workflow Agents

The local web UI organizes capabilities as workflow agents instead of a flat skill list. Each second-level item behaves like a focused assistant with its own prompt template and local conversation history.

Current groups:

- 文献阅读: 论文精读 Agent, 论文问答 Agent
- 综述与选题: 综述大纲 Agent, 开题报告 Agent
- 论文写作: Introduction Agent, Discussion Agent, 论文润色 Agent
- 引用与核验: 参考文献验证 Agent, Claim 证据核验 Agent
- 学习辅导: 课程/作业辅导 Agent

This keeps beginner workflows explicit while still allowing free-form follow-up conversation inside each agent.

## Reference Verification

The local web UI includes a `Verify Refs` button for bibliography screening. It performs deterministic metadata checks instead of asking the model to guess whether a paper exists.

Current checks:

- DOI lookup through Crossref
- PMID lookup through PubMed E-utilities
- Bibliographic candidate search through Crossref when no DOI/PMID is supplied
- Year and title-overlap mismatch warnings
- Risk labels: `Verified`, `Metadata Mismatch`, `Candidate Match`, `Unverified`, `Fabrication Risk`

This verifies reference existence and metadata consistency only. A real paper may still fail to support a manuscript claim, so high-risk biomedical claims still require reading the original source.

## DOCX Export

Install the export dependency:

```bash
pip install -r requirements.txt
```

Convert Markdown to DOCX:

```bash
python scripts/md_to_docx.py exports/output.md exports/output.docx
```

The converter supports a conservative Markdown subset: headings, paragraphs, bullet lists, numbered lists, fenced code blocks, and simple pipe tables.

## Four Test Prompts

### 1. Paper Reading

```text
请使用 Paper Summary Skill 帮我精读这篇生物医学论文。请输出：一句话总结、研究背景、核心问题、方法、主要结果、局限性、可引用点、需要人工核验的地方。
```

### 2. Literature Review

```text
请使用 Literature Review Skill，围绕“肿瘤微环境中肿瘤相关巨噬细胞对免疫治疗反应的影响”生成一个生物医学综述大纲，包括章节结构、每节写作要点、推荐检索关键词、潜在图表设计和需要核验的科学问题。
```

### 3. Manuscript Polish

```text
请使用 Manuscript Polish Skill 润色下面这段学术文本。要求保持科学含义不变，提高逻辑、清晰度和学术表达，并指出可能存在的科学表述风险：

The expression of Gene X was obviously higher in tumor tissues, and this means Gene X can promote cancer progression and can be used as a treatment target.
```

### 4. Thesis Proposal

```text
请使用 Thesis Proposal Skill，围绕“基于单细胞转录组分析探索炎症性肠病中上皮细胞状态转变及其免疫调控机制”生成开题报告草稿，包括研究背景、科学问题、研究目标、研究内容、技术路线、创新点、可行性分析、预期结果和时间计划。
```

## TODO

- Verify the exact OpenHands / Agent Canvas command and repository customization behavior in the target deployment.
- Add real end-to-end examples based on public biomedical papers.
- Add a second-phase `graphical_abstract` Skill.
- Design a controlled literature search interface; do not connect a real PubMed API until safety and citation handling are reviewed.
- Improve DOCX export styling, especially Chinese fonts and tables.
- Evaluate whether to keep using OpenHands Web GUI or build a dedicated Next.js frontend.
