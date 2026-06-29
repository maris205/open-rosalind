---
name: evidence-retrieval
description: Use when retrieving, organizing, and summarizing evidence from provided papers, future RAG chunks, sequence records, notes, or trusted biomedical documents.
---
# Evidence Retrieval Skill

Use this skill when the user asks to find supporting evidence from uploaded sources, copied excerpts, a future RAG store, sequence annotations, or project documents.

## Purpose

Produce evidence-grounded answers that preserve source traceability.

## Output Structure

1. 检索问题
2. 使用的数据源 / 文档源
3. 证据表
4. 支持的 claim
5. 反向或冲突证据
6. 证据强度
7. 不能回答的问题
8. 下一步检索建议

## Evidence Table Fields

Use this table when possible:

| Claim | Source | Locator | Evidence excerpt | Support level | Notes |
| --- | --- | --- | --- | --- | --- |

## Rules

- Do not fabricate source chunks, papers, sequence records, or database hits.
- If no RAG/search was actually performed, say so clearly.
- Keep source locators such as filename, page, section, DOI, PMID, sequence ID, or chunk ID when available.
- Separate evidence summary from model inference.
- Label unsupported claims as unverified.
