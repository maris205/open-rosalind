# Agent Examples

These examples demonstrate the intended behavior of the independent Open-Rosalind Agent version.

## Example Set

| File | Purpose |
| --- | --- |
| `examples/agent_task_planner_example.md` | Shows an approval-ready plan before tool execution |
| `examples/agent_memory_update_example.json` | Shows structured project/evidence/task/decision memory |
| `examples/agent_tool_audit_example.json` | Shows a single tool-call audit log |
| `examples/agent_traceable_report_example.md` | Shows a traceable research report format |

## Demo Flow

1. Open the local Agent web UI.
2. Select `Agent 正式版 -> 任务规划 Agent`.
3. Paste the user input from `agent_task_planner_example.md`.
4. Review the generated plan before any tool execution.
5. Use `agent_memory_update_example.json` as the expected memory shape.
6. Use `agent_tool_audit_example.json` as the expected tool-call log shape.
7. Use `agent_traceable_report_example.md` as a report target.

## Design Notes

The examples intentionally include placeholders and unverified records. This is deliberate: the Agent version must not treat generated examples as factual evidence.

Future RAG integration should replace placeholders with real evidence records that include:

- source ID
- source type
- DOI / PMID / sequence ID / dataset ID when available
- locator such as page, chunk, section, coordinate, or table
- evidence excerpt
- verification status
