---
name: tool-audit
description: Use when reviewing planned or completed tool calls for permission, provenance, reproducibility, and safety.
---
# Tool Audit Skill

Use this skill when the Agent plans or reports tool execution.

## Purpose

Ensure every tool call has a reason, input, output, permission level, and audit trail.

## Output Structure

1. Tool call summary
2. Permission level check
3. Input provenance
4. Output summary
5. Reproducibility details
6. Failure or uncertainty notes
7. Follow-up action

## Required Log Fields

| Field | Meaning |
| --- | --- |
| tool | Tool or external service name |
| input | Structured input and source references |
| permission_level | 0-5 execution permission level |
| output_summary | Short output summary |
| output_refs | Generated file, evidence record, or result ID |
| status | planned, running, success, failed, skipped |

## Rules

- Do not hide failed tool calls.
- Do not overwrite raw data.
- Do not run high-risk or external actions without approval.
- Tool outputs are evidence candidates, not automatic truth.
