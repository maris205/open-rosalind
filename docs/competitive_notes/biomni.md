# Competitive Note: Biomni

Source: https://github.com/snap-stanford/Biomni

## Observed Positioning

Biomni positions itself as a general-purpose biomedical AI agent. Its README emphasizes retrieval-augmented planning, code-based execution, a large biomedical data lake, Gradio UI, MCP integration, execution-trace PDF reports, and a security warning that generated code currently runs with broad system privileges.

## Product Signal

Relevant signals for Open-Rosalind Agent:

- Biomedical users expect agent products to connect planning, retrieval, tools, and reports.
- Tool execution and code execution are valuable, but they increase safety and reproducibility risk.
- Execution history and PDF/report export are strong trust features.
- MCP-style external tool integration is becoming a familiar agent extension path.
- A large datalake can be powerful, but it creates installation, storage, licensing, and update burdens.

## Open-Rosalind Response

Open-Rosalind Agent should learn from Biomni without copying its heavy deployment model.

Recommended direction:

- Keep the first Agent version lightweight and local-web-first.
- Treat RAG and biomedical resource libraries as later infrastructure, not a mandatory first-run download.
- Make tool audit and permission levels visible before adding broad code execution.
- Support Claude Code / skills-compatible modules first; add MCP-style adapters later.
- Prioritize evidence provenance, reference verification, and report traceability as default behavior.
- Require sandboxing before any serious local Python/R execution workflow.

## Differentiation Statement

Biomni is a broad, tool-rich biomedical AI agent with heavy data and execution capabilities. Open-Rosalind Agent should be a lighter traceable biomedical research workbench: easier to run, explicit about evidence and uncertainty, safer by default, and ready to connect to future RAG and tool layers without forcing them into the entry product.

## Feature Ideas to Borrow Carefully

- Execution history export as Markdown, DOCX, and later PDF.
- Tool-call timeline in the UI.
- MCP-style tool registry once permission boundaries are stable.
- Biomedical know-how snippets with source attribution.
- Evaluation examples for task planning, evidence extraction, and reference verification.

## Guardrails

- Do not run generated code with broad system privileges.
- Do not hide tool failures or skipped steps.
- Do not treat retrieved snippets as verified facts without source locators.
- Do not make a large datalake mandatory for the lightweight Agent branch.