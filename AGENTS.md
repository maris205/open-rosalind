# AGENTS.md

## Project

Open-Rosalind is a tool-first, evidence-grounded, traceable, workflow-constrained bio-agent system.

## Core principles

1. Tool correctness: biological facts and computations must come from skills/tools, not model guesses.
2. Evidence grounding: every scientific conclusion must cite evidence from skill outputs.
3. Trace completeness: every execution step must produce structured trace.
4. Workflow stability: agent behavior must follow MCP/workflow constraints, not free-form loops.

## Architecture rules

- Do not bypass the Skill Registry.
- Do not let Harness call tools directly. Harness calls AgentAdapter; Agent calls MCP; MCP calls Skills.
- Do not add unconstrained autonomous planning.
- Do not add long-term memory for biological/private data without explicit design approval.
- Keep Web Chat UI as the main user entry.
- Keep CLI/API as secondary developer entry.

## Coding rules

- Use typed Python where practical.
- Prefer Pydantic schemas for request/response/spec validation.
- Keep skill outputs structured.
- Always include evidence and trace fields in API responses.
- Add tests for new skills and workflows.

## Test commands

Run before finalizing changes:

```bash
pytest
python benchmark/run_biobench.py