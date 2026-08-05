---
name: agent-report-builder
description: Use when compiling plans, memory, evidence records, tool logs, and claims into a traceable research report.
---
# Agent Report Builder Skill

Use this skill when the Agent needs to produce a final or interim report from task execution.

## Purpose

Generate a report where claims, evidence, tool calls, and remaining uncertainty remain traceable.

## Output Structure

1. Executive summary
2. Research goal
3. Task plan executed
4. Evidence used
5. Tool calls and outputs
6. Main findings
7. Unsupported claims and uncertainties
8. Reproducibility checklist
9. Next steps
10. Appendix: source and tool-call map

## Rules

- Every major finding should cite evidence records or tool outputs.
- Mark unsupported inferences explicitly.
- Include failed or skipped steps when relevant.
- Do not invent missing results.
- Clinical or translational claims require high-risk manual review.
