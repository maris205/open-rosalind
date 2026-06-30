# Agent Task Planner Example

## Scenario

用户希望验证一个生物医学机制是否有可靠证据支持，并希望 Agent 自动规划后续检索、引用核验和报告生成步骤。

## User Input

```text
我想验证“IL-6 signaling 可能参与炎症性肠病患者肠上皮损伤和免疫细胞募集”这个机制是否有文献和数据支持。

请先不要直接下结论，先帮我规划一个可执行、可追溯的任务流程。
```

## Example Agent Output

# 任务规划草案

## 1. Goal Restatement

验证以下机制性 claim 是否有可靠证据支持：

> IL-6 signaling 可能参与炎症性肠病患者肠上皮损伤和免疫细胞募集。

当前阶段不直接给出结论，而是规划可审计的证据检索、引用核验、claim 审计和报告生成流程。

## 2. Known Inputs

- 疾病：炎症性肠病，IBD
- 机制：IL-6 signaling
- 过程：肠上皮损伤、免疫细胞募集
- 证据需求：文献证据、未来可扩展到表达数据或单细胞数据

## 3. Missing Inputs

- 是否限定 Crohn's disease、ulcerative colitis，还是 IBD 泛称
- 是否需要人类临床样本证据，还是也接受动物模型和体外实验
- 是否已有候选论文、BibTeX、PDF 或内部 RAG 文档
- 是否需要结合用户自己的组学数据

## 4. Task Plan

| Step ID | Action | Tool | Input refs | Expected output | Permission level | Needs approval |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | 拆解 claim 为可检索问题 | research-question | user_claim | PICO/机制型问题、关键词 | 0 | No |
| S2 | 检索或读取候选文献 | future_rag_search / uploaded_pdf | search_terms, uploaded_docs | 候选证据列表 | 1 | No |
| S3 | 验证参考文献元数据 | reference_verifier | DOI/PMID/BibTeX | Verified/Mismatch/Unverified 标签 | 1 | No |
| S4 | 逐条审计 claim 支持度 | claim-audit | evidence_chunks | claim-evidence 表 | 1 | No |
| S5 | 生成可追溯报告 | agent-report-builder | evidence_table, audit_log | Markdown 报告 | 2 | No |
| S6 | 若用户提供表达矩阵，规划分析 | analysis-plan | dataset_description | 分析计划，不运行代码 | 0 | No |
| S7 | 运行统计或生信分析 | future_executor | approved_dataset | 结果文件和日志 | 3 | Yes |

## 5. Evidence Requirements

| Claim component | Evidence needed | Risk |
| --- | --- | --- |
| IL-6 与 IBD 炎症相关 | 人类样本、综述或机制研究 | Medium |
| IL-6 signaling 与上皮损伤相关 | 机制研究、上皮模型、组织证据 | Medium |
| IL-6 与免疫细胞募集相关 | 细胞因子、趋化因子、免疫浸润证据 | Medium |
| 可作为治疗靶点 | 临床或药物研究 | High |

## 6. Risk Controls

- 不把“相关”写成“导致”，除非证据支持因果。
- 不把动物模型直接外推成人类 IBD。
- 不伪造 DOI、PMID 或引用。
- 如果只有综述证据，标注为二级证据。
- 临床疗效相关表述必须进入 High-risk manual review。

## 7. Approval Needed

当前计划 S1-S5 可作为只读流程执行。  
若进入 S7 运行用户数据分析，需要用户确认数据路径、分析范围和输出目录。

## 8. Expected Deliverable

最终输出：

- claim-evidence table
- verified reference list
- unsupported claim list
- cautious mechanism summary
- next-step analysis recommendations

提示：这是 Agent 任务规划草案，不代表证据已经完成检索或验证。
