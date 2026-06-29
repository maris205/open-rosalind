# Skill Specification

Open-Rosalind Edu v0.1 使用 prompt-based OpenHands Skills。每个 Skill 是一个独立的 `SKILL.md`，用于约束触发场景、输出结构和安全规则。

## Skill 清单

| Skill | 用途 |
| --- | --- |
| paper_summary | 论文精读、PDF 总结、摘要解读 |
| literature_review | 综述大纲、相关工作、背景章节 |
| manuscript_polish | 中文/英文论文润色、翻译、降 AI 味 |
| introduction_draft | Introduction、Background、Rationale 初稿 |
| discussion_draft | Discussion 初稿和结果解释 |
| thesis_proposal | 开题报告、研究计划、课题申请草稿 |
| citation_check | claim 引用需求和证据风险核验 |
| reference_verification | 参考文献存在性、DOI/PMID 和元数据一致性核验 |
| homework_tutor | 作业、课程报告和考试复习辅导 |

## 通用规则

- 默认中文输出。
- 默认 Markdown 结构化输出。
- 不伪造引用、DOI、PMID 或实验数据。
- 对证据不足的内容明确标注。
- 对医学和临床内容避免诊断或治疗建议。
- 较长输出末尾添加 Edu Mode disclaimer。

## 后续扩展

第二阶段可增加 `graphical_abstract` Skill，用于机制图、流程图和 graphical abstract 的设计计划与图像生成提示词。
