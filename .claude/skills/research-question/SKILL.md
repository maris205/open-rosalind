---
name: research-question
description: Use when turning a broad biomedical interest into a precise, searchable, testable research question with scope, entities, outcomes, and evidence needs.
---
# Research Question Skill

Use this skill when the user has a broad topic, rough idea, disease area, mechanism, dataset, or literature interest and needs to convert it into a researchable question.

## Purpose

Transform vague biomedical interests into clear research questions that can drive retrieval, evidence review, experiment planning, or analysis planning.

## Output Structure

Return Chinese by default unless the user asks otherwise.

1. 用户原始问题复述
2. 关键实体拆解：疾病 / 基因 / 蛋白 / 通路 / 干预 / 表型 / 数据类型
3. 可检索研究问题
4. PICO / PECO / 机制型问题框架，按场景选择
5. 纳入与排除边界
6. 需要检索的证据类型
7. 推荐检索关键词
8. 可能的研究假设，标注为假设
9. 需要人工确认的信息

## Rules

- Do not invent evidence.
- Do not claim the question is novel unless novelty was checked.
- Distinguish search terms from verified references.
- For clinical questions, do not provide diagnosis or treatment advice.
- Mark uncertain entities or unsupported assumptions.
