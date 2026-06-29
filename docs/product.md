# Open-Rosalind Edu v0.1 Product Notes

Open-Rosalind Edu 是一个基于 OpenHands、Qwen 和领域化 Edu Skills 的生物医学学习与学术写作 Agent。

## 产品定位

面向生物医学学生、研究生和青年科研人员，提供文献学习、写作辅助、论文润色、开题报告准备、课程报告辅导和引用核验提醒。

## v0.1 目标

第一阶段不重写 OpenHands runtime，不实现复杂平台能力。目标是让当前仓库作为 OpenHands repository customization 运行起来。

核心能力：

- 文献精读和 PDF 论文总结
- 综述大纲生成
- Introduction / Discussion 初稿
- 中文和英文论文润色
- 开题报告辅助
- 作业和课程报告辅导
- 引用与证据核验提醒
- Markdown 输出和 DOCX 导出

## 非目标

- 多用户权限系统
- 计费系统
- 完整 PubMed API 集成
- 完整引用数据库
- 可复现科研 pipeline
- 临床诊断或治疗建议
- 自动投稿
- 自动代写并伪装人工写作

## 技术路线

```text
OpenHands Agent Canvas / Web GUI
    -> OpenHands Agent Runtime
    -> Qwen API / DashScope / OpenAI-compatible endpoint
    -> Open-Rosalind Edu Skills
    -> Biomedical writing / literature / education workflows
```
