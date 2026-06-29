# Paper Summary Skill

Use this skill when the user uploads, pastes, or refers to a biomedical paper.

## Purpose

Help the user quickly understand a biomedical paper and convert it into structured study notes.

## Input

Possible inputs:

- PDF content
- paper title
- abstract
- DOI
- PMID
- copied paper text
- user question about the paper

## Output Structure

Return the answer in Chinese unless the user asks otherwise.

Use this structure:

1. 论文一句话总结
2. 研究背景
3. 核心科学问题
4. 研究对象 / 数据来源
5. 方法概述
6. 主要结果
7. 作者结论
8. 局限性
9. 可以用于写作引用的点
10. 需要人工核验的点

## Rules

- Do not invent results not present in the input.
- Do not invent PMID, DOI, authors, journal, or year.
- If the paper is incomplete, say which parts are missing.
- If the user asks for a critical review, include strengths and weaknesses.
- If the user asks for a Chinese summary, keep terminology accurate and natural.
- If the user asks for English output, write in academic English.
- Always include a manual verification checklist.
- End substantial outputs with the Edu Mode disclaimer.
