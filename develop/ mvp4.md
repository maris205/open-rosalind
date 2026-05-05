是的，你的 **Open‑Rosalind Skills** 系统确实可以**借鉴 Claude Code 等常用的 agent 框架格式**，但是需要在**符合你们的核心设计原则**的前提下做一些**定制化和优化**。下面我们来详细对比一下：

---

### **Claude Code / 通用大模型的 Skill 格式**

Claude Code 和其他常见大模型平台通常有以下特点：

1. **技能功能：**

   * **简单接口**：通常是由接口与任务指令组成，输入可以是文本、命令、参数等。
   * **功能灵活：** 类似于执行代码、文本生成等任务，具有很强的通用性。
   * **自由度高：** 没有严格的输入输出要求，任务过程可以自由推理和调度。
2. **缺点：**

   * **缺乏标准化：** 可能导致不同任务间的实现方式差异较大，输出结果的不一致性。
   * **证据和trace不完整：** 很难保证每一步的输出有确凿证据，也难以重现。
   * **不够适合科研：** 很多场景下不具备明确的、可重复验证的工作流程。

---

### **Open‑Rosalind Skill 的设计原则**

与你们的核心设计原则相符，Open‑Rosalind 的 **Skills** 需要：

1. **Tool-First：**
   所有技能都必须通过特定的生物工具（数据库、算法、API 等）来实现。每个技能的执行必须依赖于经过验证的工具，而非单纯的模型推理。

2. **Evidence-Grounded：**
   每个结果必须能够追溯到数据源或文献。例如，在输出一个蛋白质注释时，必须提供相应的 UniProt 条目，且该条目是已验证的。

3. **Traceable：**
   每个技能的执行过程必须记录清楚，方便后续验证和复现。所有的中间步骤、工具调用、输入输出、状态变更都应该在 trace 中清晰可见。

4. **Workflow-Constrained：**
   系统中所有技能都必须按照预定的工作流和任务模板执行，而不是自由形式的推理。确保任务的结构化和稳定性。

---

### **如何把 Claude Code 等格式与 Open‑Rosalind 的原则结合**

我们可以借鉴 Claude Code 和其他系统的设计思想，但要通过下列方式**定制化**，以符合 Open‑Rosalind 的设计原则：

#### 1. **输入输出的标准化**：

* **Claude Code**：允许任何形式的输入输出（自由文本、代码等）。
* **Open‑Rosalind**：输入输出必须遵循特定的格式和结构，例如：

  * 输入：必须定义清晰的 schema，如 `protein_sequence`, `gene_name`, `uniprot_id`。
  * 输出：必须是结构化的结果，例如包含 `summary`, `evidence`, `trace`, `confidence`。

#### 示例：

```json
{
  "name": "uniprot_lookup",
  "input_schema": {
    "query": "string",  // 必须是基因名或蛋白ID
    "organism": "string"  // 可选，限制物种
  },
  "output_schema": {
    "annotation": "string",
    "evidence": "array",
    "trace": "array"
  },
  "evidence_schema": {
    "source": "UniProt",
    "url": "string"
  },
  "deterministic": true,
  "requires_network": true,
  "local_available": false,
  "dependencies": ["requests"]
}
```

#### 2. **任务执行的标准化与受控性**：

* **Claude Code**：任务和工具调用非常灵活，执行顺序不固定。
* **Open‑Rosalind**：所有的技能执行都应该通过受控的工作流（MCP），并且每个步骤都需要通过明确的工具进行。

#### 示例工作流：

```text
User Query: "Analyze protein sequence"
→ Task Router (Determine whether it's a single-step or multi-step task)
→ Multi-step Control Protocol (MCP)
→ Step 1: Sequence Analysis (Call `sequence.detect_type`)
→ Step 2: Protein Annotation (Call `uniprot.search`)
→ Evidence Aggregation
→ Summary (Call `protein.annotation_summary`)
```

#### 3. **证据和 trace**：

* **Claude Code**：一般没有强制要求记录所有步骤的 trace，往往结果输出会不带证据。
* **Open‑Rosalind**：必须记录每个步骤的 trace，且每个结果必须有证据来源。

#### 示例 trace 记录：

```json
{
  "step": 1,
  "skill": "uniprot_lookup",
  "input": {
    "query": "BRCA1",
    "organism": "Homo sapiens"
  },
  "output": {
    "annotation": "BRCA1 is a tumor suppressor gene",
    "evidence": [
      {"source": "UniProt", "url": "https://uniprot.org/uniprot/P38398"}
    ],
    "trace": [
      {"action": "query UniProt", "timestamp": "2026-04-30T10:00:00Z"}
    ]
  },
  "status": "success",
  "latency_ms": 500
}
```

#### 4. **技能与任务的限制和可验证性**：

* **Claude Code**：它的开放性虽然给了更多灵活性，但也让任务的执行变得难以预测和验证。
* **Open‑Rosalind**：所有任务必须经过严密的规划和约束，技能和工具的调用必须是可复现的，且每个步骤都可以回溯。

#### 示例限制：

```text
- Task Router: Decides which skill to call based on user query (input validation).
- Multi-step Control Protocol: Enforces a structured task flow.
- Evidence & Trace: Mandatory for each skill, ensuring traceability.
```

---

### **最终总结**：

通过这种方式，你可以**借鉴 Claude Code 等通用 agent 的灵活性**，但同时 **确保工具驱动、标准化的框架**，以满足 Open‑Rosalind 特有的需求。

具体来说：

* **结构化的输入输出规范**（包括 evidence 和 trace）。
* **受控工作流**（每个任务必须符合一定的执行顺序和约束）。
* **高复现性**（每个步骤都能被验证和回溯）。

这种方式让你既能借用现有 agent 框架的优点，又能保持 Open‑Rosalind 在生物医学领域的差异化优势。





### Open-Rosalind Skill Spec 模板与 Repo 目录结构模板

为了帮助你顺利扩展技能库并让 **Codex** 自动化编写相关代码，下面我给你提供了一个 **Skill Spec 模板** 和 **Repo 目录模板**。你可以用它们作为标准化起点，开始构建新的技能，并轻松进行扩展。

---

## **1. Skill Spec 模板（用于描述技能的标准化格式）**

### **Skill Spec 模板结构**

```json
{
  "name": "skill_name",  // 技能名称，便于识别和调用
  "display_name": "Skill Display Name",  // 用户友好的技能名称
  "description": "Short description of what this skill does.",  // 简短描述
  "category": "category_name",  // 分类，比如 protein_annotation, sequence_analysis 等
  "version": "v1",  // 版本
  "input_schema": {  // 输入参数结构
    "parameter_1": "type",
    "parameter_2": "type"
  },
  "output_schema": {  // 输出参数结构
    "result": "type",
    "evidence": "array",
    "trace": "array"
  },
  "evidence_schema": {  // 证据结构
    "source": "string",
    "url": "string",
    "accession": "string?"
  },
  "deterministic": true,  // 是否确定性，通常工具调用是确定的
  "requires_network": true,  // 是否需要网络访问（比如查询外部数据库）
  "local_available": false,  // 是否支持本地化（例如本地数据库查询）
  "safety_level": "low",  // 安全级别（如果技能执行的操作有潜在风险）
  "dependencies": ["requests", "biopython"],  // 技能的依赖库
  "examples": [  // 示例用法
    {
      "input": { "parameter_1": "value" },
      "output_preview": { "result": "value", "evidence": ["link"] }
    }
  ]
}
```

---

### **字段解释：**

1. **name**: 用于唯一标识该技能的名称。
2. **display_name**: 适合用户看到的名称，可以稍微简洁一点。
3. **description**: 简要描述该技能的功能。
4. **category**: 将技能按任务类型进行分类，便于检索和组织。
5. **input_schema** 和 **output_schema**: 定义技能的输入和输出数据结构。保证每个技能的输入输出规范化。
6. **evidence_schema**: 强制要求所有结果都附带证据来源，保障输出的可靠性。
7. **deterministic**: 该技能是否是确定性的，通常工具调用是确定的。
8. **requires_network** 和 **local_available**: 是否需要访问外部服务或是否支持本地运行。
9. **safety_level**: 依据技能的执行性质，设定它的安全级别。
10. **dependencies**: 技能依赖的第三方库。
11. **examples**: 提供使用该技能的具体示例，便于开发和验证。

---

## **2. Open-Rosalind Skill Repo 目录模板**

以下是基于 Open-Rosalind 架构和功能，设计的一个标准化的技能库目录结构。所有技能文件和资源会按照不同层次和分类进行组织，便于维护和扩展。

### **Repo 目录结构**

```text
open_rosalind/
├── skills/                      # 技能文件夹，所有技能都存放在此
│   ├── sequence/                # 序列相关技能
│   │   ├── detect_type.py       # 序列类型检测
│   │   ├── gc_content.py       # 计算GC含量
│   │   └── translate.py        # 翻译序列
│   ├── protein/                 # 蛋白质相关技能
│   │   ├── basic_stats.py      # 蛋白质基础统计
│   │   ├── annotation_summary.py # 蛋白质注释总结
│   │   └── structure_summary.py # 蛋白质结构总结
│   ├── mutation/                # 突变相关技能
│   │   ├── diff.py             # 突变差异检测
│   │   ├── classify_basic.py   # 突变影响分类
│   │   └── clinvar_search.py   # ClinVar 突变查询
│   ├── literature/              # 文献相关技能
│   │   ├── search.py           # PubMed 搜索
│   │   └── fetch_abstract.py   # 获取文献摘要
│   ├── workflow/                # 任务工作流相关技能
│   │   ├── protein_annotation.py # 蛋白质注释流程
│   │   ├── mutation_assessment.py # 突变评估流程
│   │   └── literature_review.py # 文献审查流程
│   └── utils/                   # 工具和辅助功能
│       ├── cache.py            # 缓存管理
│       ├── helper.py           # 辅助函数
│       └── validation.py       # 输入输出验证
├── skill_specs/                 # Skill 规范文件夹
│   ├── sequence.detect_type.json # 序列类型检测规范
│   ├── protein.basic_stats.json # 蛋白质基础统计规范
│   ├── mutation.diff.json      # 突变差异检测规范
│   └── workflow.protein_annotation.json # 蛋白质注释流程规范
└── tests/                       # 测试文件夹
    ├── test_sequence.py        # 测试序列相关技能
    ├── test_protein.py         # 测试蛋白质相关技能
    ├── test_mutation.py        # 测试突变相关技能
    └── test_workflow.py        # 测试工作流相关技能
```

---

### **目录解释**：

1. **skills/**：存放各个技能模块的 Python 文件，每个技能文件通常对应一个功能或任务。

   * 根据任务类型分类（如 `sequence`、`protein`、`mutation` 等）；
   * 每个技能的文件命名需要简洁且有意义。

2. **skill_specs/**：每个技能对应的 **Skill Spec** JSON 文件，详细定义输入输出格式、技能依赖等。它可以帮助生成相应的文档，也有助于程序化调用。

3. **tests/**：存放与技能对应的单元测试文件，确保技能实现的正确性和符合预期。

4. **utils/**：存放辅助函数或通用工具，如缓存、验证等功能。

---

### **如何利用这个模板**：

1. **利用 Codex 生成技能代码**：通过提供 Skill Spec 文件，Codex 可以帮助你自动生成技能代码（例如 `sequence.detect_type.py`），并且在必要时，基于规范生成相应的接口和处理逻辑。

2. **根据需求扩展**：在这个目录结构下，你可以逐步增加新的技能文件，并根据新的需求添加相应的测试、规范文件。

3. **集成和协作**：这个结构也适合团队合作，确保技能按照标准化流程构建和测试，便于后续维护和功能扩展。

---

### **Codex 可以帮你做什么？**

1. **自动生成 Skill 代码**：提供简单的 Spec 文件，Codex 可以生成整个 Python 文件和相应的输入输出处理逻辑。
2. **自动生成测试用例**：基于 Spec，Codex 可以自动生成单元测试，确保技能的健壮性。
3. **自动生成文档**：Codex 可以根据规范文件生成 API 文档、使用示例和技能说明。

---

# **总结**：

通过这种结构化的设计，你能够轻松地扩展 Open‑Rosalind 的功能，并在严格的标准和可重复的框架下保证每个技能的质量和可用性。未来随着新技能的加入，Codex 还可以帮助你自动化很多工作，提高开发效率。

如果你愿意，我可以进一步帮助你整理这些技能模块的具体开发任务，或者直接生成代码片段，帮助加速你的开发过程！


好的，下面是 **Open‑Rosalind 30 个优先 Skill 清单**，这些技能涵盖了 **基础生物学、蛋白质分析、文献检索、突变评估、数据检索、基因注释** 等多个重要领域，既能覆盖常见的生物学任务，也能支撑后续扩展和复杂的多步任务。

---

# **Open‑Rosalind 30 个优先 Skill 清单**

---

## **1. Sequence Analysis Skills（序列分析技能）**

1. **sequence.detect_type**

   * 识别输入的序列类型（DNA、RNA、蛋白质等）。

2. **sequence.gc_content**

   * 计算序列的 GC 含量。

3. **sequence.translate**

   * 将 DNA/RNA 序列翻译为蛋白质序列。

4. **sequence.reverse_complement**

   * 计算序列的反向互补序列。

5. **sequence.kmer_stats**

   * 计算给定序列的 k-mer 统计信息。

6. **sequence.align_pairwise**

   * 对两条序列进行比对。

---

## **2. Protein Analysis Skills（蛋白质分析技能）**

7. **protein.basic_stats**

   * 计算蛋白质的基本统计信息（分子量、氨基酸组成等）。

8. **protein.molecular_weight**

   * 计算蛋白质的分子量。

9. **protein.annotation_summary**

   * 获取蛋白质的注释信息（UniProt/SwissProt）。

10. **protein.structure_summary**

    * 获取蛋白质的结构信息（PDB/AlphaFold）。

11. **uniprot.search**

    * 在 UniProt 中根据 ID/名称查询蛋白质信息。

12. **uniprot.fetch_entry**

    * 获取某个蛋白质条目的详细信息。

---

## **3. Mutation Analysis Skills（突变分析技能）**

13. **mutation.diff**

    * 比较两个突变的差异。

14. **mutation.classify_basic**

    * 根据影响分类突变（如错义突变、无义突变）。

15. **clinvar.search**

    * 查询 ClinVar 数据库中的突变与疾病关联。

16. **mutation.impact_summary**

    * 给出突变的功能影响总结。

---

## **4. Literature and Database Skills（文献与数据库技能）**

17. **pubmed.search**

    * 在 PubMed 中执行文献检索。

18. **pubmed.fetch_abstract**

    * 获取文献的摘要信息。

19. **pubmed.fetch_metadata**

    * 获取文献的元数据（如作者、期刊、DOI）。

20. **literature.topic_summary**

    * 对某一生物学话题进行文献总结。

21. **reactome.pathway_lookup**

    * 查询 Reactome 中的通路信息。

22. **go.term_lookup**

    * 查询 Gene Ontology 中的功能术语。

---

## **5. Gene and Transcript Annotation Skills（基因与转录本注释技能）**

23. **ensembl.gene_lookup**

    * 查询 Ensembl 中的基因信息。

24. **ensembl.transcript_lookup**

    * 查询 Ensembl 中的转录本信息。

25. **ncbi.gene_lookup**

    * 查询 NCBI Gene 数据库中的基因信息。

26. **gene.cross_reference**

    * 获取基因的跨数据库注释（如 Ensembl <-> NCBI）。

---

## **6. Pathway and Enrichment Skills（通路与富集分析技能）**

27. **reactome.enrichment_analysis**

    * 对基因集合进行 Reactome 通路富集分析。

28. **gprofiler.enrichment**

    * 使用 g:Profiler 进行基因集合富集分析。

29. **pathway.summary**

    * 获取某个通路的详细信息和富集结果。

---

## **7. Workflow and Task Management Skills（工作流与任务管理技能）**

30. **workflow.protein_annotation**

    * 蛋白质注释工作流：从序列到 UniProt 注释到功能描述。

---

# **总结与扩展**

这些技能涵盖了从基本序列分析到蛋白质注释、文献查阅、突变评估等核心生物学任务，是构建一个强大、可复现的生物信息学系统的基础。

---

## **后续扩展的优先方向：**

1. **整合本地数据库支持**（如本地 UniProt / Ensembl）。
2. **多模态技能支持**（例如整合表格数据与基因组信息，支持通路图绘制等）。
3. **实现跨平台工作流支持**，例如支持从 **FastAPI** 到 **CLI** 的全平台调用。
4. **结合 GPU 加速的技能**，如通过深度学习加速蛋白质折叠预测等复杂任务。

这些任务不仅扩展 Open-Rosalind 的技能库，也确保你能够在未来构建更复杂的任务与工作流，并继续保持生物信息学领域的竞争力。
