# Citation Check Skill

Use this skill when the user asks whether references support specific claims, or when the user wants citation suggestions.

## Purpose

Help identify whether a biomedical claim requires evidence and whether supplied references appear relevant.

## Output Structure

1. 原句 / claim
2. 需要引用吗？
3. 需要哪类证据？
4. 已提供引用是否可能支持？
5. 风险等级
6. 建议修改
7. 需要人工核验的地方

## Rules

- Do not invent references.
- If source text is not provided, do not claim a citation supports the statement.
- Use risk labels:
  - Low: general background claim
  - Medium: specific biomedical mechanism
  - High: clinical efficacy, diagnostic accuracy, treatment effect, survival benefit, safety claim
- End substantial outputs with the Edu Mode disclaimer.
