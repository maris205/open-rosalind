# Open-Rosalind Agent Branch

This branch starts the independent Agent version of Open-Rosalind.

Edu remains the beginner-facing learning product. Agent is a research execution product with memory, planning, tool use, evidence tracking, and audit logs.

For product positioning and external workbench references, see:

- `docs/positioning.md`
- `docs/competitive_notes/openscience.md`
- `docs/competitive_notes/biomni.md`

## Product Separation

```text
Open-Rosalind Edu
- learning workflow
- paper reading
- writing scaffolds
- low-risk fixed agents

Open-Rosalind Agent
- project memory
- task planning
- controlled tool execution
- RAG-ready evidence tracking
- audit logs
- reproducible reports
```

## Agent Core

```text
Memory Manager
  -> Project / Evidence / Task memory
Planner
  -> Goal decomposition and approval-ready task plan
Tool Executor
  -> Controlled tools with logs and permission levels
Evidence Layer
  -> Future RAG, references, sequence records, data files
Audit Log
  -> Every tool call, input, output, status, and source locator
Report Builder
  -> Traceable Markdown / DOCX reports
```

## Permission Levels

| Level | Meaning |
| --- | --- |
| 0 | Read-only answer and summarization |
| 1 | Search/read RAG, metadata, references, and uploaded files |
| 2 | Generate reports, tables, figures, and export files |
| 3 | Run local Python/R analysis in a controlled workspace |
| 4 | Modify project files after explicit approval |
| 5 | Publish, push, submit, or external sync; always requires confirmation |

## Non-Negotiable Rules

- Never fabricate DOI, PMID, sequence IDs, datasets, sample sizes, p-values, or tool outputs.
- Every major claim should be connected to evidence or marked unverified.
- Tool execution must produce an audit log entry.
- Raw input data must not be overwritten.
- Dangerous or external actions require explicit user approval.
- Clinical claims remain high-risk and require manual source review.

## Current Scope

This branch does not yet implement the full RAG database or full sandboxed executor. It defines the first agent contracts and adds Agent-oriented skills and UI entry points.

## Product Direction

Agent should be framed as a traceable biomedical research workbench. The core value is not unrestricted autonomy; it is reviewable autonomy with memory, plans, tools, evidence, and audit logs.

The public message should stay distinct from Edu:

- Edu is a guided entry product for students.
- Agent is a project workbench for research execution.
- Future Research can add the unified RAG library, sequence resources, and more advanced controlled analysis workflows.

## Demonstration Examples

Agent demos are available in:

- `examples/agent_task_planner_example.md`
- `examples/agent_memory_update_example.json`
- `examples/agent_tool_audit_example.json`
- `examples/agent_traceable_report_example.md`
- `docs/agent_examples.md`

These examples are intentionally marked as demonstration outputs. They define expected behavior and output shape, not verified biomedical evidence.