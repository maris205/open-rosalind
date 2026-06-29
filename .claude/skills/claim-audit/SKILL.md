---
name: claim-audit
description: Use when auditing biomedical claims against supplied evidence, references, RAG chunks, paper excerpts, or sequence annotations.
---
# Claim Audit Skill

Use this skill when the user provides claims and wants to know whether the evidence supports them.

## Purpose

Detect unsupported, overclaimed, or high-risk biomedical statements before they enter a manuscript, report, or proposal.

## Output Structure

1. Claim 拆解
2. 证据来源清单
3. Claim-证据对应表
4. 风险等级
5. 过度推断或缺失证据
6. 建议改写
7. 需要人工核验的地方

## Risk Labels

- Low: general background or well-established descriptive claim
- Medium: specific mechanism, association, biomarker, pathway, or preclinical interpretation
- High: clinical efficacy, diagnostic accuracy, survival benefit, safety, treatment recommendation, causality from observational data

## Rules

- A real reference does not automatically support a claim.
- Do not infer causality from correlation unless the supplied evidence justifies it.
- Do not invent missing data.
- Require original-source checking for High-risk claims.
