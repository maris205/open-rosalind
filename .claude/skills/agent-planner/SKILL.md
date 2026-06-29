---
name: agent-planner
description: Use when decomposing a biomedical research goal into an approval-ready task plan with permission levels, evidence needs, tool calls, and risk controls.
---
# Agent Planner Skill

Use this skill when the user wants the Agent to plan a research task before execution.

## Purpose

Convert an open-ended research goal into an auditable plan that can be approved, revised, and executed step by step.

## Output Structure

1. Goal restatement
2. Known inputs and missing inputs
3. Assumptions
4. Task plan table
5. Required tools
6. Permission level for each step
7. Evidence and source requirements
8. Risk controls
9. User approvals needed
10. Expected final deliverables

## Plan Table

| Step ID | Action | Tool | Input refs | Expected output | Permission level | Needs approval |
| --- | --- | --- | --- | --- | --- | --- |

## Rules

- Do not execute tools while planning.
- Mark any step requiring external network, file modification, code execution, or publication.
- Prefer read-only evidence retrieval before analysis or generation.
- If evidence is missing, plan retrieval before conclusion.
- High-risk clinical claims require manual review.
