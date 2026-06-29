# Open-Rosalind Research Branch

This branch adds a Research Agent layer above the Edu workflow.

## Product Positioning

Open-Rosalind Edu is the beginner-facing learning and writing workflow.

Open-Rosalind Research is the evidence-grounded research workflow. It is designed to sit between Edu and a future full ReAct-style execution agent.

```text
Edu: learn, read, draft
Research: retrieve, verify, audit, plan
Agent: execute, trace, and report
```

## Current Scope

This branch does not implement the full RAG store yet. It prepares the agent and skill structure so future RAG components can plug in cleanly.

Current Research agents:

- Research Question Agent
- Evidence Retrieval Agent
- Claim Audit Agent
- Protocol Draft Agent
- Analysis Plan Agent
- Research Report Agent

## Claude Code / Agent Skills Compatibility

Research skills are stored under:

```text
.claude/skills/<skill-name>/SKILL.md
```

Each `SKILL.md` uses Agent Skills-style YAML frontmatter:

```yaml
---
name: research-question
description: Use when turning a broad biomedical interest into a precise, searchable, testable research question with scope, entities, outcomes, and evidence needs.
---
```

Directory names match skill names and use lowercase hyphen-separated identifiers.

## RAG-Ready Contract

Future RAG retrieval should return evidence chunks with stable locators:

| Field | Meaning |
| --- | --- |
| source_id | Stable document, paper, sequence, or project record ID |
| source_type | paper, sequence, protocol, note, dataset, guideline |
| title | Source title or record name |
| locator | page, section, chunk ID, sequence ID, coordinate, table, figure |
| excerpt | Short evidence text or annotation |
| metadata | DOI, PMID, version, date, organism, database, file hash |

Research agents should treat retrieved chunks as evidence candidates, not automatic truth.

## Trust Rules

- No fabricated DOI, PMID, references, sequence IDs, datasets, sample sizes, or p-values.
- Every major claim should be linked to a source locator when available.
- If a claim lacks source support, mark it as unverified.
- A real reference does not automatically support a claim.
- High-risk biomedical claims require manual review of original sources.
- Wet-lab protocols and clinical interpretations must remain review-ready drafts.
