const functionGroups = [
  {
    id: "research",
    standalone: true,
    items: [
      {
        id: "research_assistant",
        title: "Rosalind Agent",
        icon: "✦",
        skill: "research_assistant",
        purpose: "主科研对话：理解任务、组织证据，并协调论文工作流。",
        template: "请作为综合生物医学科研助手处理我的任务。先识别当前需要的是规划、记忆、证据整理、工具工作流、工具审计、参考文献安全检查还是报告生成，再给出可执行且可追溯的回答。关键结论必须连接证据或标注未验证。",
        starters: [
          "帮我规划一个完整的科研任务",
          "整理当前项目记忆和开放问题",
          "从上传材料中提取证据记录",
          "审查工具调用并生成可追溯报告"
        ]
      }
    ]
  },
  {
    id: "paper_assistant",
    title: "论文助手",
    icon: "▤",
    items: [
      {
        id: "paper_summary",
        title: "论文精读",
        icon: "◎",
        skill: "paper_summary",
        purpose: "从上传论文中提取研究问题、方法、结果、局限和待核验信息。",
        template: "请精读我提供的生物医学论文，输出一句话总结、研究背景、核心问题、研究对象或数据来源、方法、主要结果、作者结论、局限性、可引用点和需要人工核验的内容。区分论文原文与推断。"
      },
      {
        id: "idea_discovery",
        title: "Idea 发现",
        icon: "◇",
        skill: "idea_discovery",
        purpose: "从生物医学问题、文献缺口和可用数据中形成可验证的研究 Idea。",
        template: "请围绕我的生物医学研究方向发现可验证的研究 Idea，区分已知事实、研究缺口和假设，并评估创新性、可行性、数据需求、伦理风险和验证路径。"
      },
      {
        id: "literature_review",
        title: "文献综述",
        icon: "⌕",
        skill: "literature_review",
        purpose: "梳理研究现状、证据层级、争议和可复现的文献检索策略。",
        template: "请围绕以下生物医学主题完成文献综述规划，包括核心问题、PICO/PECO、数据库与检索式、证据分层、研究现状、争议、缺口和待核验文献。不要伪造引用。"
      },
      {
        id: "paper_outline",
        title: "论文大纲",
        icon: "☷",
        skill: "paper_outline",
        purpose: "把研究问题、数据和目标组织成完整论文结构。",
        template: "请根据我的研究问题、研究设计和已有结果生成生物医学论文大纲，按 IMRaD 结构列出每节论点、所需证据、图表位置和缺失信息。"
      },
      {
        id: "introduction_draft",
        title: "引言写作",
        icon: "I",
        skill: "introduction_draft",
        purpose: "生成 Introduction / Background 的谨慎初稿。",
        template: "请为以下研究主题生成 Introduction 初稿。所有需要文献支持的位置用 [需要引用] 标注，不要伪造引用。"
      },
      {
        id: "methods_draft",
        title: "方法写作",
        icon: "M",
        skill: "methods_draft",
        purpose: "将真实研究流程整理成可复现的方法部分。",
        template: "请仅依据我提供的真实研究流程撰写 Methods，覆盖研究设计、对象、数据、实验或分析流程、统计方法、软件版本、伦理和可复现性信息；缺失项请标记，不得补造。"
      },
      {
        id: "results_draft",
        title: "结果写作",
        icon: "R",
        skill: "results_draft",
        purpose: "把真实结果组织为客观、与图表一致的 Results。",
        template: "请仅依据我提供的数据、统计结果和图表撰写 Results，按主要终点到次要分析组织，不解释机制，不补造数值，并列出需要核对的数据一致性问题。"
      },
      {
        id: "discussion_draft",
        title: "讨论写作",
        icon: "D",
        skill: "discussion_draft",
        purpose: "基于用户提供的结果撰写 Discussion。",
        template: "请基于我提供的研究结果生成 Discussion 初稿。不要添加未提供的结果，不要从相关性直接推出因果。"
      },
      {
        id: "abstract_title",
        title: "摘要与标题",
        icon: "A",
        skill: "abstract_title",
        purpose: "基于完整论文生成结构化摘要、标题和关键词。",
        template: "请基于我提供的论文内容生成生物医学结构化摘要、候选标题和关键词。所有数字必须来自原文，结论强度必须与研究设计一致。"
      },
      {
        id: "manuscript_polish",
        title: "论文润色",
        icon: "✎",
        skill: "manuscript_polish",
        purpose: "润色中英文生医论文，保留科学含义。",
        template: "请润色下面的学术文本，保持科学含义不变，提高逻辑、清晰度和学术表达，并指出可能的科学表述风险。"
      },
      {
        id: "peer_review",
        title: "论文评审",
        icon: "评",
        skill: "peer_review",
        purpose: "以同行评审视角检查创新性、方法、结果、论证和报告规范。",
        template: "请以严格但建设性的生物医学同行评审者身份审阅我提供的论文或稿件。区分主要问题与次要问题，检查创新性、研究设计、统计方法、结果解释、图表与文本一致性、引用风险、伦理和报告规范，并给出可执行修改建议。不要补造文中不存在的信息。"
      },
      {
        id: "reference_verification",
        title: "参考文献验证",
        icon: "✓",
        skill: "reference_verification",
        purpose: "检查文献是否存在及 DOI、PMID 和元数据一致性。",
        template: "请验证以下参考文献是否真实存在，并检查 DOI、PMID、题名、作者、期刊和年份是否一致。每条参考文献请单独成行。",
        deterministic: "verifyRefs"
      },
      {
        id: "citation_check",
        title: "Claim 证据核验",
        icon: "!",
        skill: "citation_check",
        purpose: "判断论文 Claim 是否需要引用、证据是否匹配以及表述风险。",
        template: "请核验我提供的论文 Claim：判断是否需要引用、需要哪类证据、当前材料是否支持、风险等级和谨慎改写建议。若只有摘要或书目信息，不要声称原文一定支持。"
      }
    ]
  },
  {
    id: "biology_tools",
    title: "生物学工具",
    icon: "⌬",
    items: [
      {
        id: "protein_analysis",
        title: "蛋白质分析",
        icon: "P",
        skill: "protein_analysis",
        purpose: "整理蛋白质序列、UniProt 注释、结构、功能和证据边界。",
        template: "请分析我提供的蛋白质序列、UniProt accession、基因符号或蛋白名称。依次检查输入类型、基础序列特征、蛋白身份、功能、结构域或结构信息、亚细胞定位、同源性线索和证据来源。无法实际查询数据库时必须明确说明，不得伪造 UniProt、PDB 或其他数据库结果。"
      },
      {
        id: "mutation_assessment",
        title: "突变评估",
        icon: "Δ",
        skill: "mutation_assessment",
        purpose: "评估 WT/MT 序列或 HGVS 变异的分子影响与证据等级。",
        template: "请评估我提供的野生型与突变型序列、基因符号或 HGVS 变异。区分可直接计算的序列差异、基于理化性质的推断、数据库注释、文献证据和临床解释。没有 ClinVar、gnomAD、UniProt 或原始文献证据时，不得声称致病或良性。"
      },
      {
        id: "sequence_analysis",
        title: "序列分析",
        icon: "≋",
        skill: "sequence_analysis",
        purpose: "识别 DNA、RNA 或蛋白质序列并规划基础分析。",
        template: "请识别并分析我提供的生物序列，检查序列类型、长度、组成、异常字符、可能的翻译或比对需求，并给出可复现的下一步分析方案。不要声称运行了未实际执行的工具。"
      },
      {
        id: "gene_annotation",
        title: "基因注释",
        icon: "G",
        skill: "gene_annotation",
        purpose: "整理基因身份、功能、表达、疾病和数据库交叉引用。",
        template: "请围绕我提供的基因符号或标识符整理基因身份、物种、主要功能、表达、通路、疾病关联和数据库交叉引用。明确区分已提供证据、需要数据库查询的信息和推断。"
      },
      {
        id: "pathway_analysis",
        title: "通路分析",
        icon: "↗",
        skill: "pathway_analysis",
        purpose: "组织基因集的通路富集思路、背景集和解释风险。",
        template: "请为我提供的基因集设计或审查通路分析，说明背景集、数据库、富集方法、多重检验、方向性、冗余通路处理和验证方案。未提供真实工具输出时不要编造富集结果或 P 值。"
      }
    ]
  }
];

const functions = Object.fromEntries(
  functionGroups.flatMap((group) => group.items.map((item) => [item.id, item]))
);

const starterExamples = {
  idea_discovery: [
    "我的方向是肿瘤相关巨噬细胞与免疫治疗，现有公开单细胞数据。请提出 3 个可验证、不过度宽泛的研究 Idea。",
    "已知现象：IBD 上皮细胞存在状态转换。请从机制缺口、可用数据和验证成本三个角度寻找选题。"
  ],
  literature_review: [
    "请围绕‘肿瘤微环境中乳酸代谢对 CD8+ T 细胞耗竭的影响’设计综述框架和 PubMed 检索式。",
    "主题：单细胞转录组在炎症性肠病中的应用。请梳理证据层级、主要争议、研究缺口和推荐图表。"
  ],
  paper_outline: [
    "研究：回顾性队列评估炎症指标与结直肠癌预后的关系。请按 IMRaD 生成论文大纲并标出每节所需证据。",
    "我有差异表达、通路富集和生存分析结果。请设计结果章节顺序及对应图表位置。"
  ],
  introduction_draft: [
    "请为‘肿瘤相关巨噬细胞影响肺癌免疫治疗响应’写 4 段式 Introduction，缺少引用处标记 [需要引用]。",
    "根据以下研究目的和已核验文献摘要写引言，不要添加摘要之外的机制结论：\n研究目的：\n文献摘要："
  ],
  methods_draft: [
    "请把以下真实流程整理成可复现的 Methods；缺失的软件版本和参数请标记：\n研究设计：\n样本：\n实验/分析流程：\n统计方法：",
    "这是我的单细胞分析记录，请按数据质控、标准化、降维聚类、细胞注释和差异分析撰写方法部分："
  ],
  results_draft: [
    "请仅根据下面的统计表写 Results，不解释机制，并逐项核对样本量、效应值、95% CI 和 P 值：",
    "请根据图 1–4 的说明组织结果章节，先主要终点，再次要分析；没有提供的数字用 [缺失] 标记。"
  ],
  discussion_draft: [
    "主要结果：Marker A 与较差生存相关，但研究为回顾性设计。请写 Discussion，避免把相关性写成因果。",
    "请基于以下结果和 3 篇已核验文献写讨论，包含主要发现、与既往研究比较、可能解释、局限和临床意义："
  ],
  abstract_title: [
    "请根据下面完整稿件生成 250 词结构式摘要、5 个候选标题和 5 个关键词；所有数字必须来自原文。",
    "请为这项观察性队列研究生成中英文标题，避免使用‘预测’‘机制’等超出研究设计的词。"
  ],
  manuscript_polish: [
    "请润色下面英文段落，保持数值和科学含义不变，并用列表说明每类修改：\nThe expression of Gene X was obviously higher...",
    "请把下面中文结果段落改为简洁的学术表达，同时标出因果过度、绝对化或证据不足的句子："
  ],
  peer_review: [
    "请按期刊同行评审格式审阅下面稿件，先给总体评价，再列 Major Comments、Minor Comments 和优先修改清单。",
    "请重点评审这项回顾性临床研究的方法与统计：纳排标准、混杂控制、缺失值、多重比较和结论强度。"
  ],
  reference_verification: [
    "请核验下面每条参考文献的 DOI、PMID、题名、期刊和年份是否一致：\n1. ...\n2. ...",
    "我上传了一份 BibTeX。请找出元数据不一致、无法验证和疑似虚构的条目，并给出人工核验清单。"
  ],
  citation_check: [
    "Claim：Gene X promotes tumor progression and is a therapeutic target. 请判断需要什么证据，并给出谨慎改写。",
    "请逐句检查下面讨论段落：哪些句子需要引用、当前文献是否可能支持、风险等级是什么。"
  ],
  protein_analysis: [
    "请分析 UniProt accession P38398：整理蛋白身份、功能、结构域、定位、结构证据和需要数据库核验的项目。",
    "请分析以下蛋白质 FASTA 序列。先检查长度和异常字符，再提出 UniProt、InterPro、BLAST 和结构分析步骤：\n>protein_1\nMKWVTFISLLFLFSSAYSR..."
  ],
  mutation_assessment: [
    "请评估 TP53 p.R175H。区分氨基酸性质变化、蛋白结构推断、数据库证据、文献证据和临床解释。",
    "请比较以下 WT/MT 蛋白序列，列出差异位置及性质变化；不要仅凭性质变化判断致病性：\nWT: ...\nMT: ..."
  ],
  sequence_analysis: [
    "请判断下面序列是 DNA、RNA 还是蛋白质，检查异常字符，并给出下一步分析方案：\n>seq1\nATGCGT...",
    "我上传了一份 FASTA，请检查序列数量、命名、长度分布和是否适合做多序列比对。"
  ],
  gene_annotation: [
    "请整理人类基因 TP53 的标准名称、主要功能、通路、表达、疾病关联及推荐核验数据库。",
    "基因符号：CXCL8，物种：Homo sapiens。请列出注释工作流，并区分已知事实与待查询信息。"
  ],
  pathway_analysis: [
    "我有一组人类上调基因。请设计 GO/Reactome 富集方案，包括背景集、多重检验和冗余通路处理。",
    "请审查下面的通路富集结果，检查 P 值校正、基因重叠、方向性和结论是否过度："
  ]
};

for (const [id, starters] of Object.entries(starterExamples)) {
  if (functions[id]) functions[id].starters = starters;
}

const DEFAULT_PAPER_AGENT_IDS = [
  "paper_summary",
  "literature_review",
  "manuscript_polish",
  "peer_review",
  "reference_verification"
];
const REQUIRED_PAPER_AGENT_IDS = new Set(["peer_review", "reference_verification"]);
const DEFAULT_BIOLOGY_TOOL_IDS = ["protein_analysis", "mutation_assessment"];

function savedPaperAgentIds() {
  try {
    const saved = JSON.parse(localStorage.getItem("rosalind.paperAgents") || "null");
    if (!Array.isArray(saved)) return [...DEFAULT_PAPER_AGENT_IDS];
    const valid = saved.filter((id) => functions[id] && id !== "research_assistant");
    for (const id of REQUIRED_PAPER_AGENT_IDS) {
      if (!valid.includes(id)) valid.push(id);
    }
    return [...new Set(valid)];
  } catch {
    return [...DEFAULT_PAPER_AGENT_IDS];
  }
}

function savedBiologyToolIds() {
  try {
    const saved = JSON.parse(localStorage.getItem("rosalind.biologyTools") || "null");
    if (!Array.isArray(saved)) return [...DEFAULT_BIOLOGY_TOOL_IDS];
    return [...new Set(saved.filter((id) => functions[id]))];
  } catch {
    return [...DEFAULT_BIOLOGY_TOOL_IDS];
  }
}

const state = {
  functionId: "research_assistant",
  chats: [],
  activeChatId: "",
  user: null,
  isSending: false,
  uploaded: null,
  authMode: "login",
  paperAgentIds: savedPaperAgentIds(),
  biologyToolIds: savedBiologyToolIds(),
  managingGroupId: "paper_assistant",
  projectId: "",
  projects: [],
  desktopMode: false,
  containerCapability: null,
  projectDirectoryAuthorization: null,
  projectFiles: [],
  projectFilesProjectId: "",
  projectFileAgentJobId: "",
  providerProfileId: "",
  desktopConversationIds: {},
  desktopChatStorageAvailable: false,
  desktopChatPersistenceError: ""
};

const agentPlanPolls = new Map();
let containerCapabilityRefreshTimer = null;
let containerCapabilityRefreshInFlight = null;
let chatPersistenceChain = Promise.resolve();

const els = {
  authScreen: document.getElementById("authScreen"),
  authForm: document.getElementById("authForm"),
  loginMode: document.getElementById("loginMode"),
  registerMode: document.getElementById("registerMode"),
  authEmail: document.getElementById("authEmail"),
  authPassword: document.getElementById("authPassword"),
  authError: document.getElementById("authError"),
  authSubmit: document.getElementById("authSubmit"),
  appShell: document.getElementById("appShell"),
  newChat: document.getElementById("newChat"),
  chatHistory: document.getElementById("chatHistory"),
  sidebarAccount: document.getElementById("sidebarAccount"),
  accountAvatar: document.getElementById("accountAvatar"),
  accountMenu: document.getElementById("accountMenu"),
  currentUser: document.getElementById("currentUser"),
  logout: document.getElementById("logout"),
  projectSelect: document.getElementById("projectSelect"),
  newProject: document.getElementById("newProject"),
  openProject: document.getElementById("openProject"),
  projectDialog: document.getElementById("projectDialog"),
  projectDialogTitle: document.getElementById("projectDialogTitle"),
  projectDirectorySection: document.getElementById("projectDirectorySection"),
  projectDirectoryStatus: document.getElementById("projectDirectoryStatus"),
  projectDirectoryPath: document.getElementById("projectDirectoryPath"),
  authorizeProjectDirectory: document.getElementById("authorizeProjectDirectory"),
  revealProjectDirectory: document.getElementById("revealProjectDirectory"),
  scanProjectFiles: document.getElementById("scanProjectFiles"),
  revokeProjectDirectory: document.getElementById("revokeProjectDirectory"),
  projectFilesSection: document.getElementById("projectFilesSection"),
  projectFilesStatus: document.getElementById("projectFilesStatus"),
  projectFileList: document.getElementById("projectFileList"),
  memoryCategory: document.getElementById("memoryCategory"),
  memoryContent: document.getElementById("memoryContent"),
  addMemory: document.getElementById("addMemory"),
  memoryList: document.getElementById("memoryList"),
  projectPlanList: document.getElementById("projectPlanList"),
  desktopRuntime: document.getElementById("desktopRuntime"),
  detailPanel: document.getElementById("detailPanel"),
  detailPanelEyebrow: document.getElementById("detailPanelEyebrow"),
  detailPanelTitle: document.getElementById("detailPanelTitle"),
  detailPanelContent: document.getElementById("detailPanelContent"),
  detailPanelNote: document.getElementById("detailPanelNote"),
  closeDetailPanel: document.getElementById("closeDetailPanel"),
  skillList: document.getElementById("skillList"),
  selectedSkill: document.getElementById("selectedSkill"),
  activePurpose: document.getElementById("activePurpose"),
  conversation: document.getElementById("conversation"),
  taskInput: document.getElementById("taskInput"),
  sendButton: document.getElementById("sendButton"),
  modeBadge: document.getElementById("modeBadge"),
  copyOutput: document.getElementById("copyOutput"),
  clearChat: document.getElementById("clearChat"),
  openSettings: document.getElementById("openSettings"),
  settingsDialog: document.getElementById("settingsDialog"),
  providerStorageNote: document.getElementById("providerStorageNote"),
  agentDialog: document.getElementById("agentDialog"),
  agentDialogTitle: document.getElementById("agentDialogTitle"),
  agentDialogDescription: document.getElementById("agentDialogDescription"),
  agentChoices: document.getElementById("agentChoices"),
  resetAgents: document.getElementById("resetAgents"),
  baseUrl: document.getElementById("baseUrl"),
  model: document.getElementById("model"),
  apiKey: document.getElementById("apiKey"),
  keyStatus: document.getElementById("keyStatus"),
  clearProviderKey: document.getElementById("clearProviderKey"),
  temperature: document.getElementById("temperature"),
  temperatureValue: document.getElementById("temperatureValue"),
  documentFile: document.getElementById("documentFile"),
  uploadStatus: document.getElementById("uploadStatus"),
  attachmentChip: document.getElementById("attachmentChip"),
  attachmentName: document.getElementById("attachmentName"),
  attachmentMeta: document.getElementById("attachmentMeta"),
  removeAttachment: document.getElementById("removeAttachment")
};

function setAuthMode(mode) {
  state.authMode = mode;
  const registering = mode === "register";
  els.loginMode.classList.toggle("active", !registering);
  els.registerMode.classList.toggle("active", registering);
  els.authSubmit.textContent = registering ? "创建账户" : "登录";
  els.authPassword.autocomplete = registering ? "new-password" : "current-password";
  els.authError.textContent = "";
}

function showAuth(message = "") {
  els.appShell.hidden = true;
  els.authScreen.hidden = false;
  els.authError.textContent = message;
  els.authPassword.value = "";
  els.authEmail.focus();
}

async function showApp(user) {
  els.authScreen.hidden = true;
  els.appShell.hidden = false;
  state.user = user;
  els.currentUser.textContent = user.email;
  els.accountAvatar.textContent = (user.email || "U").trim().slice(0, 1).toUpperCase();
  await loadConfig();
  await loadChats(user);
  drawSignal();
  renderFunctions();
  selectFunction(state.functionId);
  await loadProjects();
  await hydrateCompletedAgentArtifacts();
  resumeAgentPlanPolling();
}

async function checkAuth() {
  const response = await fetch("/api/auth/me");
  if (!response.ok) return showAuth();
  const data = await response.json();
  await showApp(data.user);
}

async function submitAuth(event) {
  event.preventDefault();
  els.authSubmit.disabled = true;
  els.authError.textContent = "";
  try {
    const response = await fetch(`/api/auth/${state.authMode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: els.authEmail.value.trim(), password: els.authPassword.value })
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "账户操作失败。");
    await showApp(data.user);
  } catch (error) {
    els.authError.textContent = String(error.message || error);
  } finally {
    els.authSubmit.disabled = false;
  }
}

async function logout() {
  await fetch("/api/auth/logout", { method: "POST" });
  persistChats();
  await flushChatPersistence();
  state.chats = [];
  state.activeChatId = "";
  state.user = null;
  state.desktopChatStorageAvailable = false;
  closeAccountMenu();
  clearAttachment();
  showAuth();
}

async function authenticatedFetch(url, options = {}) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    showAuth("会话已过期，请重新登录。");
    throw new Error("会话已过期，请重新登录。");
  }
  return response;
}

async function agentRequest(url, options = {}) {
  const response = await authenticatedFetch(url, options);
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || "Agent 请求失败。");
  return data;
}

async function loadProjects() {
  const data = await agentRequest("/api/projects");
  state.projects = data.projects || [];
  if (!state.projects.length) {
    const created = await agentRequest("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "我的研究项目", description: "由 Rosalind Agent 创建的默认项目" })
    });
    state.projects = [created.project];
  }
  if (!state.projects.some((project) => project.id === state.projectId)) state.projectId = state.projects[0].id;
  els.projectSelect.innerHTML = "";
  for (const project of state.projects) {
    const option = document.createElement("option");
    option.value = project.id;
    option.textContent = project.name;
    option.selected = project.id === state.projectId;
    els.projectSelect.appendChild(option);
  }
}

async function createProjectFromUi() {
  const name = window.prompt("请输入科研项目名称：", "新研究项目");
  if (!name?.trim()) return;
  try {
    const data = await agentRequest("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() })
    });
    state.projectId = data.project.id;
    await loadProjects();
    setBadge("project ready");
  } catch (error) {
    setBadge("error", "error");
    window.alert(String(error.message || error));
  }
}

function renderProjectDirectoryAuthorization(authorization) {
  const previous = state.projectDirectoryAuthorization;
  state.projectDirectoryAuthorization = authorization || null;
  els.projectDirectorySection.hidden = !state.desktopMode;
  if (!state.desktopMode) return;
  if (!authorization) {
    resetProjectFiles();
    els.projectDirectoryStatus.textContent = "尚未授权目录。Agent 和工具无法访问你的其他文件。";
    els.projectDirectoryPath.textContent = "";
    els.projectDirectoryPath.hidden = true;
    els.authorizeProjectDirectory.textContent = "选择文件夹";
    els.revealProjectDirectory.hidden = true;
    els.scanProjectFiles.hidden = true;
    els.revokeProjectDirectory.hidden = true;
    return;
  }
  if (previous?.projectId !== authorization.projectId || previous?.displayPath !== authorization.displayPath) {
    resetProjectFiles(authorization.projectId);
  }
  els.projectDirectoryStatus.textContent = authorization.available
    ? `已授权${authorization.write ? "读取和写入" : "只读访问"}。只有此目录可作为当前项目的本地工作区。`
    : "原授权目录当前不可用，请重新选择文件夹或撤销授权。";
  els.projectDirectoryPath.textContent = authorization.displayPath;
  els.projectDirectoryPath.hidden = false;
  els.authorizeProjectDirectory.textContent = "更换文件夹";
  els.revealProjectDirectory.hidden = !authorization.available;
  els.scanProjectFiles.hidden = !authorization.available;
  els.revokeProjectDirectory.hidden = false;
  els.projectFilesSection.hidden = false;
}

function resetProjectFiles(projectId = "") {
  state.projectFiles = [];
  state.projectFilesProjectId = projectId;
  state.projectFileAgentJobId = "";
  els.projectFilesSection.hidden = !projectId;
  els.projectFilesStatus.textContent = "点击“扫描项目文件”读取安全文件清单。";
  els.projectFileList.innerHTML = "";
}

function renderProjectFiles(files, truncated = false) {
  state.projectFiles = Array.isArray(files) ? files : [];
  els.projectFilesSection.hidden = false;
  els.projectFilesStatus.textContent = state.projectFiles.length
    ? `已发现 ${state.projectFiles.length} 个非敏感文件${truncated ? "，结果已达到安全上限" : ""}。`
    : "授权目录中没有可展示的非敏感文件。";
  els.projectFileList.innerHTML = "";
  for (const file of state.projectFiles) {
    const article = document.createElement("article");
    const copy = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = file.path;
    const meta = document.createElement("small");
    meta.textContent = `${formatFileSize(file.sizeBytes)} · ${file.readable ? "可预览文本" : "文件"}`;
    copy.append(title, meta);
    article.appendChild(copy);
    if (file.readable) {
      const preview = document.createElement("button");
      preview.type = "button";
      preview.textContent = "预览";
      preview.addEventListener("click", () => previewProjectFile(file.path, article, preview));
      article.appendChild(preview);
    }
    els.projectFileList.appendChild(article);
  }
}

async function scanProjectFiles() {
  if (!state.desktopMode || !state.projectId || !state.projectDirectoryAuthorization?.available) return;
  els.scanProjectFiles.disabled = true;
  els.projectFilesStatus.textContent = "正在通过 Desktop Core 扫描授权目录…";
  try {
    const agentJobId = await desktopToolHostJob();
    const toolRun = await desktopInvoke("desktop_run_low_risk_tool", {
      agentJobId,
      toolName: "project.files.list",
      input: {}
    });
    if (toolRun.status !== "succeeded") throw new Error(toolRun.output?.error || `ToolRun ${toolRun.status}`);
    state.projectFileAgentJobId = agentJobId;
    state.projectFilesProjectId = state.projectId;
    renderProjectFiles(toolRun.output?.files, Boolean(toolRun.output?.truncated));
    setBadge("project files ready");
  } catch (error) {
    els.projectFilesStatus.textContent = `扫描失败：${String(error.message || error)}`;
    setBadge("error", "error");
  } finally {
    els.scanProjectFiles.disabled = false;
  }
}

async function previewProjectFile(path, article, button) {
  if (!state.projectFileAgentJobId || state.projectFilesProjectId !== state.projectId) return;
  button.disabled = true;
  button.textContent = "读取中";
  try {
    const toolRun = await desktopInvoke("desktop_run_low_risk_tool", {
      agentJobId: state.projectFileAgentJobId,
      toolName: "project.file.read",
      input: { path }
    });
    if (toolRun.status !== "succeeded") throw new Error(toolRun.output?.error || `ToolRun ${toolRun.status}`);
    let preview = article.querySelector("pre");
    if (!preview) {
      preview = document.createElement("pre");
      article.appendChild(preview);
    }
    preview.textContent = `${toolRun.output?.content || ""}${toolRun.output?.truncated ? "\n\n[预览已截断]" : ""}`;
    button.textContent = "刷新预览";
  } catch (error) {
    button.textContent = "预览失败";
    button.title = String(error.message || error);
  } finally {
    button.disabled = false;
  }
}

async function loadProjectDirectoryAuthorization() {
  if (!state.desktopMode || !state.projectId) {
    renderProjectDirectoryAuthorization(null);
    return null;
  }
  const authorization = await desktopInvoke("desktop_get_project_directory_authorization", {
    projectId: state.projectId
  });
  renderProjectDirectoryAuthorization(authorization);
  return authorization;
}

async function authorizeProjectDirectory() {
  if (!state.desktopMode || !state.projectId) return;
  els.authorizeProjectDirectory.disabled = true;
  try {
    const authorization = await desktopInvoke("desktop_authorize_project_directory", {
      projectId: state.projectId
    });
    if (authorization) {
      renderProjectDirectoryAuthorization(authorization);
      setBadge("project directory ready");
    }
  } catch (error) {
    setBadge("error", "error");
    window.alert(String(error.message || error));
  } finally {
    els.authorizeProjectDirectory.disabled = false;
  }
}

async function revealProjectDirectory() {
  if (!state.desktopMode || !state.projectId) return;
  try {
    await desktopInvoke("desktop_reveal_project_directory", { projectId: state.projectId });
  } catch (error) {
    window.alert(String(error.message || error));
    await loadProjectDirectoryAuthorization();
  }
}

async function revokeProjectDirectory() {
  if (!state.desktopMode || !state.projectId) return;
  const approved = await confirmDesktopAction(
    "撤销后，Agent 和工具将无法继续访问这个目录。目录及其中的文件不会被删除。",
    { title: "撤销项目目录授权" }
  );
  if (!approved) return;
  await desktopInvoke("desktop_revoke_project_directory", { projectId: state.projectId });
  renderProjectDirectoryAuthorization(null);
  setBadge("project directory revoked");
}

async function loadProjectDialog() {
  if (!state.projectId) return;
  const [data] = await Promise.all([
    agentRequest(`/api/projects/${state.projectId}/workspace`),
    loadProjectDirectoryAuthorization()
  ]);
  els.projectDialogTitle.textContent = data.project.name;
  els.memoryList.innerHTML = "";
  if (!data.memory.length) els.memoryList.textContent = "暂无项目记忆。";
  for (const memory of data.memory) {
    const article = document.createElement("article");
    const meta = document.createElement("strong");
    meta.textContent = `${memory.category} · ${memory.sourceType}`;
    const content = document.createElement("p");
    content.textContent = memory.content;
    article.append(meta, content);
    els.memoryList.appendChild(article);
  }
  els.projectPlanList.innerHTML = "";
  if (!data.plans.length) els.projectPlanList.textContent = "暂无任务计划。";
  for (const plan of data.plans) {
    const article = document.createElement("article");
    const title = document.createElement("strong");
    title.textContent = `${plan.status} · ${plan.steps.filter((step) => step.status === "completed").length}/${plan.steps.length} 步完成`;
    const goal = document.createElement("p");
    goal.textContent = plan.goal;
    article.append(title, goal);
    els.projectPlanList.appendChild(article);
  }
}

async function openProjectDialog() {
  try {
    await loadProjectDialog();
    els.projectDialog.showModal();
  } catch (error) {
    window.alert(String(error.message || error));
  }
}

async function addProjectMemory() {
  const content = els.memoryContent.value.trim();
  if (!content || !state.projectId) return;
  els.addMemory.disabled = true;
  try {
    await agentRequest(`/api/projects/${state.projectId}/memory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: els.memoryCategory.value, content })
    });
    els.memoryContent.value = "";
    await loadProjectDialog();
  } finally {
    els.addMemory.disabled = false;
  }
}

function currentFunction() {
  return functions[state.functionId] || functions.research_assistant;
}

function makeChatId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `chat-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function makeMessageId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `message-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function parseLegacyAgentResult(content) {
  const source = String(content || "");
  if (!source.trimStart().startsWith("# Agent 执行结果")) return null;
  const headings = [...source.matchAll(/^##\s+(\d+)\.\s+(.+)$/gm)].filter((match) => {
    const following = source.slice(match.index + match[0].length, match.index + match[0].length + 180);
    return /^\s*状态：[^\n]+·\s*尝试次数：\d+/m.test(following);
  });
  if (!headings.length) return null;
  const process = headings.map((match, index) => {
    const end = headings[index + 1]?.index ?? source.search(/^---$/m);
    const sectionEnd = end > match.index ? end : source.length;
    const section = source.slice(match.index + match[0].length, sectionEnd).trim();
    const status = section.match(/^状态：([^·\n]+)\s*·\s*尝试次数：(\d+)/m);
    const output = section.replace(/^状态：[^\n]+\n*/m, "").trim();
    return {
      position: Number(match[1]),
      title: match[2].trim(),
      skill: "",
      status: status?.[1]?.trim() || "completed",
      attempts: Number(status?.[2] || 0),
      output,
      error: ""
    };
  });
  const finalOutput = process.at(-1)?.output || "Agent 任务已完成。";
  return { content: finalOutput, process };
}

function normalizeMessage(message) {
  const normalized = message && typeof message === "object" ? message : {};
  normalized.id = typeof normalized.id === "string" && normalized.id ? normalized.id : makeMessageId();
  normalized.role = normalized.role === "assistant" ? "assistant" : "user";
  normalized.content = String(normalized.content || "");
  if (normalized.role === "assistant") {
    const legacyResult = !Array.isArray(normalized.agentProcess) ? parseLegacyAgentResult(normalized.content) : null;
    if (legacyResult) {
      normalized.content = legacyResult.content;
      normalized.agentProcess = legacyResult.process;
    }
    normalized.sources = Array.isArray(normalized.sources) ? normalized.sources : [];
    normalized.trace = Array.isArray(normalized.trace) ? normalized.trace : [];
    normalized.agentProcess = Array.isArray(normalized.agentProcess) ? normalized.agentProcess.map((step, index) => ({
      position: Number(step?.position || index + 1),
      title: String(step?.title || `步骤 ${index + 1}`),
      skill: String(step?.skill || ""),
      status: String(step?.status || "unknown"),
      attempts: Number(step?.attempts || 0),
      instruction: String(step?.instruction || ""),
      output: String(step?.output || ""),
      error: String(step?.error || ""),
      confidence: Math.max(0, Math.min(100, Number(step?.confidence ?? (String(step?.status || "") === "completed" ? 72 : 40))))
    })) : [];
    normalized.artifacts = Array.isArray(normalized.artifacts) ? normalized.artifacts.map((artifact) => ({
      name: String(artifact?.name || artifact?.path || "产物文件"),
      path: String(artifact?.path || ""),
      size: Number(artifact?.size || 0),
      mime: String(artifact?.mime || "application/octet-stream"),
      modifiedAt: String(artifact?.modifiedAt || ""),
      url: String(artifact?.url || "")
    })).filter((artifact) => artifact.path && artifact.url) : [];
    normalized.toolArtifacts = Array.isArray(normalized.toolArtifacts) ? normalized.toolArtifacts.map((artifact) => ({
      artifactId: String(artifact?.artifactId || artifact?.id || ""),
      name: String(artifact?.name || artifact?.path || "ToolRun 产物"),
      size: Number(artifact?.size ?? artifact?.sizeBytes ?? 0),
      sha256: String(artifact?.sha256 || ""),
      kind: String(artifact?.kind || "file")
    })).filter((artifact) => artifact.artifactId && artifact.name) : [];
    normalized.feedback = ["like", "dislike"].includes(normalized.feedback) ? normalized.feedback : "none";
    normalized.agentJobId = String(normalized.agentJobId || "");
    if (!normalized.agentPlan && normalized.content.includes("任务已提交后台执行")) {
      const legacyJobId = normalized.content.match(/任务 ID：?\s*`?([a-f0-9]{32})`?/i)?.[1] || "";
      if (legacyJobId) normalized.agentPlan = { planId: "", status: "submitted", jobId: legacyJobId, error: "" };
    }
    if (normalized.agentPlan && typeof normalized.agentPlan === "object") {
      normalized.agentPlan = {
        planId: String(normalized.agentPlan.planId || ""),
        status: ["pending", "starting", "running", "submitted", "completed", "failed", "cancelled"].includes(normalized.agentPlan.status)
          ? normalized.agentPlan.status
          : "pending",
        jobId: String(normalized.agentPlan.jobId || ""),
        error: String(normalized.agentPlan.error || ""),
        resultMessageId: String(normalized.agentPlan.resultMessageId || ""),
        projectId: String(normalized.agentPlan.projectId || "")
      };
    }
  }
  return normalized;
}

function addSessionMessage(role, content, extras = {}) {
  const message = normalizeMessage({ id: makeMessageId(), role, content, ...extras });
  currentSession().push(message);
  return message;
}

function chatOwnerId(user = state.user) {
  const identity = user?.id || user?.email || "anonymous";
  return String(identity).trim().toLowerCase();
}

function chatStorageKey(user = state.user) {
  return `rosalind.chats.${encodeURIComponent(chatOwnerId(user))}`;
}

function createChat(functionId = state.functionId, shouldRender = true) {
  const now = new Date().toISOString();
  const chat = {
    id: makeChatId(),
    functionId: functions[functionId] ? functionId : "research_assistant",
    title: "新对话",
    messages: [],
    createdAt: now,
    updatedAt: now
  };
  state.chats.unshift(chat);
  state.activeChatId = chat.id;
  state.functionId = chat.functionId;
  persistChats();
  if (shouldRender) {
    renderChatHistory();
    selectFunction(chat.functionId, { updateChat: false });
  }
  return chat;
}

function activeChat() {
  let chat = state.chats.find((item) => item.id === state.activeChatId);
  if (!chat) chat = createChat(state.functionId, false);
  return chat;
}

function normalizeChatState(saved) {
  const savedChats = Array.isArray(saved) ? saved : saved?.chats;
  if (!Array.isArray(savedChats)) return { activeChatId: "", chats: [] };
  let chats = savedChats.slice(0, 100).filter((chat) => chat && typeof chat.id === "string").map((chat) => ({
    id: chat.id,
    functionId: functions[chat.functionId] ? chat.functionId : "research_assistant",
    title: typeof chat.title === "string" && chat.title.trim() ? chat.title.trim().slice(0, 60) : "新对话",
    messages: Array.isArray(chat.messages) ? chat.messages.map(normalizeMessage) : [],
    createdAt: chat.createdAt || new Date().toISOString(),
    updatedAt: chat.updatedAt || chat.createdAt || new Date().toISOString()
  }));
  const savedActiveId = chats.some((chat) => chat.id === saved?.activeChatId)
    ? saved.activeChatId
    : chats[0]?.id || "";
  const activeIsEmpty = chats.find((chat) => chat.id === savedActiveId)?.messages.length === 0;
  const emptyChatId = activeIsEmpty
    ? savedActiveId
    : chats.find((chat) => chat.messages.length === 0)?.id;
  chats = chats.filter((chat) => chat.messages.length > 0 || chat.id === emptyChatId);
  return {
    chats,
    activeChatId: chats.some((chat) => chat.id === savedActiveId) ? savedActiveId : chats[0]?.id || ""
  };
}

async function loadChats(user) {
  state.chats = [];
  state.activeChatId = "";
  state.desktopChatStorageAvailable = false;
  state.desktopChatPersistenceError = "";
  let localState = { activeChatId: "", chats: [] };
  try {
    localState = normalizeChatState(JSON.parse(localStorage.getItem(chatStorageKey(user)) || "null"));
  } catch {
    localState = { activeChatId: "", chats: [] };
  }

  let loadedState = localState;
  let shouldWriteDesktopState = false;
  if (state.desktopMode) {
    try {
      const desktopState = normalizeChatState(await desktopInvoke("desktop_load_ui_chat_state", {
        ownerId: chatOwnerId(user)
      }));
      state.desktopChatStorageAvailable = true;
      if (desktopState.chats.length) {
        loadedState = desktopState;
      } else {
        shouldWriteDesktopState = true;
      }
    } catch (error) {
      state.desktopChatPersistenceError = String(error.message || error);
      console.error("Unable to load Desktop Core chat state", error);
    }
  }

  state.chats = loadedState.chats;
  state.activeChatId = loadedState.activeChatId;
  if (!state.chats.length) {
    createChat("research_assistant", false);
    shouldWriteDesktopState = state.desktopChatStorageAvailable;
  }
  state.functionId = activeChat().functionId;
  if (shouldWriteDesktopState) {
    persistChats();
    await flushChatPersistence();
  }
  renderChatHistory();
}

function persistChats() {
  if (!state.user) return;
  const snapshot = {
    activeChatId: state.activeChatId,
    chats: state.chats.slice(0, 100)
  };
  try {
    localStorage.setItem(chatStorageKey(), JSON.stringify(snapshot));
  } catch {
    // A full or unavailable localStorage must not block the chat UI.
  }
  if (!state.desktopMode || !state.desktopChatStorageAvailable) return;
  let desktopSnapshot;
  try {
    desktopSnapshot = JSON.parse(JSON.stringify(snapshot));
  } catch (error) {
    state.desktopChatPersistenceError = String(error.message || error);
    return;
  }
  const ownerId = chatOwnerId();
  chatPersistenceChain = chatPersistenceChain
    .catch(() => {})
    .then(() => desktopInvoke("desktop_replace_ui_chat_state", {
      ownerId,
      activeChatId: desktopSnapshot.activeChatId,
      chats: desktopSnapshot.chats
    }))
    .then(() => {
      state.desktopChatPersistenceError = "";
    })
    .catch((error) => {
      state.desktopChatPersistenceError = String(error.message || error);
      console.error("Unable to persist Desktop Core chat state", error);
    });
}

async function flushChatPersistence() {
  await chatPersistenceChain.catch(() => {});
}

function chatTimeLabel(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" });
}

function renderChatHistory() {
  els.chatHistory.innerHTML = "";
  if (!state.chats.length) {
    const empty = document.createElement("p");
    empty.className = "chat-history-empty";
    empty.textContent = "还没有历史对话";
    els.chatHistory.appendChild(empty);
    return;
  }
  const chats = [...state.chats].sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
  for (const chat of chats) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chat-history-item";
    button.disabled = state.isSending;
    button.classList.toggle("active", chat.id === state.activeChatId);
    const title = document.createElement("span");
    title.className = "chat-history-title";
    title.textContent = chat.title || "新对话";
    const meta = document.createElement("span");
    meta.className = "chat-history-meta";
    const functionTitle = chat.functionId === "research_assistant"
      ? "主对话"
      : functions[chat.functionId]?.title || "主对话";
    meta.textContent = `${functionTitle} · ${chatTimeLabel(chat.updatedAt)}`;
    button.append(title, meta);
    button.addEventListener("click", () => switchChat(chat.id));
    els.chatHistory.appendChild(button);
  }
}

function switchChat(chatId) {
  const chat = state.chats.find((item) => item.id === chatId);
  if (!chat) return;
  state.activeChatId = chat.id;
  state.functionId = chat.functionId;
  closeDetailPanel();
  clearAttachment();
  persistChats();
  renderChatHistory();
  selectFunction(chat.functionId, { updateChat: false });
}

function prepareActiveChatForMessage(input) {
  const chat = activeChat();
  if (chat.title === "新对话" && input.trim()) {
    chat.title = input.trim().replace(/\s+/g, " ").slice(0, 28);
  }
  chat.updatedAt = new Date().toISOString();
  chat.functionId = state.functionId;
  persistChats();
  renderChatHistory();
  if (state.functionId === "research_assistant") els.selectedSkill.textContent = chat.title;
}

function currentSession() {
  return activeChat().messages;
}

function drawSignal(canvasId = "signalCanvas") {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#0f766e";
  ctx.lineWidth = 2;
  for (let row = 0; row < 3; row += 1) {
    ctx.beginPath();
    for (let x = 0; x < canvas.width; x += 1) {
      const y = 9 + row * 11 + Math.sin((x + row * 10) / 7) * 4;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
}

function setBadge(text, type = "") {
  els.modeBadge.textContent = text;
  els.modeBadge.className = `status-badge ${type}`.trim();
}

function setAgentExecutionLock(locked) {
  state.isSending = locked;
  els.taskInput.disabled = locked;
  els.sendButton.disabled = locked;
  els.newChat.disabled = locked;
  document.querySelectorAll(".chat-history-item, .function-item, .standalone-function, .manage-agents").forEach((button) => {
    button.disabled = locked;
  });
  if (!locked) {
    renderChatHistory();
    els.taskInput.focus();
  }
}

function setUploadStatus(text, type = "") {
  els.uploadStatus.textContent = text;
  els.uploadStatus.className = `hint ${type}`.trim();
}

function renderFunctions() {
  els.skillList.innerHTML = "";
  for (const group of functionGroups) {
    if (group.standalone) continue;
    const section = document.createElement("section");
    section.className = "function-group";

    const groupHeader = document.createElement("div");
    groupHeader.className = "function-group-header";
    const heading = document.createElement("h2");
    const groupIcon = document.createElement("span");
    groupIcon.className = "group-icon";
    groupIcon.textContent = group.icon;
    const groupTitle = document.createElement("span");
    groupTitle.textContent = group.title;
    heading.append(groupIcon, groupTitle);
    groupHeader.appendChild(heading);
    if (["paper_assistant", "biology_tools"].includes(group.id)) {
      const manage = document.createElement("button");
      manage.type = "button";
      manage.className = "manage-agents";
      manage.disabled = state.isSending;
      manage.textContent = "+ 添加";
      manage.addEventListener("click", () => openAgentManager(group.id));
      groupHeader.appendChild(manage);
    }
    section.appendChild(groupHeader);

    const list = document.createElement("div");
    list.className = "function-list";
    let visibleItems = group.items;
    if (group.id === "paper_assistant") {
      visibleItems = group.items.filter((item) => state.paperAgentIds.includes(item.id));
    } else if (group.id === "biology_tools") {
      visibleItems = group.items.filter((item) => state.biologyToolIds.includes(item.id));
    }
    for (const item of visibleItems) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "function-item";
      button.disabled = state.isSending;
      button.dataset.functionId = item.id;
      const icon = document.createElement("span");
      icon.className = "function-icon";
      icon.textContent = item.icon;
      const title = document.createElement("span");
      title.className = "function-title";
      title.textContent = item.title;
      button.append(icon, title);
      button.addEventListener("click", () => chooseFunction(item.id));
      list.appendChild(button);
    }
    section.appendChild(list);
    els.skillList.appendChild(section);
  }
}

function renderAgentChoices() {
  els.agentChoices.innerHTML = "";
  const group = functionGroups.find((item) => item.id === state.managingGroupId);
  const selectedIds = state.managingGroupId === "paper_assistant" ? state.paperAgentIds : state.biologyToolIds;
  const requiredIds = state.managingGroupId === "paper_assistant" ? REQUIRED_PAPER_AGENT_IDS : new Set();
  els.agentDialogTitle.textContent = state.managingGroupId === "paper_assistant" ? "管理论文助手" : "管理生物学工具";
  els.agentDialogDescription.textContent = state.managingGroupId === "paper_assistant"
    ? "每个入口对应一个 Skill；论文评审和参考文献验证为必选。"
    : "每个入口对应一个独立 Skill，可按研究需要添加或移除。";
  for (const item of group.items) {
    const label = document.createElement("label");
    label.className = "agent-choice";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = item.id;
    checkbox.checked = selectedIds.includes(item.id);
    checkbox.disabled = requiredIds.has(item.id);
    const text = document.createElement("span");
    text.innerHTML = `<strong>${item.title}</strong><small>${item.purpose}</small>`;
    label.append(checkbox, text);
    els.agentChoices.appendChild(label);
  }
}

function openAgentManager(groupId) {
  state.managingGroupId = groupId;
  renderAgentChoices();
  els.agentDialog.showModal();
}

function saveAgentChoices() {
  const selected = [...els.agentChoices.querySelectorAll('input[type="checkbox"]:checked')]
    .map((input) => input.value);
  if (state.managingGroupId === "paper_assistant") {
    for (const id of REQUIRED_PAPER_AGENT_IDS) {
      if (!selected.includes(id)) selected.push(id);
    }
    state.paperAgentIds = selected;
    localStorage.setItem("rosalind.paperAgents", JSON.stringify(selected));
  } else {
    state.biologyToolIds = selected;
    localStorage.setItem("rosalind.biologyTools", JSON.stringify(selected));
  }
  const managedIds = new Set(functionGroups.find((group) => group.id === state.managingGroupId).items.map((item) => item.id));
  if (managedIds.has(state.functionId) && !selected.includes(state.functionId)) {
    state.functionId = "research_assistant";
  }
  renderFunctions();
  chooseFunction(state.functionId);
}

function sourceProvider(url) {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    if (host.includes("pubmed.ncbi.nlm.nih.gov")) return "PubMed";
    if (host.includes("blast.ncbi.nlm.nih.gov")) return "NCBI BLAST";
    if (host.includes("ncbi.nlm.nih.gov")) return "NCBI";
    if (host.includes("uniprot.org")) return "UniProt";
    if (host.includes("doi.org")) return "DOI";
    if (host.includes("crossref.org")) return "Crossref";
    return host || "外部来源";
  } catch {
    return "外部来源";
  }
}

function extractSourcesFromText(text, includePlainLines = false) {
  const sources = [];
  const seen = new Set();
  const add = (url, title = "", provider = "", snippet = "") => {
    const cleanedUrl = String(url || "").replace(/[.,;:，。；：)]+$/, "");
    const key = cleanedUrl || `${title}|${snippet}`;
    if (!key || seen.has(key)) return;
    seen.add(key);
    sources.push({
      title: String(title || provider || "参考来源").replace(/^[-*+\d.)\s]+/, "").trim(),
      url: cleanedUrl,
      provider: String(provider || (cleanedUrl ? sourceProvider(cleanedUrl) : "文献条目")),
      snippet: String(snippet || "").trim()
    });
  };
  const markdownPattern = /\[([^\]]+)]\((https?:\/\/[^\s)]+)\)/g;
  for (const match of String(text || "").matchAll(markdownPattern)) add(match[2], match[1]);
  const urlPattern = /https?:\/\/[^\s<>\])]+/g;
  for (const match of String(text || "").matchAll(urlPattern)) add(match[0]);
  const doiPattern = /\b(10\.\d{4,9}\/[-._;()/:A-Z0-9]+)/gi;
  for (const match of String(text || "").matchAll(doiPattern)) add(`https://doi.org/${match[1]}`, `DOI ${match[1]}`, "DOI");
  const pmidPattern = /\b(?:PMID|PubMed)[:\s]*(\d{6,9})\b/gi;
  for (const match of String(text || "").matchAll(pmidPattern)) add(`https://pubmed.ncbi.nlm.nih.gov/${match[1]}/`, `PubMed PMID ${match[1]}`, "PubMed");

  for (const line of String(text || "").split("\n")) {
    const cleaned = line.replace(/^\s*(?:[-*+] |\d+[.)]\s*)/, "").trim();
    if (!cleaned || /^#{1,4}\s/.test(cleaned) || cleaned.length < 8) continue;
    const url = cleaned.match(/https?:\/\/[^\s<>\])]+/)?.[0] || "";
    if (url) {
      const title = cleaned.replace(url, "").replace(/^[：:\s]+|[：:\s]+$/g, "");
      add(url, title);
    } else if ((includePlainLines || /\b(?:doi|pmid|et al\.|\d{4})\b/i.test(cleaned)) && cleaned.length <= 500) {
      add("", cleaned, "文献条目");
    }
  }
  return sources.slice(0, 80);
}

function splitTerminalSources(content) {
  const source = String(content || "");
  const headingPattern = /^#{1,4}\s*(?:参考来源|参考文献|引用来源|来源|Sources?|References?)(?:\s*[（(].*?[）)])?\s*$/gim;
  const matches = [...source.matchAll(headingPattern)];
  const match = matches.at(-1);
  if (!match || match.index <= 0) {
    return { body: source, sourceSection: "" };
  }
  const body = source.slice(0, match.index).trim();
  const sourceSection = source.slice(match.index + match[0].length).trim();
  return body && sourceSection ? { body, sourceSection } : { body: source, sourceSection: "" };
}

function uniqueSources(...groups) {
  const items = [];
  const seen = new Set();
  for (const source of groups.flat()) {
    if (!source || typeof source !== "object") continue;
    const normalized = {
      title: String(source.title || source.provider || "参考来源"),
      url: String(source.url || ""),
      provider: String(source.provider || (source.url ? sourceProvider(source.url) : "文献条目")),
      snippet: String(source.snippet || "")
    };
    const key = normalized.url || `${normalized.title}|${normalized.snippet}`;
    if (!key || seen.has(key)) continue;
    seen.add(key);
    items.push(normalized);
  }
  return items.slice(0, 80);
}

function presentationForMessage(message) {
  const split = splitTerminalSources(message.content);
  const sectionSources = extractSourcesFromText(split.sourceSection, true);
  const processSources = (message.agentProcess || []).flatMap((step) => extractSourcesFromText(step.output || ""));
  const inlineSources = Array.isArray(message.sources) && message.sources.length
    ? []
    : extractSourcesFromText(message.content);
  const sources = uniqueSources(message.sources || [], sectionSources, inlineSources, processSources);
  const trace = Array.isArray(message.trace) && message.trace.length
    ? message.trace
    : [{
        title: "生成并组织回答",
        kind: "reasoning",
        confidence: 62,
        detail: "该历史回答未记录真实工具日志，因此仅展示可审计的过程摘要，不能视为完整思维链。"
      }];
  message.sources = sources;
  message.trace = trace;
  return {
    body: split.body,
    sources,
    trace,
    agentProcess: message.agentProcess || [],
    artifacts: message.artifacts || [],
    toolArtifacts: message.toolArtifacts || []
  };
}

function actionIcon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("message-action-icon");
  const paths = {
    copy: ["M9 9h10v10H9z", "M5 15H4V5h10v1"],
    markdown: ["M3 6h18v12H3z", "M6 15V9l2.5 3L11 9v6", "m14-3 2 2 2-2", "M16 9v5"],
    like: ["M7 10v10H3V10h4Z", "M7 18c3 1 5 2 9 2l4-8c.5-1-.2-2-1.3-2H14l1-4c.3-1.7-2-2.5-2.8-1L7 10"],
    dislike: ["M7 14V4H3v10h4Z", "M7 6c3-1 5-2 9-2l4 8c.5 1-.2 2-1.3 2H14l1 4c.3 1.7-2 2.5-2.8 1L7 14"],
    trace: ["M5 5h4v4H5z", "M15 5h4v4h-4z", "M10 15h4v4h-4z", "M9 7h6", "M17 9v3l-5 3", "M7 9v3l5 3"],
    sources: ["M4 5h16v14H4z", "M8 9h8", "M8 13h8", "M8 17h5"],
    files: ["M4 7h6l2 2h8v10H4z", "M8 13h8", "M8 16h5"],
    download: ["M12 4v11", "m8 11 4 4 4-4", "M5 20h14"]
  };
  for (const value of paths[name] || []) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", value);
    svg.appendChild(path);
  }
  return svg;
}

function makeActionButton(icon, label, visibleLabel = "") {
  const button = document.createElement("button");
  button.type = "button";
  button.title = label;
  button.setAttribute("aria-label", label);
  button.appendChild(actionIcon(icon));
  if (visibleLabel) {
    const text = document.createElement("span");
    text.textContent = visibleLabel;
    button.appendChild(text);
  }
  return button;
}

function closeDetailPanel() {
  els.detailPanel.hidden = true;
  els.appShell.classList.remove("detail-open");
}

function renderSourcesPanel(sources) {
  const list = document.createElement("div");
  list.className = "source-list";
  for (const [index, source] of sources.entries()) {
    const card = document.createElement(source.url ? "a" : "article");
    card.className = "source-card";
    if (source.url) {
      card.href = source.url;
      card.target = "_blank";
      card.rel = "noopener noreferrer";
    }
    const number = document.createElement("span");
    number.className = "source-index";
    number.textContent = String(index + 1);
    const copy = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = source.title || `来源 ${index + 1}`;
    const provider = document.createElement("small");
    provider.textContent = source.url ? `${source.provider} · ${source.url}` : source.provider;
    copy.append(title, provider);
    if (source.snippet) {
      const snippet = document.createElement("p");
      snippet.textContent = source.snippet;
      copy.appendChild(snippet);
    }
    card.append(number, copy);
    list.appendChild(card);
  }
  return list;
}

function confidenceLabel(value) {
  const confidence = Math.max(0, Math.min(100, Number(value) || 0));
  if (confidence >= 85) return { label: `高 ${confidence}%`, className: "high" };
  if (confidence >= 70) return { label: `中 ${confidence}%`, className: "medium" };
  return { label: `低 ${confidence}%`, className: "low" };
}

function renderTracePanel(trace) {
  const list = document.createElement("div");
  list.className = "trace-list";
  for (const [index, step] of trace.entries()) {
    const article = document.createElement("article");
    article.className = `trace-step ${step.kind === "reasoning" ? "reasoning" : "tool"}`;
    const marker = document.createElement("span");
    marker.className = "trace-marker";
    marker.textContent = String(index + 1);
    const card = document.createElement("div");
    card.className = "trace-card";
    const header = document.createElement("div");
    header.className = "trace-card-header";
    const title = document.createElement("h3");
    title.textContent = String(step.title || `步骤 ${index + 1}`);
    const confidence = confidenceLabel(step.confidence);
    const badge = document.createElement("span");
    badge.className = `confidence-badge ${confidence.className}`;
    badge.textContent = confidence.label;
    header.append(title, badge);
    const detail = document.createElement("p");
    detail.textContent = String(step.detail || "该步骤没有更多记录。");
    card.append(header, detail);
    article.append(marker, card);
    list.appendChild(article);
  }
  return list;
}

function renderAgentProcessPanel(process) {
  const list = document.createElement("div");
  list.className = "agent-process-list";
  for (const [index, step] of process.entries()) {
    const details = document.createElement("details");
    details.className = "agent-process-step";
    if (index === process.length - 1) details.open = true;
    const summary = document.createElement("summary");
    const title = document.createElement("strong");
    title.textContent = `${step.position || index + 1}. ${step.title || `步骤 ${index + 1}`}`;
    const meta = document.createElement("span");
    meta.className = "agent-process-meta";
    const metaText = document.createElement("span");
    metaText.textContent = [step.skill, step.status, step.attempts ? `${step.attempts} 次尝试` : ""].filter(Boolean).join(" · ");
    meta.appendChild(metaText);
    if (step.confidence) {
      const confidence = confidenceLabel(step.confidence);
      const badge = document.createElement("span");
      badge.className = `confidence-badge ${confidence.className}`;
      badge.textContent = confidence.label;
      meta.appendChild(badge);
    }
    summary.append(title, meta);
    const content = document.createElement("div");
    content.className = "agent-process-output";
    if (step.instruction) {
      const instruction = document.createElement("p");
      instruction.className = "agent-process-instruction";
      instruction.textContent = step.instruction;
      content.appendChild(instruction);
    }
    if (step.output) content.appendChild(renderMarkdown(step.output));
    if (step.error) {
      const error = document.createElement("p");
      error.className = "agent-process-error";
      error.textContent = step.error;
      content.appendChild(error);
    }
    if (!step.output && !step.error) {
      const empty = document.createElement("p");
      empty.className = "detail-empty";
      empty.textContent = "该步骤没有保存详细输出。";
      content.appendChild(empty);
    }
    details.append(summary, content);
    list.appendChild(details);
  }
  return list;
}

function formatFileSize(size) {
  const bytes = Math.max(0, Number(size) || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function renderArtifactsPanel(artifacts) {
  const list = document.createElement("div");
  list.className = "artifact-list";
  for (const artifact of artifacts) {
    const link = document.createElement("a");
    link.className = "artifact-card";
    link.href = artifact.url;
    link.download = artifact.name;
    const icon = actionIcon("download");
    const copy = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = artifact.name;
    const meta = document.createElement("small");
    meta.textContent = `${formatFileSize(artifact.size)} · ${artifact.path}`;
    copy.append(title, meta);
    link.append(icon, copy);
    list.appendChild(link);
  }
  return list;
}

function renderToolArtifactsPanel(artifacts) {
  const list = document.createElement("div");
  list.className = "artifact-list";
  for (const artifact of artifacts) {
    const card = document.createElement("div");
    card.className = "artifact-card tool-artifact-card";
    const icon = actionIcon("files");
    const copy = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = artifact.name;
    const meta = document.createElement("small");
    const digest = artifact.sha256 ? ` · SHA-256 ${artifact.sha256.slice(0, 12)}…` : "";
    meta.textContent = `${formatFileSize(artifact.size)} · ${artifact.kind === "text" ? "文本" : "文件"}${digest}`;
    copy.append(title, meta);
    const controls = document.createElement("div");
    controls.className = "tool-artifact-actions";
    if (artifact.kind === "text") {
      const preview = document.createElement("button");
      preview.type = "button";
      preview.textContent = "预览";
      preview.addEventListener("click", async () => {
        preview.disabled = true;
        preview.textContent = "读取中";
        try {
          const result = await desktopInvoke("desktop_read_tool_artifact", { artifactId: artifact.artifactId });
          let output = card.querySelector(".tool-artifact-preview");
          if (!output) {
            output = document.createElement("pre");
            output.className = "tool-artifact-preview";
            card.appendChild(output);
          }
          output.textContent = result.previewable
            ? `${result.content || ""}${result.truncated ? "\n\n[预览已截断]" : ""}`
            : "该文件不是可预览的 UTF-8 文本。";
          preview.textContent = "刷新预览";
        } catch (error) {
          preview.textContent = "预览失败";
          preview.title = String(error.message || error);
        } finally {
          preview.disabled = false;
        }
      });
      controls.appendChild(preview);
    }
    const reveal = document.createElement("button");
    reveal.type = "button";
    reveal.textContent = "显示文件";
    reveal.addEventListener("click", async () => {
      reveal.disabled = true;
      try {
        await desktopInvoke("desktop_reveal_tool_artifact", { artifactId: artifact.artifactId });
        reveal.textContent = "已显示";
      } catch (error) {
        reveal.textContent = "显示失败";
        reveal.title = String(error.message || error);
      } finally {
        reveal.disabled = false;
      }
    });
    controls.appendChild(reveal);
    const exportButton = document.createElement("button");
    exportButton.type = "button";
    exportButton.textContent = "另存为";
    exportButton.addEventListener("click", async () => {
      exportButton.disabled = true;
      exportButton.textContent = "选择位置";
      try {
        const result = await desktopInvoke("desktop_export_tool_artifact", { artifactId: artifact.artifactId });
        exportButton.textContent = result ? "已保存" : "另存为";
        if (result) exportButton.title = `${result.fileName} · ${formatFileSize(result.sizeBytes)}`;
      } catch (error) {
        exportButton.textContent = "保存失败";
        exportButton.title = String(error.message || error);
      } finally {
        exportButton.disabled = false;
      }
    });
    controls.appendChild(exportButton);
    card.append(icon, copy, controls);
    list.appendChild(card);
  }
  return list;
}

function openDetailPanel(type, message, presentation) {
  els.detailPanelContent.innerHTML = "";
  els.detailPanel.hidden = false;
  els.appShell.classList.add("detail-open");
  if (type === "sources") {
    els.detailPanelEyebrow.textContent = "回答证据";
    els.detailPanelTitle.textContent = `参考来源 (${presentation.sources.length})`;
    els.detailPanelNote.textContent = "来源链接用于追溯证据；链接真实存在不等于支持回答中的全部结论，请核对原文。";
    els.detailPanelContent.appendChild(presentation.sources.length
      ? renderSourcesPanel(presentation.sources)
      : Object.assign(document.createElement("p"), { className: "detail-empty", textContent: "这条回答没有可展示的来源。" }));
  } else if (type === "artifacts") {
    els.detailPanelEyebrow.textContent = "Agent 交付";
    els.detailPanelTitle.textContent = `产物文件 (${presentation.artifacts.length})`;
    els.detailPanelNote.textContent = "这里列出当前科研项目中的 Agent 产物。文件通过登录权限校验后下载，内部运行文件不会展示。";
    els.detailPanelContent.appendChild(presentation.artifacts.length
      ? renderArtifactsPanel(presentation.artifacts)
      : Object.assign(document.createElement("p"), { className: "detail-empty", textContent: "这项任务没有可下载的产物。" }));
  } else if (type === "tool-artifacts") {
    els.detailPanelEyebrow.textContent = "本地 ToolRun";
    els.detailPanelTitle.textContent = `本地产物 (${presentation.toolArtifacts.length})`;
    els.detailPanelNote.textContent = "预览和显示文件都由 Desktop Core 按 Artifact ID 校验路径、大小和 SHA-256；WebView 不能提交任意本地路径。";
    els.detailPanelContent.appendChild(presentation.toolArtifacts.length
      ? renderToolArtifactsPanel(presentation.toolArtifacts)
      : Object.assign(document.createElement("p"), { className: "detail-empty", textContent: "这次 ToolRun 没有保存产物。" }));
  } else if (type === "agent-process") {
    els.detailPanelEyebrow.textContent = "Agent 执行记录";
    els.detailPanelTitle.textContent = `执行过程 (${presentation.agentProcess.length})`;
    els.detailPanelNote.textContent = "这里展示各步骤保存的完整输出、Python 代码和工具记录；它是可审计执行记录，不是模型内部隐藏思维链。";
    els.detailPanelContent.appendChild(renderAgentProcessPanel(presentation.agentProcess));
  } else {
    els.detailPanelEyebrow.textContent = "可审计过程";
    els.detailPanelTitle.textContent = `分析与工具过程 (${presentation.trace.length})`;
    els.detailPanelNote.textContent = "这里展示 ReAct 风格的步骤摘要、真实工具记录和依据置信度，不展示模型内部隐藏思维链。置信度表示步骤依据强弱，不代表结论正确率。";
    els.detailPanelContent.appendChild(renderTracePanel(presentation.trace));
  }
  message.lastOpenedDetail = type;
}

function primaryReportArtifact(message, artifacts) {
  if (!artifacts.length) return null;
  const referenced = [...String(message.content || "").matchAll(/\/workspace\/project\/([^\s`)'"，。]+)/g)]
    .map((match) => match[1]);
  for (const path of referenced) {
    const exact = artifacts.find((artifact) => artifact.path === path);
    if (exact) return exact;
  }
  return artifacts.find((artifact) => /(?:comprehensive|integrated|final).*report.*\.md$/i.test(artifact.name))
    || artifacts.find((artifact) => /report.*\.md$/i.test(artifact.name))
    || artifacts.find((artifact) => /\.md$/i.test(artifact.name))
    || null;
}

async function submitMessageFeedback(message, rating, likeButton, dislikeButton) {
  const previous = message.feedback || "none";
  const next = previous === rating ? "none" : rating;
  message.feedback = next;
  likeButton.classList.toggle("active", next === "like");
  dislikeButton.classList.toggle("active", next === "dislike");
  likeButton.disabled = true;
  dislikeButton.disabled = true;
  persistChats();
  try {
    const response = await authenticatedFetch("/api/messages/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messageId: message.id,
        chatId: activeChat().id,
        skill: message.skill || currentFunction().skill,
        rating: next,
        content: message.content
      })
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "反馈保存失败");
  } catch (error) {
    message.feedback = previous;
    likeButton.classList.toggle("active", previous === "like");
    dislikeButton.classList.toggle("active", previous === "dislike");
    likeButton.title = `反馈保存失败：${String(error.message || error)}`;
  } finally {
    likeButton.disabled = false;
    dislikeButton.disabled = false;
    persistChats();
  }
}

function appendMessage(role, content, sourceMessage = null) {
  const message = normalizeMessage(sourceMessage || { role, content });
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user"
    ? "你"
    : currentFunction().id === "research_assistant" ? "助手" : currentFunction().title;

  const presentation = role === "assistant" ? presentationForMessage(message) : null;
  const body = role === "assistant" ? renderMarkdown(presentation.body) : document.createElement("pre");
  if (role !== "assistant") body.textContent = content;

  article.append(label, body);
  if (role === "assistant") {
    if (message.agentPlan?.planId || message.agentPlan?.jobId) article.appendChild(renderAgentPlanApproval(message));
    const actions = document.createElement("div");
    actions.className = "message-actions";
    const copyText = makeActionButton("copy", "复制回答");
    copyText.addEventListener("click", () => copyToClipboard(body.innerText, copyText));
    const copyMarkdown = makeActionButton("markdown", "复制 Markdown", "Markdown");
    copyMarkdown.addEventListener("click", () => copyToClipboard(String(content || ""), copyMarkdown));
    const likeButton = makeActionButton("like", "这个回答有帮助");
    const dislikeButton = makeActionButton("dislike", "这个回答需要改进");
    dislikeButton.classList.add("feedback-dislike");
    likeButton.classList.toggle("active", message.feedback === "like");
    dislikeButton.classList.toggle("active", message.feedback === "dislike");
    likeButton.addEventListener("click", () => submitMessageFeedback(message, "like", likeButton, dislikeButton));
    dislikeButton.addEventListener("click", () => submitMessageFeedback(message, "dislike", likeButton, dislikeButton));
    const hasAgentProcess = presentation.agentProcess.length > 0;
    const traceButton = makeActionButton(
      "trace",
      hasAgentProcess ? "查看 Agent 执行过程" : "查看分析与工具过程",
      hasAgentProcess ? `执行过程 · ${presentation.agentProcess.length}` : `${presentation.trace.length} 步过程`
    );
    traceButton.classList.add("detail-trigger");
    traceButton.addEventListener("click", () => openDetailPanel(hasAgentProcess ? "agent-process" : "trace", message, presentation));
    actions.append(copyText, copyMarkdown, likeButton, dislikeButton, traceButton);
    if (presentation.sources.length) {
      const sourceButton = makeActionButton("sources", "查看参考来源", `${presentation.sources.length} 篇来源`);
      sourceButton.classList.add("detail-trigger");
      sourceButton.addEventListener("click", () => openDetailPanel("sources", message, presentation));
      actions.appendChild(sourceButton);
    }
    if (presentation.artifacts.length) {
      const artifactButton = makeActionButton("files", "查看 Agent 产物", `产物 · ${presentation.artifacts.length}`);
      artifactButton.classList.add("detail-trigger");
      artifactButton.addEventListener("click", () => openDetailPanel("artifacts", message, presentation));
      actions.appendChild(artifactButton);
      const report = primaryReportArtifact(message, presentation.artifacts);
      if (report) {
        const download = document.createElement("a");
        download.className = "message-download";
        download.href = report.url;
        download.download = report.name;
        download.title = `下载 ${report.name}`;
        download.setAttribute("aria-label", `下载报告 ${report.name}`);
        download.append(actionIcon("download"), Object.assign(document.createElement("span"), { textContent: "下载报告" }));
        actions.appendChild(download);
      }
    }
    if (presentation.toolArtifacts.length) {
      const toolArtifacts = makeActionButton("files", "查看本地 ToolRun 产物", `本地产物 · ${presentation.toolArtifacts.length}`);
      toolArtifacts.classList.add("detail-trigger");
      toolArtifacts.addEventListener("click", () => openDetailPanel("tool-artifacts", message, presentation));
      actions.appendChild(toolArtifacts);
    }
    if (state.desktopMode && message.agentJobId) {
      const textStatistics = makeActionButton("trace", "使用低风险本地工具统计这条回答", "文本统计");
      textStatistics.addEventListener("click", () => runDesktopTextStatistics(message.agentJobId, String(content || "")));
      actions.appendChild(textStatistics);
    }
    const pythonBlocks = [...String(content || "").matchAll(/```(?:python|py)\s*\n([\s\S]*?)```/gi)];
    if (pythonBlocks.length) {
      const runPython = document.createElement("button");
      runPython.type = "button";
      runPython.textContent = "运行 Python";
      runPython.title = "查看权限并逐次确认后执行最后一个 Python 代码块";
      runPython.addEventListener("click", async () => {
        const activeToolRunId = runPython.dataset.toolRunId;
        if (activeToolRunId) {
          runPython.disabled = true;
          setBadge("python cancelling");
          try {
            await desktopInvoke("desktop_cancel_tool_run", { toolRunId: activeToolRunId });
          } catch (error) {
            runPython.disabled = false;
            setBadge("error", "error");
            addSessionMessage("assistant", `## 无法停止 Python\n\n${String(error.message || error)}`);
            renderConversation();
          }
          return;
        }
        await runPythonCode(pythonBlocks.at(-1)[1].trim(), message.agentJobId, runPython, "native");
      });
      actions.appendChild(runPython);
      if (state.desktopMode) {
        const capability = state.containerCapability;
        const runSandbox = document.createElement("button");
        runSandbox.type = "button";
        runSandbox.textContent = capability?.available ? "Docker 沙箱" : "Docker 未就绪";
        runSandbox.title = capability?.available
          ? "在固定镜像、无网络、只读根文件系统的容器中运行"
          : capability?.reason || "安装并启动 Docker Desktop 后可用";
        runSandbox.disabled = !capability?.available;
        runSandbox.addEventListener("click", async () => {
          const activeToolRunId = runSandbox.dataset.toolRunId;
          if (activeToolRunId) {
            runSandbox.disabled = true;
            setBadge("container cancelling");
            try {
              await desktopInvoke("desktop_cancel_tool_run", { toolRunId: activeToolRunId });
            } catch (error) {
              runSandbox.disabled = false;
              setBadge("error", "error");
              addSessionMessage("assistant", `## 无法停止 Docker 沙箱\n\n${String(error.message || error)}`);
              renderConversation();
            }
            return;
          }
          await runPythonCode(pythonBlocks.at(-1)[1].trim(), message.agentJobId, runSandbox, "container");
        });
        actions.appendChild(runSandbox);
      }
    }
    article.appendChild(actions);
  }
  els.conversation.appendChild(article);
}

async function copyToClipboard(text, button) {
  const original = button.innerHTML;
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "已复制";
    setTimeout(() => { button.innerHTML = original; }, 1200);
  } catch {
    button.textContent = "复制失败";
    setTimeout(() => { button.innerHTML = original; }, 1500);
  }
}

async function desktopToolHostJob(agentJobId) {
  if (agentJobId) return agentJobId;
  const conversationId = await desktopAgentConversation();
  const job = await desktopInvoke("desktop_create_agent_job", {
    conversationId,
    request: {
      mode: "tool-host",
      purpose: "user-initiated-python-tool"
    }
  });
  let detail = await desktopInvoke("desktop_start_agent_job", { jobId: job.id });
  for (let attempt = 0; attempt < 40 && ["queued", "running", "cancelling"].includes(detail.job.status); attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 25));
    detail = await desktopInvoke("desktop_refresh_agent_job", { jobId: job.id });
  }
  if (detail.job.status !== "completed") {
    throw new Error(`Tool-host AgentJob ended with status ${detail.job.status}`);
  }
  return job.id;
}

async function ensureDesktopContainerImage() {
  let capability = await refreshDesktopContainerCapability({ render: false });
  if (!capability.available) throw new Error(capability.reason || "Docker Desktop 不可用。");
  if (capability.imageAvailable) return true;
  setBadge("preparing container");
  capability = await desktopInvoke("desktop_prepare_container_image");
  state.containerCapability = capability;
  updateDesktopContainerStatus(capability);
  return capability.imageAvailable;
}

async function runPythonCode(code, agentJobId = "", triggerButton = null, executorMode = "native") {
  const containerMode = state.desktopMode && executorMode === "container";
  if (containerMode) {
    try {
      if (!await ensureDesktopContainerImage()) return;
    } catch (error) {
      addSessionMessage("assistant", `## Docker 沙箱尚未就绪\n\n${String(error.message || error)}`);
      renderConversation();
      setBadge("error", "error");
      return;
    }
  }
  let execution = state.desktopMode
    ? containerMode
      ? { runtime: "Docker / Python", network: "none", readOnlyRoot: true }
      : { runtime: "Local Python", network: "host", readOnlyRoot: false }
    : { runtime: "Docker / Python", network: "disabled", readOnlyRoot: true };
  let contractRun = null;
  if (!state.desktopMode) {
    try {
      execution = await authenticatedFetch("/api/execution/config").then((response) => response.json());
    } catch {
      // The execution endpoint will return the authoritative error if unavailable.
    }
  }
  if (state.desktopMode) {
    try {
      agentJobId = await desktopToolHostJob(agentJobId);
      contractRun = await desktopInvoke("desktop_propose_tool_run", {
        agentJobId,
        toolName: containerMode ? "python.container" : "python.run",
        input: { code }
      });
    } catch (error) {
      addSessionMessage("assistant", `## 无法创建 Python ToolRun\n\n${String(error.message || error)}`);
      renderConversation();
      setBadge("error", "error");
      return;
    }
  }
  const permissions = contractRun?.permissionSnapshot;
  const warning = execution.runtime === "Local Python"
    ? `极高风险工具 python.run 请求逐次授权。\n\n将在本机 Python 中直接执行此代码。它不是 Docker 沙箱，拥有当前用户级文件和网络能力。\n\n权限快照：文件 ${permissions?.filesystem?.map((item) => `${item.scope}:${item.mode}`).join(", ") || "未声明"}；网络 ${permissions?.network || "host"}；Secret ${permissions?.secrets?.length || 0} 项。\n\n请确认你已经逐行检查代码，是否继续？`
    : `高风险工具 python.container 请求逐次授权。\n\n将在固定镜像、无网络、只读根文件系统、非 root 的 Docker 沙箱中执行代码，只挂载本次任务的只读输入目录和可写输出目录。\n\n镜像：${state.containerCapability?.image || "固定摘要镜像"}\n权限快照：文件 ${permissions?.filesystem?.map((item) => `${item.scope}:${item.mode}`).join(", ") || "未声明"}；网络 ${permissions?.network || "none"}；Secret ${permissions?.secrets?.length || 0} 项。\n\n是否继续？`;
  let approved;
  try {
    approved = await confirmDesktopToolRun(warning);
  } catch (error) {
    addSessionMessage("assistant", `## 无法显示工具授权对话框\n\n${String(error.message || error)}`);
    renderConversation();
    setBadge("error", "error");
    return;
  }
  if (contractRun) {
    try {
      await desktopInvoke("desktop_decide_tool_run", {
        toolRunId: contractRun.id,
        approved
      });
    } catch (error) {
      addSessionMessage("assistant", `## 无法保存工具授权决定\n\n${String(error.message || error)}`);
      renderConversation();
      return;
    }
  }
  if (!approved) {
    setBadge("tool denied");
    return;
  }
  setBadge("python running");
  try {
    let data;
    if (contractRun) {
      if (triggerButton) {
        triggerButton.dataset.toolRunId = contractRun.id;
        triggerButton.textContent = containerMode ? "停止沙箱" : "停止 Python";
        triggerButton.title = containerMode
          ? "停止本次容器 ToolRun 并删除临时容器"
          : "停止本次 Python ToolRun 及其子进程";
      }
      const completedRun = await desktopInvoke(containerMode
        ? "desktop_execute_approved_container_tool"
        : "desktop_execute_approved_python_tool", {
        toolRunId: contractRun.id
      });
      data = completedRun.output || { ok: false, status: completedRun.status, files: [] };
    } else {
      data = await agentRequest("/api/execute/python", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, confirmed: true })
      });
    }
    const lines = [containerMode || !state.desktopMode ? "# Python 沙箱结果" : "# Python 本地执行结果", "", `**状态：** ${data.status}`, `**Job ID：** \`${data.jobId}\``, ""];
    if (contractRun) lines.splice(4, 0, `**ToolRun ID：** \`${contractRun.id}\``, "");
    if (data.stdout) lines.push("## stdout", "", "```text", data.stdout, "```", "");
    if (data.stderr) lines.push("## stderr", "", "```text", data.stderr, "```", "");
    if (data.error) lines.push("## 执行器错误", "", String(data.error), "");
    if (data.files?.length) {
      lines.push("## 输出文件", "");
      for (const file of data.files) {
        if (file.url) {
          lines.push(`- [${file.name}](${file.url}) · ${file.size} bytes${file.sha256 ? ` · SHA-256 \`${file.sha256}\`` : ""}`);
        } else {
          lines.push(`- \`${file.name}\` · ${file.size} bytes · 已保存在本地 ToolRun 输出目录`);
        }
      }
    }
    addSessionMessage("assistant", lines.join("\n"), {
      toolArtifacts: Array.isArray(data.files) ? data.files : []
    });
    persistChats();
    renderConversation();
    setBadge(data.ok ? "python done" : "error", data.ok ? "" : "error");
  } catch (error) {
    currentSession().push({ role: "assistant", content: `## Python 执行失败\n\n${String(error.message || error)}` });
    renderConversation();
    setBadge("error", "error");
  } finally {
    if (triggerButton) {
      delete triggerButton.dataset.toolRunId;
      triggerButton.disabled = false;
      triggerButton.textContent = containerMode ? "Docker 沙箱" : "运行 Python";
      triggerButton.title = containerMode
        ? "在固定镜像、无网络、只读根文件系统的容器中运行"
        : "查看权限并逐次确认后执行最后一个 Python 代码块";
    }
  }
}

async function runDesktopTextStatistics(agentJobId, text) {
  setBadge("tool running");
  try {
    const toolRun = await desktopInvoke("desktop_run_low_risk_tool", {
      agentJobId,
      toolName: "text.statistics",
      input: { text }
    });
    const output = toolRun.output || {};
    addSessionMessage(
      "assistant",
      [
        "## 本地文本统计",
        "",
        `- 字符数：${output.characters ?? 0}`,
        `- 非空白字符：${output.nonWhitespaceCharacters ?? 0}`,
        `- 单词数：${output.words ?? 0}`,
        `- 行数：${output.lines ?? 0}`,
        `- UTF-8 字节数：${output.bytes ?? 0}`
      ].join("\n"),
      {
        trace: [{
          title: "Tool Contract · text.statistics",
          kind: "tool",
          confidence: 100,
          detail: `Native Executor · ${toolRun.status} · 无文件、网络或 Secret 权限`
        }]
      }
    );
    renderConversation();
    setBadge(toolRun.status === "succeeded" ? "tool done" : "error", toolRun.status === "succeeded" ? "" : "error");
  } catch (error) {
    addSessionMessage("assistant", `## ToolRun 失败\n\n${String(error.message || error)}`);
    renderConversation();
    setBadge("error", "error");
  }
}

function appendInlineMarkdown(container, text) {
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g;
  let cursor = 0;
  for (const match of text.matchAll(pattern)) {
    if (match.index > cursor) container.appendChild(document.createTextNode(text.slice(cursor, match.index)));
    const token = match[0];
    if (token.startsWith("`")) {
      const code = document.createElement("code");
      code.textContent = token.slice(1, -1);
      container.appendChild(code);
    } else if (token.startsWith("**")) {
      const strong = document.createElement("strong");
      strong.textContent = token.slice(2, -2);
      container.appendChild(strong);
    } else {
      const linkMatch = token.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
      const link = document.createElement("a");
      link.textContent = linkMatch[1];
      link.href = linkMatch[2];
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      container.appendChild(link);
    }
    cursor = match.index + token.length;
  }
  if (cursor < text.length) container.appendChild(document.createTextNode(text.slice(cursor)));
}

function markdownTable(lines, start) {
  if (start + 1 >= lines.length || !/^\s*\|?\s*:?-{3,}/.test(lines[start + 1])) return null;
  const rows = [];
  let index = start;
  while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
    if (index !== start + 1) {
      rows.push(lines[index].trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim()));
    }
    index += 1;
  }
  if (!rows.length) return null;
  const table = document.createElement("table");
  rows.forEach((cells, rowIndex) => {
    const row = document.createElement("tr");
    cells.forEach((cell) => {
      const element = document.createElement(rowIndex === 0 ? "th" : "td");
      appendInlineMarkdown(element, cell);
      row.appendChild(element);
    });
    (rowIndex === 0 ? table.createTHead() : table.tBodies[0] || table.createTBody()).appendChild(row);
  });
  return { element: table, next: index };
}

function renderMarkdown(source) {
  const root = document.createElement("div");
  root.className = "markdown-body";
  const lines = String(source || "").replace(/\r\n/g, "\n").split("\n");
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }
    if (line.trim().startsWith("```")) {
      const language = line.trim().slice(3).trim();
      const content = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) content.push(lines[index++]);
      if (index < lines.length) index += 1;
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      if (language) code.dataset.language = language;
      code.textContent = content.join("\n");
      pre.appendChild(code);
      root.appendChild(pre);
      continue;
    }
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const element = document.createElement(`h${heading[1].length}`);
      appendInlineMarkdown(element, heading[2]);
      root.appendChild(element);
      index += 1;
      continue;
    }
    const table = markdownTable(lines, index);
    if (table) {
      root.appendChild(table.element);
      index = table.next;
      continue;
    }
    if (/^\s*[-*+]\s+/.test(line) || /^\s*\d+[.)]\s+/.test(line)) {
      const ordered = /^\s*\d+[.)]\s+/.test(line);
      const list = document.createElement(ordered ? "ol" : "ul");
      while (index < lines.length) {
        const match = lines[index].match(ordered ? /^\s*\d+[.)]\s+(.+)$/ : /^\s*[-*+]\s+(.+)$/);
        if (!match) break;
        const item = document.createElement("li");
        appendInlineMarkdown(item, match[1]);
        list.appendChild(item);
        index += 1;
      }
      root.appendChild(list);
      continue;
    }
    if (/^>\s?/.test(line)) {
      const quote = document.createElement("blockquote");
      const parts = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) parts.push(lines[index++].replace(/^>\s?/, ""));
      appendInlineMarkdown(quote, parts.join("\n"));
      root.appendChild(quote);
      continue;
    }
    if (/^---+$/.test(line.trim())) {
      root.appendChild(document.createElement("hr"));
      index += 1;
      continue;
    }
    const paragraph = document.createElement("p");
    const parts = [line];
    index += 1;
    while (index < lines.length && lines[index].trim() && !/^(#{1,4})\s+|^\s*```|^\s*[-*+]\s+|^\s*\d+[.)]\s+|^>\s?|^---+$/.test(lines[index])) {
      if (markdownTable(lines, index)) break;
      parts.push(lines[index++]);
    }
    appendInlineMarkdown(paragraph, parts.join("\n"));
    root.appendChild(paragraph);
  }
  return root;
}

function renderConversation() {
  persistChats();
  renderChatHistory();
  els.conversation.innerHTML = "";
  const session = currentSession();
  if (!session.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const title = document.createElement("h3");
    title.textContent = currentFunction().id === "research_assistant" ? "新对话" : currentFunction().title;
    const purpose = document.createElement("p");
    purpose.textContent = currentFunction().purpose;
    empty.append(title, purpose);
    if (currentFunction().starters) {
      const starters = document.createElement("div");
      starters.className = "starter-list";
      for (const text of currentFunction().starters) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = text;
        button.addEventListener("click", () => {
          els.taskInput.value = text;
          els.taskInput.focus();
        });
        starters.appendChild(button);
      }
      empty.appendChild(starters);
    }
    els.conversation.appendChild(empty);
    return;
  }

  for (const item of session) {
    appendMessage(item.role, item.content, item);
  }
  els.conversation.scrollTop = els.conversation.scrollHeight;
}

function selectFunction(functionId, options = {}) {
  state.functionId = functions[functionId] ? functionId : "research_assistant";
  if (options.updateChat !== false) {
    const chat = activeChat();
    chat.functionId = state.functionId;
    chat.updatedAt = new Date().toISOString();
    persistChats();
    renderChatHistory();
  }
  const item = currentFunction();
  els.selectedSkill.textContent = item.id === "research_assistant" ? activeChat().title : item.title;
  els.activePurpose.textContent = item.purpose;
  els.taskInput.placeholder = `与“${item.title}”对话，Enter 发送，Shift+Enter 换行`;
  document.querySelectorAll(".function-item, .standalone-function").forEach((button) => {
    button.classList.toggle("active", button.dataset.functionId === item.id);
  });
  setBadge("ready");
  updateUploadContext();
  renderConversation();
  els.taskInput.focus();
}

function chooseFunction(functionId) {
  const targetFunctionId = functions[functionId] ? functionId : "research_assistant";
  const chat = activeChat();
  if (chat.messages.length > 0 && chat.functionId !== targetFunctionId) {
    clearAttachment();
    createChat(targetFunctionId);
    return;
  }
  selectFunction(targetFunctionId);
}

function updateDesktopContainerStatus(capability) {
  const dockerStatus = capability?.available
    ? capability.imageAvailable ? "Docker 沙箱就绪" : "Docker 待准备镜像"
    : capability?.installed ? "Docker 未启动" : "无 Docker";
  const baseTitle = els.desktopRuntime.dataset.baseTitle || "本地执行";
  els.desktopRuntime.title = `${baseTitle} · ${dockerStatus}`;
}

function scheduleDesktopContainerRefresh(capability) {
  if (containerCapabilityRefreshTimer) {
    clearTimeout(containerCapabilityRefreshTimer);
    containerCapabilityRefreshTimer = null;
  }
  if (!state.desktopMode || capability?.available || document.visibilityState === "hidden") return;
  containerCapabilityRefreshTimer = setTimeout(() => {
    containerCapabilityRefreshTimer = null;
    void refreshDesktopContainerCapability();
  }, 5000);
}

async function refreshDesktopContainerCapability({ render = true } = {}) {
  if (!state.desktopMode) return null;
  if (containerCapabilityRefreshInFlight) return containerCapabilityRefreshInFlight;
  containerCapabilityRefreshInFlight = (async () => {
    const previous = JSON.stringify(state.containerCapability);
    try {
      state.containerCapability = await desktopInvoke("desktop_container_capability");
    } catch {
      state.containerCapability = {
        installed: false,
        available: false,
        imageAvailable: false,
        reason: "无法读取 Docker 能力。"
      };
    }
    updateDesktopContainerStatus(state.containerCapability);
    scheduleDesktopContainerRefresh(state.containerCapability);
    if (render && previous !== JSON.stringify(state.containerCapability)) renderConversation();
    return state.containerCapability;
  })();
  try {
    return await containerCapabilityRefreshInFlight;
  } finally {
    containerCapabilityRefreshInFlight = null;
  }
}

async function loadConfig() {
  const config = await fetch("/api/config").then((response) => response.json());
  state.desktopMode = Boolean(config.desktopMode);
  els.baseUrl.value = config.baseUrl;
  els.model.value = config.model;
  els.keyStatus.textContent = config.hasEnvApiKey
    ? "已检测到环境变量 DASHSCOPE_API_KEY。"
    : "未检测到环境变量，可在此临时填写 API Key。";
  if (config.desktopMode) {
    await loadDesktopProviderProfile();
    try {
      const status = await fetch("/api/desktop/status").then((response) => response.json());
      els.desktopRuntime.hidden = false;
      els.desktopRuntime.textContent = "本地执行";
      els.desktopRuntime.dataset.baseTitle = `Python ${status.python} · ${status.agentRuntime}`;
      els.desktopRuntime.title = els.desktopRuntime.dataset.baseTitle;
      document.documentElement.dataset.runtime = "desktop";
    } catch {
      els.desktopRuntime.hidden = false;
      els.desktopRuntime.textContent = "本地模式";
      els.desktopRuntime.dataset.baseTitle = "本地模式";
    }
    await refreshDesktopContainerCapability({ render: false });
  }
}

function desktopInvoke(command, args = {}) {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new Error("Desktop Core IPC 不可用。");
  return invoke(command, args);
}

async function confirmDesktopAction(message, { title = "OpenRosalind", kind = "warning" } = {}) {
  const nativeConfirm = window.__TAURI__?.dialog?.confirm;
  const approved = typeof nativeConfirm === "function"
    ? await nativeConfirm(message, { title, kind })
    : window.confirm(message);
  if (typeof approved !== "boolean") {
    throw new Error("确认对话框没有返回有效决定。");
  }
  return approved;
}

async function confirmDesktopToolRun(message) {
  return confirmDesktopAction(message, { title: "OpenRosalind 工具授权" });
}

async function loadDesktopProviderProfile() {
  try {
    const [vault, profiles] = await Promise.all([
      desktopInvoke("desktop_credential_vault_status"),
      desktopInvoke("desktop_list_provider_profiles")
    ]);
    const profile = profiles.find((item) => item.isDefault) || profiles[0];
    if (!profile) throw new Error("未找到模型 Provider 配置。");
    state.providerProfileId = profile.id;
    els.baseUrl.value = profile.baseUrl;
    els.model.value = profile.model;
    els.providerStorageNote.textContent = `API Key 安全保存在 ${vault.backend}，不会发送给 OpenRosalind 服务。`;
    els.keyStatus.textContent = profile.hasCredential
      ? `已在 ${vault.backend} 中配置 API Key。留空将保留现有 Key。`
      : `尚未配置 API Key；保存后将写入 ${vault.backend}。`;
    els.clearProviderKey.hidden = !profile.hasCredential;
  } catch (error) {
    els.keyStatus.textContent = `系统凭据库不可用：${String(error.message || error)}`;
    els.clearProviderKey.hidden = true;
  }
}

async function saveDesktopProviderProfile() {
  const apiKey = els.apiKey.value.trim();
  const profile = await desktopInvoke("desktop_save_provider_profile", {
    profileId: state.providerProfileId || null,
    name: "通义千问",
    providerType: "openai_compatible",
    baseUrl: els.baseUrl.value.trim(),
    model: els.model.value.trim(),
    apiKey: apiKey || null,
    setDefault: true
  });
  state.providerProfileId = profile.id;
  els.apiKey.value = "";
  els.apiKey.readOnly = true;
  els.clearProviderKey.hidden = !profile.hasCredential;
  els.keyStatus.textContent = profile.hasCredential
    ? "Provider 配置已保存，API Key 位于系统凭据库。"
    : "Provider 配置已保存，尚未配置 API Key。";
}

async function clearDesktopProviderCredential() {
  const profile = await desktopInvoke("desktop_clear_provider_credential", {
    profileId: state.providerProfileId || null
  });
  els.apiKey.value = "";
  els.apiKey.readOnly = true;
  els.clearProviderKey.hidden = true;
  els.keyStatus.textContent = profile.hasCredential ? "API Key 仍存在。" : "系统凭据库中的 API Key 已清除。";
}

function attachmentBlock() {
  if (!state.uploaded) return "";
  const truncated = state.uploaded.truncated ? "\n[文档过长，内容已截断]" : "";
  return `\n\n---\n附件：${state.uploaded.filename}\n\n${state.uploaded.text}${truncated}\n---`;
}

function isBiologyFunction(functionId = state.functionId) {
  const biologyGroup = functionGroups.find((group) => group.id === "biology_tools");
  return biologyGroup.items.some((item) => item.id === functionId);
}

function proteinSequenceValidationError(value) {
  const text = String(value || "").trim();
  const hasFastaHeader = /(?:^|\n)\s*>/.test(text);
  const compact = text.replace(/\s+/g, "");
  const looksLikeRawSequence = compact.length >= 10 && /^[A-Za-z0-9*.-]+$/.test(compact);
  if (!hasFastaHeader && !looksLikeRawSequence) return "";

  const lines = text.split(/\r?\n/);
  const sequenceLines = [];
  let collecting = !hasFastaHeader;
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (line.startsWith(">")) {
      collecting = true;
      continue;
    }
    if (collecting && line) {
      const looksLikeInstruction = /[\u3400-\u9fff]|\s|[，。！？；：]/.test(line);
      if (hasFastaHeader && looksLikeInstruction) collecting = false;
      else sequenceLines.push(line);
    }
  }
  const symbols = sequenceLines.join("").toUpperCase().split("")
    .filter((character) => !/\s/.test(character) && !["-", "."].includes(character));
  if (!symbols.length) return "FASTA 标题后未找到序列。请将序列放在标题下一行；本次未执行 BLAST。";

  const letters = symbols.filter((character) => /^[A-Z*]$/.test(character));
  const basicNucleotide = new Set(["A", "C", "G", "T", "U"]);
  const standardAminoAcid = new Set("ACDEFGHIKLMNPQRSTVWY*".split(""));
  const nucleotideFraction = letters.length
    ? letters.filter((character) => basicNucleotide.has(character)).length / letters.length
    : 0;
  const expected = nucleotideFraction >= 0.5 ? basicNucleotide : standardAminoAcid;
  const invalid = [...new Set(symbols.filter((character) => !expected.has(character)))];
  if (invalid.length) {
    return `无法可靠判定序列类型。检测到非法或不兼容字符：${invalid.join("、")}。请提供仅包含标准核酸或氨基酸字符的 FASTA 序列；本次未执行 BLAST。`;
  }
  if (nucleotideFraction >= 0.9 && letters.length >= 8) {
    return "输入内容更像核酸序列，不适用于蛋白质分析。请改用序列分析工具；本次未执行 BLAST。";
  }
  return "";
}

function uploadHint() {
  return isBiologyFunction()
    ? "支持 FASTA（蛋白序列自动 BLAST）、FASTQ、GenBank 和序列文本，最大 12 MB"
    : "支持 PDF、BibTeX、DOCX 和文本，最大 12 MB";
}

function updateUploadContext() {
  els.documentFile.accept = isBiologyFunction()
    ? ".fa,.fasta,.faa,.fna,.ffn,.frn,.fastq,.fq,.gb,.gbk,.genbank,.aln,.clustal,.phy,.phylip,.pdb,.cif,.mmcif,.txt"
    : ".pdf,.bib,.txt,.md,.markdown,.csv,.tsv,.json,.docx";
  if (!state.uploaded) setUploadStatus(uploadHint());
}

function clearAttachment() {
  state.uploaded = null;
  els.documentFile.value = "";
  els.attachmentChip.hidden = true;
  setUploadStatus(uploadHint());
}

function showAttachment(upload) {
  els.attachmentName.textContent = upload.filename;
  els.attachmentMeta.textContent = `${upload.chars} 字符${upload.truncated ? "，已截断" : ""}`;
  els.attachmentChip.hidden = false;
}

async function uploadFile(file) {
  if (!file) return;
  setUploadStatus(`解析中：${file.name}`);
  const form = new FormData();
  form.append("document", file);
  try {
    const response = await authenticatedFetch("/api/upload", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "上传解析失败");
    }
    state.uploaded = data;
    showAttachment(data);
    setUploadStatus(`已解析：${data.filename}`);
  } catch (error) {
    clearAttachment();
    setUploadStatus(String(error), "error");
  }
}

function historyForApi() {
  return currentSession().slice(-8).map((item) => ({
    role: item.role === "assistant" ? "assistant" : "user",
    content: item.requestContent || item.content
  }));
}

async function verifyReferences(requestInput, displayInput) {
  setBadge("verifying");
  try {
    const response = await authenticatedFetch("/api/verify-references", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: state.uploaded ? state.uploaded.text : requestInput })
    });
    const data = await response.json();
    const content = data.content || data.error || "No verification output.";
    addSessionMessage("user", displayInput, { requestContent: requestInput });
    addSessionMessage("assistant", content, {
      skill: currentFunction().skill,
      sources: data.sources,
      trace: data.trace
    });
    setBadge(response.ok ? "verified" : "error", response.ok ? "" : "error");
  } catch (error) {
    addSessionMessage("user", displayInput, { requestContent: requestInput });
    addSessionMessage("assistant", String(error), { skill: currentFunction().skill });
    setBadge("error", "error");
  }
}

async function executeBiologyTool(item, input, displayInput) {
  setBadge("tool running");
  const validationError = item.id === "protein_analysis"
    ? proteinSequenceValidationError(state.uploaded?.text || input)
    : "";
  if (validationError) {
    addSessionMessage("user", displayInput, { requestContent: input });
    addSessionMessage("assistant", `## 无法识别该序列\n\n${validationError}`, {
      skill: item.skill,
      trace: [{
        title: "本地校验生物序列",
        kind: "tool",
        confidence: 99,
        detail: "检测序列字符集并在外部查询前中止无效输入；本次没有执行 BLAST。"
      }]
    });
    setBadge("invalid sequence", "error");
    return;
  }
  try {
    const response = await authenticatedFetch("/api/biology/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool: item.id,
        input,
        attachment: state.uploaded?.text || ""
      })
    });
    const data = await response.json();
    const content = data.content || data.error || "工具没有返回结果。";
    addSessionMessage("user", displayInput, { requestContent: input });
    addSessionMessage("assistant", content, {
      skill: item.skill,
      sources: data.sources,
      trace: data.trace
    });
    setBadge(data.ok ? "tool result" : "error", data.ok ? "" : "error");
  } catch (error) {
    addSessionMessage("user", displayInput, { requestContent: input });
    addSessionMessage("assistant", String(error.message || error), { skill: item.skill });
    setBadge("error", "error");
  }
}

function planMarkdown(plan, summary = "") {
  const lines = ["# Agent 任务计划", ""];
  if (summary) lines.push(summary, "");
  lines.push(`**状态：** ${plan.status}`, "", `**目标：** ${plan.goal}`, "", "## 执行步骤", "");
  for (const step of plan.steps || []) {
    lines.push(`${step.position}. **${step.title}**`, `   - Skill：\`${step.skill}\``, `   - ${step.instruction}`, "");
  }
  lines.push("> 请使用下方按钮确认或取消。确认后任务会提交后台执行，你可以关闭页面；工具和数据库结果仍需人工核验。");
  return lines.join("\n");
}

function chatContainingMessage(message) {
  return state.chats.find((chat) => chat.messages.some((item) => item.id === message.id)) || null;
}

function addMessageToChat(chat, role, content, extras = {}) {
  const message = normalizeMessage({ id: makeMessageId(), role, content, ...extras });
  chat.messages.push(message);
  chat.updatedAt = new Date().toISOString();
  return message;
}

function refreshAgentPlanMessage(message) {
  const chat = chatContainingMessage(message);
  if (chat) chat.updatedAt = new Date().toISOString();
  persistChats();
  renderChatHistory();
  if (chat?.id === state.activeChatId) renderConversation();
}

function cancelAgentPlan(message) {
  if (message.agentPlan?.status !== "pending") return;
  message.agentPlan.status = "cancelled";
  message.agentPlan.error = "";
  setBadge("plan cancelled");
  refreshAgentPlanMessage(message);
}

function renderAgentPlanApproval(message) {
  const plan = message.agentPlan;
  const card = document.createElement("section");
  card.className = `agent-plan-approval ${plan.status}`;
  card.setAttribute("aria-live", "polite");

  const copy = document.createElement("div");
  const title = document.createElement("strong");
  const detail = document.createElement("span");
  const labels = {
    pending: ["等待你的确认", "确认后才会提交后台；取消不会执行任何步骤。"],
    starting: ["正在提交任务", "正在确认计划并加入后台队列…"],
    running: ["后台任务运行中", plan.jobId ? `任务 ID：${plan.jobId}` : "任务已经进入后台队列。"],
    submitted: ["正在恢复后台任务状态", plan.error || (plan.jobId ? `任务 ID：${plan.jobId}，页面会自动更新结果。` : "页面会自动更新结果。")],
    completed: ["后台任务已完成", "最终结果已追加到对话；执行记录和产物可在回答下方查看。"],
    failed: ["后台任务失败", plan.error || "请稍后重试或在科研项目中检查任务状态。"],
    cancelled: ["已取消", "该计划没有提交后台执行。"]
  };
  const [titleText, detailText] = labels[plan.status] || labels.pending;
  title.textContent = titleText;
  detail.textContent = detailText;
  copy.append(title, detail);
  card.appendChild(copy);

  if (plan.status === "pending") {
    const actions = document.createElement("div");
    actions.className = "agent-plan-approval-actions";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "agent-plan-cancel";
    cancel.textContent = "取消";
    cancel.addEventListener("click", () => cancelAgentPlan(message));
    const approve = document.createElement("button");
    approve.type = "button";
    approve.className = "agent-plan-confirm";
    approve.textContent = "确认并运行";
    approve.addEventListener("click", () => runApprovedAgentPlan(message));
    actions.append(cancel, approve);
    card.appendChild(actions);
  } else if (["starting", "running"].includes(plan.status)) {
    const activity = document.createElement("span");
    activity.className = "agent-plan-activity";
    activity.setAttribute("aria-hidden", "true");
    card.appendChild(activity);
  }
  return card;
}

function agentProcessForPlan(plan) {
  const toolSkills = new Set(["evidence-manager", "reference-verification", "python-sandbox", "tool-audit", "gene_annotation", "protein_analysis", "mutation_assessment", "pathway_analysis"]);
  return (plan.steps || []).map((step, index) => ({
    position: Number(step.position || index + 1),
    title: String(step.title || `步骤 ${index + 1}`),
    skill: String(step.skill || ""),
    status: String(step.status || "unknown"),
    attempts: Number(step.attempts || 0),
    instruction: String(step.instruction || ""),
    output: String(step.output || ""),
    error: String(step.error || ""),
    confidence: step.status === "completed" ? (toolSkills.has(String(step.skill || "")) ? 90 : 72) : 40
  }));
}

function completedPlanMarkdown(plan) {
  const steps = plan.steps || [];
  const finalStep = [...steps].reverse().find((step) => step.status === "completed" && String(step.output || "").trim());
  if (!finalStep) {
    const completed = steps.filter((step) => step.status === "completed").length;
    return `# Agent 任务完成\n\n已完成 ${completed}/${steps.length} 个执行步骤。完整执行记录可在回答下方查看。`;
  }
  let output = String(finalStep.output || "")
    .replace(/<!--\s*runtime:[\s\S]*?-->/gi, "")
    .replace(/```(?:python|py)\s*\n[\s\S]*?```/gi, "\n> Python 代码已移至回答下方的“执行过程”。\n")
    .trim();
  if (output.length > 12_000) {
    const boundary = output.lastIndexOf("\n", 12_000);
    output = `${output.slice(0, boundary > 8_000 ? boundary : 12_000).trim()}\n\n> 聊天区仅展示摘要，完整报告请使用下方下载入口。`;
  }
  return output;
}

async function fetchProjectArtifacts(projectId) {
  if (!projectId) return [];
  try {
    const data = await agentRequest(`/api/projects/${projectId}/artifacts`);
    return Array.isArray(data.artifacts) ? data.artifacts : [];
  } catch {
    return [];
  }
}

async function hydrateCompletedAgentArtifacts() {
  const cache = new Map();
  let changed = false;
  for (const chat of state.chats) {
    for (const message of chat.messages) {
      if (message.agentPlan?.status !== "completed" || !message.agentPlan.resultMessageId) continue;
      const result = chat.messages.find((entry) => entry.id === message.agentPlan.resultMessageId);
      if (!result || result.artifacts?.length) continue;
      const projectId = message.agentPlan.projectId || state.projectId;
      if (!projectId) continue;
      if (!cache.has(projectId)) cache.set(projectId, await fetchProjectArtifacts(projectId));
      result.artifacts = cache.get(projectId);
      message.agentPlan.projectId = projectId;
      changed = true;
    }
  }
  if (changed) {
    persistChats();
    renderConversation();
  }
}

async function applyAgentTaskResult(message, chat, task) {
  const planCompleted = task.plan?.status === "completed";
  message.agentPlan.status = planCompleted ? "completed" : "failed";
  message.agentPlan.error = task.error || task.plan?.steps?.find((step) => step.error)?.error || "";
  message.agentPlan.projectId = String(task.plan?.projectId || message.agentPlan.projectId || state.projectId || "");
  if (task.plan && !message.agentPlan.resultMessageId) {
    const artifacts = await fetchProjectArtifacts(message.agentPlan.projectId);
    const result = addMessageToChat(chat, "assistant", completedPlanMarkdown(task.plan), {
      skill: "research_assistant",
      agentProcess: agentProcessForPlan(task.plan),
      artifacts,
      trace: (task.plan.steps || []).map((step) => ({
        title: `${step.position}. ${step.title}`,
        kind: String(step.output || "").includes("OpenHands") ? "tool" : "reasoning",
        confidence: step.status === "completed" ? (String(step.output || "").includes("OpenHands") ? 90 : 72) : 40,
        detail: `Skill：${step.skill}；状态：${step.status}；尝试次数：${step.attempts}。`
      }))
    });
    message.agentPlan.resultMessageId = result.id;
  }
  if (task.status === "failed" && task.error && !message.agentPlan.resultMessageId) {
    const result = addMessageToChat(chat, "assistant", `## 后台任务失败\n\n${task.error.split("\n").slice(-4).join("\n")}`, { skill: "research_assistant" });
    message.agentPlan.resultMessageId = result.id;
  }
  if (chat.id === state.activeChatId) setBadge(`Agent ${message.agentPlan.status}`, planCompleted ? "" : "error");
  if (!state.chats.some((item) => item.messages.some((entry) => ["running", "submitted", "starting"].includes(entry.agentPlan?.status)))) {
    setAgentExecutionLock(false);
  }
  refreshAgentPlanMessage(message);
}

function monitorAgentPlan(message, chat) {
  const jobId = message.agentPlan?.jobId;
  if (!jobId || agentPlanPolls.has(jobId)) return agentPlanPolls.get(jobId);
  const terminal = new Set(["finished", "failed", "stopped", "canceled"]);
  const polling = (async () => {
    while (state.user && ["running", "submitted"].includes(message.agentPlan.status)) {
      try {
        const data = await agentRequest(`/api/tasks/${jobId}/status`);
        const task = data.task;
        if (terminal.has(task.status)) {
          await applyAgentTaskResult(message, chat, task);
          return;
        }
        if (message.agentPlan.status !== "running") {
          message.agentPlan.status = "running";
          refreshAgentPlanMessage(message);
        }
      } catch (error) {
        if (!state.user) return;
        message.agentPlan.status = "submitted";
        message.agentPlan.error = `暂时无法获取任务状态：${String(error.message || error)}`;
        refreshAgentPlanMessage(message);
      }
      await new Promise((resolve) => setTimeout(resolve, 3000));
    }
  })().finally(() => agentPlanPolls.delete(jobId));
  agentPlanPolls.set(jobId, polling);
  return polling;
}

function resumeAgentPlanPolling() {
  for (const chat of state.chats) {
    for (const message of chat.messages) {
      if (message.agentPlan?.jobId && ["running", "submitted"].includes(message.agentPlan.status)) {
        setAgentExecutionLock(true);
        monitorAgentPlan(message, chat);
      }
    }
  }
}

async function runApprovedAgentPlan(message) {
  if (message.agentPlan?.status !== "pending") return;
  const chat = chatContainingMessage(message);
  if (!chat) return;
  message.agentPlan.status = "starting";
  message.agentPlan.error = "";
  setAgentExecutionLock(true);
  setBadge("submitting Agent");
  refreshAgentPlanMessage(message);

  try {
    await agentRequest(`/api/plans/${message.agentPlan.planId}/confirm`, { method: "POST" });
    const queued = await agentRequest(`/api/plans/${message.agentPlan.planId}/run-all`, { method: "POST" });
    message.agentPlan.status = "running";
    message.agentPlan.jobId = queued.task.jobId;
    setBadge(`Agent ${queued.task.status}`);
    refreshAgentPlanMessage(message);
    monitorAgentPlan(message, chat);
  } catch (error) {
    message.agentPlan.status = "failed";
    message.agentPlan.error = String(error.message || error);
    addMessageToChat(chat, "assistant", `## Agent 执行失败\n\n${message.agentPlan.error}`, { skill: "research_assistant" });
    setBadge("error", "error");
    setAgentExecutionLock(false);
  } finally {
    refreshAgentPlanMessage(message);
  }
}

async function executeAgentTask(input, displayInput) {
  setBadge("planning");
  try {
    if (!state.projectId) await loadProjects();
    const generated = await agentRequest(`/api/projects/${state.projectId}/plans/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        goal: input,
        apiKey: els.apiKey.value.trim(),
        baseUrl: els.baseUrl.value.trim(),
        model: els.model.value.trim()
      })
    });
    addSessionMessage("user", displayInput, { requestContent: input });
    addSessionMessage("assistant", planMarkdown(generated.plan, generated.summary), {
      skill: "research_assistant",
      agentPlan: { planId: generated.plan.id, status: "pending", jobId: "", error: "", projectId: state.projectId },
      trace: [
        { title: "读取项目记忆与用户目标", kind: "tool", confidence: 92, detail: "从当前科研项目中读取已保存的事实、证据、限制和开放问题。" },
        { title: "生成可确认的 Agent 计划", kind: "reasoning", confidence: 68, detail: "模型将目标拆分为可审计步骤；执行前需要用户确认。" }
      ]
    });
    renderConversation();
    setBadge("awaiting approval");
  } catch (error) {
    addSessionMessage("assistant", `## Agent 执行失败\n\n${String(error.message || error)}`, { skill: "research_assistant" });
    setBadge("error", "error");
  }
}

function shouldVerifyReferences(item, input) {
  if (item.deterministic === "verifyRefs") return true;
  if (item.id !== "research_assistant") return false;
  if (state.uploaded?.kind === "bibliography" || state.uploaded?.extension === ".bib") return true;
  return /(参考文献|doi|pmid)/i.test(input) && /(验证|核验|真假|真实|存在)/.test(input);
}

async function generate(requestInput, displayInput) {
  els.sendButton.disabled = true;
  setBadge("running");
  try {
    const response = await authenticatedFetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        skill: currentFunction().skill,
        input: requestInput,
        history: historyForApi(),
        apiKey: els.apiKey.value.trim(),
        baseUrl: els.baseUrl.value.trim(),
        model: els.model.value.trim(),
        temperature: els.temperature.value
      })
    });
    const data = await response.json();
    const content = data.content || data.error || "No output.";
    addSessionMessage("user", displayInput, { requestContent: requestInput });
    addSessionMessage("assistant", content, {
      skill: currentFunction().skill,
      sources: data.sources,
      trace: data.trace
    });
    setBadge(data.mode || "done", data.ok ? "" : "error");
  } catch (error) {
    addSessionMessage("user", displayInput, { requestContent: requestInput });
    addSessionMessage("assistant", String(error), { skill: currentFunction().skill });
    setBadge("error", "error");
  } finally {
    els.sendButton.disabled = false;
  }
}

function providerRequestId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function generateWithDesktopProvider(requestInput, displayInput) {
  els.sendButton.disabled = true;
  setBadge("preparing local model");
  let unlisten = null;
  try {
    const prepared = await agentRequest("/api/desktop/model-request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        skill: currentFunction().skill,
        input: requestInput,
        history: historyForApi()
      })
    });
    const requestId = providerRequestId();
    const listen = window.__TAURI__?.event?.listen;
    if (listen) {
      unlisten = await listen("desktop-provider-delta", (event) => {
        if (event.payload?.requestId === requestId) {
          setBadge(`local streaming ${event.payload.index}`);
        }
      });
    }
    const result = await desktopInvoke("desktop_stream_provider_chat", {
      profileId: state.providerProfileId || null,
      requestId,
      messages: prepared.messages,
      temperature: Number(els.temperature.value)
    });
    addSessionMessage("user", displayInput, { requestContent: requestInput });
    addSessionMessage("assistant", result.content || "No output.", {
      skill: currentFunction().skill,
      trace: [
        {
          title: "Desktop Core 直连模型 Provider",
          kind: "model",
          confidence: 85,
          detail: `${result.model} · ${result.elapsedMillis} ms · API Key 未进入 Web/Python 服务`
        }
      ]
    });
    setBadge("local provider");
  } catch (error) {
    addSessionMessage("user", displayInput, { requestContent: requestInput });
    addSessionMessage("assistant", `## 本地模型调用失败\n\n${String(error.message || error)}`, {
      skill: currentFunction().skill
    });
    setBadge("error", "error");
  } finally {
    if (unlisten) unlisten();
    els.sendButton.disabled = false;
  }
}

async function desktopAgentConversation() {
  const chatId = activeChat().id;
  const contextId = `${chatId}:${state.projectId || "no-project"}`;
  if (state.desktopConversationIds[contextId]) return state.desktopConversationIds[contextId];
  const conversation = await desktopInvoke("desktop_create_conversation", {
    title: activeChat().title || "Research Assistant",
    projectId: state.projectId || null
  });
  state.desktopConversationIds[contextId] = conversation.id;
  return conversation.id;
}

async function generateWithDesktopAgent(requestInput, displayInput) {
  els.sendButton.disabled = true;
  setBadge("starting local agent");
  let unlisten = null;
  try {
    const prepared = await agentRequest("/api/desktop/model-request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        skill: currentFunction().skill,
        input: requestInput,
        history: historyForApi()
      })
    });
    const conversationId = await desktopAgentConversation();
    const job = await desktopInvoke("desktop_create_agent_job", {
      conversationId,
      request: {
        mode: "agent",
        providerProfileId: state.providerProfileId || null,
        messages: prepared.messages,
        temperature: Number(els.temperature.value)
      }
    });
    const listen = window.__TAURI__?.event?.listen;
    if (listen) {
      unlisten = await listen("desktop-provider-delta", (event) => {
        setBadge(`agent streaming ${event.payload?.index || 0}`);
      });
    }
    let detail = await desktopInvoke("desktop_start_agent_job", { jobId: job.id });
    for (let attempt = 0; attempt < 120 && ["queued", "running", "cancelling"].includes(detail.job.status); attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 50));
      detail = await desktopInvoke("desktop_refresh_agent_job", { jobId: job.id });
    }
    const result = detail.job.result || {};
    if (detail.job.status !== "completed") {
      throw new Error(result.error || `AgentJob ended with status ${detail.job.status}`);
    }
    const toolRuns = Array.isArray(result.toolRuns) ? result.toolRuns : [];
    addSessionMessage("user", displayInput, { requestContent: requestInput });
    addSessionMessage("assistant", result.content || "No output.", {
      skill: currentFunction().skill,
      agentJobId: job.id,
      agentProcess: toolRuns.map((toolRun, index) => ({
        position: index + 1,
        title: String(toolRun.toolName || "本地工具"),
        skill: "desktop-tool-contract",
        status: String(toolRun.status || "unknown"),
        attempts: 1,
        instruction: `Desktop Core 校验并执行 ${String(toolRun.toolName || "Tool Contract")}`,
        output: JSON.stringify(toolRun.output ?? { error: toolRun.error || "" }, null, 2),
        error: String(toolRun.error || ""),
        confidence: toolRun.status === "succeeded" ? 95 : 30
      })),
      trace: [
        {
          title: "本地 AgentJob · Tool Agent v4",
          kind: "agent",
          confidence: 88,
          detail: `${result.model || "configured model"} · ${detail.events.length} events · ${toolRuns.length} 个 ToolRun · Worker 未接触 API Key`
        },
        ...toolRuns.map((toolRun) => ({
          title: `Tool Contract · ${String(toolRun.toolName || "unknown")}`,
          kind: "tool",
          confidence: toolRun.status === "succeeded" ? 95 : 30,
          detail: `${String(toolRun.status || "unknown")} · ${String(toolRun.toolRunId || "未创建 ToolRun")}`
        }))
      ]
    });
    setBadge("local agent");
  } catch (error) {
    addSessionMessage("user", displayInput, { requestContent: requestInput });
    addSessionMessage("assistant", `## 本地 Agent 执行失败\n\n${String(error.message || error)}`, {
      skill: currentFunction().skill
    });
    setBadge("error", "error");
  } finally {
    if (unlisten) unlisten();
    els.sendButton.disabled = false;
  }
}

async function sendMessage() {
  if (state.isSending) return;
  const input = els.taskInput.value.trim();
  if (!input && !state.uploaded) {
    els.taskInput.focus();
    return;
  }

  const item = currentFunction();
  const displayParts = [];
  if (input) displayParts.push(input);
  if (state.uploaded) displayParts.push(`[附件] ${state.uploaded.filename}`);
  const displayInput = displayParts.join("\n\n");
  const requestInput = `${item.template}\n\n用户请求：${input || "请处理附件内容。"}${attachmentBlock()}`;

  state.isSending = true;
  closeAccountMenu();
  els.newChat.disabled = true;
  els.sidebarAccount.disabled = true;
  els.sendButton.disabled = true;
  document.querySelectorAll(".chat-history-item, .function-item, .standalone-function, .manage-agents").forEach((button) => {
    button.disabled = true;
  });
  prepareActiveChatForMessage(displayInput);
  els.taskInput.value = "";
  appendMessage("user", displayInput);
  const pending = document.createElement("article");
  pending.className = "message assistant pending";
  const pendingText = document.createElement("span");
  pendingText.textContent = "处理中";
  const pendingDots = document.createElement("span");
  pendingDots.className = "pending-dots";
  pendingDots.setAttribute("aria-label", "...");
  for (let index = 0; index < 3; index += 1) {
    const dot = document.createElement("span");
    dot.textContent = ".";
    pendingDots.appendChild(dot);
  }
  pending.append(pendingText, pendingDots);
  els.conversation.appendChild(pending);
  els.conversation.scrollTop = els.conversation.scrollHeight;

  try {
    if (item.id === "research_assistant" && state.desktopMode) {
      await generateWithDesktopAgent(requestInput, displayInput);
    } else if (item.id === "research_assistant") {
      await executeAgentTask(input, displayInput);
    } else if (["protein_analysis", "mutation_assessment"].includes(item.id)) {
      await executeBiologyTool(item, input, displayInput);
    } else if (shouldVerifyReferences(item, input)) {
      await verifyReferences(input || state.uploaded.text, displayInput);
    } else if (state.desktopMode) {
      await generateWithDesktopProvider(requestInput, displayInput);
    } else {
      await generate(requestInput, displayInput);
    }
  } finally {
    clearAttachment();
    state.isSending = false;
    els.newChat.disabled = false;
    els.sidebarAccount.disabled = false;
    els.sendButton.disabled = false;
    document.querySelectorAll(".function-item, .standalone-function, .manage-agents").forEach((button) => {
      button.disabled = false;
    });
    renderConversation();
    els.taskInput.focus();
  }
}

function copyLatestAnswer() {
  const latest = [...currentSession()].reverse().find((item) => item.role === "assistant");
  if (!latest) return;
  navigator.clipboard.writeText(latest.content).then(() => setBadge("Markdown copied"));
}

function closeAccountMenu() {
  els.accountMenu.hidden = true;
  els.sidebarAccount.setAttribute("aria-expanded", "false");
}

function toggleAccountMenu() {
  const willOpen = els.accountMenu.hidden;
  els.accountMenu.hidden = !willOpen;
  els.sidebarAccount.setAttribute("aria-expanded", String(willOpen));
}

function clearCurrentChat() {
  const chat = activeChat();
  chat.messages = [];
  chat.title = "新对话";
  chat.updatedAt = new Date().toISOString();
  closeDetailPanel();
  clearAttachment();
  closeAccountMenu();
  persistChats();
  renderChatHistory();
  renderConversation();
  setBadge("ready");
}

function startNewChat() {
  closeDetailPanel();
  const chat = activeChat();
  if (!chat.messages.some((message) => message.role === "user") || !chat.messages.some((message) => message.role === "assistant")) {
    if (chat.messages.length === 0) {
      chat.functionId = "research_assistant";
      chat.title = "新对话";
      chat.updatedAt = new Date().toISOString();
      state.functionId = chat.functionId;
      persistChats();
      renderChatHistory();
      selectFunction(chat.functionId, { updateChat: false });
    }
    return;
  }
  const reusableEmptyChat = state.chats.find((item) => item.id !== chat.id && item.messages.length === 0);
  if (reusableEmptyChat) {
    reusableEmptyChat.functionId = "research_assistant";
    reusableEmptyChat.title = "新对话";
    reusableEmptyChat.updatedAt = new Date().toISOString();
    switchChat(reusableEmptyChat.id);
    return;
  }
  createChat("research_assistant");
}

function bindEvents() {
  window.addEventListener("focus", () => {
    void refreshDesktopContainerCapability();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") void refreshDesktopContainerCapability();
    else persistChats();
  });
  window.addEventListener("beforeunload", persistChats);
  els.loginMode.addEventListener("click", () => setAuthMode("login"));
  els.registerMode.addEventListener("click", () => setAuthMode("register"));
  els.authForm.addEventListener("submit", submitAuth);
  els.logout.addEventListener("click", logout);
  els.newChat.addEventListener("click", () => {
    closeAccountMenu();
    clearAttachment();
    startNewChat();
  });
  els.sidebarAccount.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleAccountMenu();
  });
  els.accountMenu.addEventListener("click", (event) => event.stopPropagation());
  els.closeDetailPanel.addEventListener("click", closeDetailPanel);
  document.addEventListener("click", closeAccountMenu);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAccountMenu();
      closeDetailPanel();
    }
  });
  els.projectSelect.addEventListener("change", () => {
    state.projectId = els.projectSelect.value;
    renderProjectDirectoryAuthorization(null);
    setBadge("project switched");
  });
  els.newProject.addEventListener("click", createProjectFromUi);
  els.openProject.addEventListener("click", openProjectDialog);
  els.authorizeProjectDirectory.addEventListener("click", authorizeProjectDirectory);
  els.revealProjectDirectory.addEventListener("click", revealProjectDirectory);
  els.scanProjectFiles.addEventListener("click", scanProjectFiles);
  els.revokeProjectDirectory.addEventListener("click", () => {
    void revokeProjectDirectory().catch((error) => {
      setBadge("error", "error");
      window.alert(String(error.message || error));
    });
  });
  els.addMemory.addEventListener("click", addProjectMemory);
  els.agentDialog.addEventListener("close", () => {
    if (els.agentDialog.returnValue === "save") saveAgentChoices();
  });
  els.resetAgents.addEventListener("click", () => {
    if (state.managingGroupId === "paper_assistant") {
      state.paperAgentIds = [...DEFAULT_PAPER_AGENT_IDS];
      localStorage.setItem("rosalind.paperAgents", JSON.stringify(state.paperAgentIds));
    } else {
      state.biologyToolIds = [...DEFAULT_BIOLOGY_TOOL_IDS];
      localStorage.setItem("rosalind.biologyTools", JSON.stringify(state.biologyToolIds));
    }
    renderAgentChoices();
  });
  els.sendButton.addEventListener("click", sendMessage);
  els.taskInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });
  els.documentFile.addEventListener("change", () => uploadFile(els.documentFile.files[0]));
  els.removeAttachment.addEventListener("click", clearAttachment);
  els.copyOutput.addEventListener("click", copyLatestAnswer);
  els.clearChat.addEventListener("click", clearCurrentChat);
  els.openSettings.addEventListener("click", () => {
    closeAccountMenu();
    els.apiKey.value = "";
    els.apiKey.readOnly = true;
    els.settingsDialog.showModal();
  });
  els.apiKey.addEventListener("focus", () => {
    els.apiKey.readOnly = false;
  });
  els.apiKey.addEventListener("blur", () => {
    if (!els.apiKey.value) els.apiKey.readOnly = true;
  });
  els.openProject.addEventListener("click", closeAccountMenu);
  els.newProject.addEventListener("click", closeAccountMenu);
  els.settingsDialog.addEventListener("click", (event) => {
    if (event.target === els.settingsDialog) els.settingsDialog.close();
  });
  els.settingsDialog.querySelector("form").addEventListener("submit", async (event) => {
    if (!state.desktopMode || event.submitter?.value !== "done") return;
    event.preventDefault();
    try {
      await saveDesktopProviderProfile();
      els.settingsDialog.close("done");
    } catch (error) {
      els.keyStatus.textContent = String(error.message || error);
    }
  });
  els.clearProviderKey.addEventListener("click", async () => {
    try {
      await clearDesktopProviderCredential();
    } catch (error) {
      els.keyStatus.textContent = String(error.message || error);
    }
  });
  els.temperature.addEventListener("input", () => {
    els.temperatureValue.textContent = els.temperature.value;
  });
}

async function init() {
  drawSignal("authSignalCanvas");
  bindEvents();
  setAuthMode("login");
  await checkAuth();
}

init();
