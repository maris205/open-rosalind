# Open-Rosalind Agent Positioning

Open-Rosalind Agent is the research-execution version of Open-Rosalind. It should be positioned as a traceable biomedical research workbench, not as a general chat assistant.

## Product Line

```text
Open-Rosalind Edu
  Beginner-facing product for students and early researchers.
  Focus: paper reading, writing scaffolds, reference checks, and explicit guided skills.

Open-Rosalind Agent
  Research execution product for project work.
  Focus: memory, planning, tool use, evidence tracking, audit logs, and reproducible reports.

Open-Rosalind Research
  Future formal research version.
  Focus: unified RAG, sequence databases, biomedical document corpora, and controlled analysis workflows.
```

Edu should remain simple and explicit. Agent should support autonomous planning and execution, while still making every important step inspectable.

## Core Position

Open-Rosalind Agent is a biomedical-first AI workbench for:

- decomposing research tasks into reviewable plans
- maintaining project memory across sessions
- validating references and evidence provenance
- running controlled local analysis workflows
- producing traceable Markdown, DOCX, and later notebook-style reports
- preparing for a unified biomedical RAG layer

The product promise is not that the model knows everything. The promise is that the system can show what it used, what it did, what remains uncertain, and what needs human review.

## Differentiation

Compared with generic scientific AI workbenches, Open-Rosalind Agent should emphasize:

- biomedical and sequence-analysis workflows from the beginning
- reference verification as a first-class skill
- evidence objects with source locators, confidence, and verification status
- Claude Code / skills-compatible agent modules
- local-first deployment for labs, courses, and internal data
- explicit permission levels for tool execution
- separation between beginner Edu workflows and more autonomous Agent workflows

This keeps the public message sharper than "AI for science" and makes the product easier to explain: Open-Rosalind Agent is for traceable biomedical research execution.

## Workbench Modules

Recommended top-level modules:

- Projects: project goals, files, datasets, reports, and status
- Planner: task decomposition, assumptions, dependencies, and approval points
- Memory: stable project facts, user preferences, constraints, and reusable context
- Evidence: references, uploaded files, database records, RAG snippets, and verification state
- Tools: controlled local or external tools with permission levels
- Audit Log: tool calls, inputs, outputs, timestamps, failures, and source locators
- Reports: traceable research notes, literature summaries, experiment plans, and final exports

The current branch already starts this through Agent skills and JSON schemas. The next implementation step is to expose these modules more clearly in the local Web UI.

## OpenScience Reference

OpenScience describes itself as an open-source AI workbench for scientific research: https://www.openscience.sh/

That direction validates the workbench framing, but Open-Rosalind should not copy a generic scientific assistant position. The stronger path is to keep the Agent version narrowly credible:

- biomedical-first
- evidence-first
- RAG-ready
- local and auditable
- compatible with skill-based agent execution

## Near-Term Roadmap

1. Add clearer Agent workbench navigation in the Web UI.
2. Add a visible project memory panel backed by `schemas/agent/memory.schema.json`.
3. Add a task-plan panel backed by `schemas/agent/task_plan.schema.json`.
4. Add a tool-audit panel backed by `schemas/agent/tool_call.schema.json`.
5. Add evidence cards backed by `schemas/agent/evidence.schema.json`.
6. Connect reference verification outputs into evidence objects.
7. Later, connect unified biomedical RAG and sequence resources.

## Messaging

Recommended short tagline:

> Open-Rosalind Agent is a traceable biomedical research workbench with memory, planning, tool audit, and evidence-backed reports.

Recommended longer description:

> Open-Rosalind Agent helps biomedical researchers plan tasks, verify literature, track evidence, execute controlled tools, and generate reproducible research reports. It is designed for traceability first: outputs should connect back to files, references, database records, tool calls, or clearly marked assumptions.