---
name: evidence-manager
description: Use when turning uploaded papers, notes, database snippets, RAG passages, or tool outputs into traceable evidence records for biomedical research tasks.
---
# Evidence Manager Skill

Use this skill when the Agent needs to extract, normalize, or review evidence before drawing conclusions.

## Purpose

Convert raw biomedical materials into auditable evidence records that can be linked to claims, plans, memory, tool logs, and reports.

## Output Structure

1. Source inventory
2. Evidence record table
3. Claims supported by each record
4. Verification status
5. Missing metadata
6. Risk notes
7. Manual review checklist

## Evidence Table

| Evidence ID | Source locator | Evidence type | Claim or observation | Support level | Verification status | Notes |
| --- | --- | --- | --- | --- | --- | --- |

## Rules

- Do not invent DOI, PMID, accession IDs, sample sizes, p-values, or database records.
- Preserve source locators such as file name, page, paragraph, DOI, PMID, URL, accession, or tool-call ID.
- Separate directly observed evidence from model inference.
- Mark weak, missing, or unverifiable evidence explicitly.
- High-risk biomedical or clinical claims require manual source review.