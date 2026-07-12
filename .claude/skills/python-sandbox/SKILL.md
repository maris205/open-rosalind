---
name: python-sandbox
description: Use when planning a short biomedical Python analysis that will be reviewed and explicitly approved before execution in the Open-Rosalind Docker sandbox.
---
# Python Sandbox Skill

Prepare reproducible Python analysis for the controlled offline executor.

## Workflow

1. Clarify the research question and supplied data.
2. Separate supplied facts, assumptions, and missing inputs.
3. State the planned analysis, expected outputs, and validation checks.
4. Provide one complete `python` fenced code block.
5. Stop for user review and approval. Never claim the code ran.

## Runtime Contract

- Python standard library only in the initial image.
- No network access.
- Read inputs from `/workspace/input` when available.
- Write all generated files to the current directory (`/workspace/output`).
- Maximum runtime and resources are server-controlled.
- Raw input files must never be modified.

## Biomedical Rules

- Do not invent observations, sample sizes, variables, p-values, or effect sizes.
- Preserve identifiers, units, missing values, and denominators.
- Distinguish exploratory analysis from confirmatory analysis.
- Do not convert association into causation.
- Treat clinical interpretation as requiring expert review.
- Include deterministic seeds when randomness is necessary.
