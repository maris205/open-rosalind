const agentGroups = [
  {
    id: "agent",
    title: "Agent 正式版",
    agents: [
      {
        id: "agent_planner",
        title: "任务规划 Agent",
        skill: "agent-planner",
        purpose: "把科研目标拆成可审批、可执行、可追溯的任务计划。",
        template: "请把下面的科研目标拆解成一个可审批的 Agent 执行计划。请列出步骤、工具、输入来源、输出、权限等级、风险和需要我确认的地方。\n\n科研目标："
      },
      {
        id: "memory_manager",
        title: "Memory Agent",
        skill: "memory-manager",
        purpose: "维护项目记忆、证据记忆、任务记忆和决策记录。",
        template: "请把下面的信息整理成 Open-Rosalind Agent 的结构化 memory update。区分用户提供事实、证据、推断、决策和开放问题。\n\n信息："
      },
      {
        id: "tool_audit",
        title: "工具审计 Agent",
        skill: "tool-audit",
        purpose: "审查工具调用的权限、输入来源、输出和可复现性。",
        template: "请审计以下计划中或已完成的工具调用。请检查权限等级、输入来源、输出、失败风险、可复现性和是否需要人工确认。\n\n工具调用记录或计划："
      },
      {
        id: "agent_report_builder",
        title: "可追溯报告 Agent",
        skill: "agent-report-builder",
        purpose: "把任务计划、证据、工具日志和结论编成可追溯报告。",
        template: "请根据以下任务计划、证据、工具日志和结论生成可追溯研究报告。每个主要结论都要连接证据或标注未验证。\n\n材料："
      }
    ]
  },{
    id: "reading",
    title: "文献阅读",
    agents: [
      {
        id: "paper_summary",
        title: "论文精读 Agent",
        skill: "paper_summary",
        purpose: "上传或粘贴论文后，生成结构化精读笔记。",
        template: "请帮我精读这篇生物医学论文。请输出一句话总结、研究背景、核心问题、研究对象/数据来源、方法概述、主要结果、作者结论、局限性、可引用点和需要人工核验的点。\n\n论文内容如下：\n"
      },
      {
        id: "paper_qa",
        title: "论文问答 Agent",
        skill: "paper_summary",
        purpose: "围绕已上传论文继续追问方法、结果、图表和局限。",
        template: "请基于下面论文内容回答我的问题。回答时区分论文原文信息和你的推断。\n\n论文内容：\n\n我的问题："
      }
    ]
  },
  {
    id: "review",
    title: "综述与选题",
    agents: [
      {
        id: "literature_review",
        title: "综述大纲 Agent",
        skill: "literature_review",
        purpose: "围绕主题生成综述框架、检索词和图表思路。",
        template: "请围绕以下主题生成一个生物医学综述大纲，包括章节结构、每节写作要点、推荐检索关键词、潜在图表设计和需要核验的科学问题。\n\n主题："
      },
      {
        id: "thesis_proposal",
        title: "开题报告 Agent",
        skill: "thesis_proposal",
        purpose: "把研究方向整理成开题报告草稿。",
        template: "请围绕以下研究方向生成开题报告草稿，包括研究背景、科学问题、研究目标、研究内容、技术路线、创新点、可行性分析、预期结果和时间计划。\n\n研究方向："
      }
    ]
  },
  {
    id: "writing",
    title: "论文写作",
    agents: [
      {
        id: "introduction_draft",
        title: "Introduction Agent",
        skill: "introduction_draft",
        purpose: "生成 Introduction / Background 的谨慎初稿。",
        template: "请为以下研究主题生成 Introduction 初稿。所有需要文献支持的位置用 [需要引用] 标注，不要伪造引用。\n\n研究主题与已有信息："
      },
      {
        id: "discussion_draft",
        title: "Discussion Agent",
        skill: "discussion_draft",
        purpose: "基于用户提供的结果写 Discussion，不编造结果。",
        template: "请基于以下研究结果生成 Discussion 初稿。不要添加我没有提供的结果，不要从相关性直接推出因果。\n\n研究目标：\n\n主要结果：\n\n图表说明："
      },
      {
        id: "manuscript_polish",
        title: "论文润色 Agent",
        skill: "manuscript_polish",
        purpose: "润色中英文生医论文段落，保留科学含义。",
        template: "请润色下面这段学术文本。要求保持科学含义不变，提高逻辑、清晰度和学术表达，并指出可能存在的科学表述风险。\n\n文本：\n"
      }
    ]
  },
  {
    id: "verification",
    title: "引用与核验",
    agents: [
      {
        id: "reference_verification",
        title: "参考文献验证 Agent",
        skill: "reference_verification",
        purpose: "检查参考文献是否真实存在、DOI/PMID 和元数据是否一致。",
        template: "请验证以下参考文献是否真实存在，并检查 DOI、PMID、题名、作者、期刊和年份是否一致。每条参考文献请单独成行。\n\n参考文献：\n",
        deterministic: "verifyRefs"
      },
      {
        id: "citation_check",
        title: "Claim 证据核验 Agent",
        skill: "citation_check",
        purpose: "判断正文 claim 是否需要引用、需要哪类证据和风险等级。",
        template: "请检查以下 claim 是否需要引用、需要哪类证据、风险等级是什么，并给出谨慎改写建议。若我提供了参考文献，请只判断其可能相关性，不要声称一定支持。\n\nClaim：\n\n参考文献或摘要："
      }
    ]
  },
  {
    id: "learning",
    title: "学习辅导",
    agents: [
      {
        id: "homework_tutor",
        title: "课程/作业辅导 Agent",
        skill: "homework_tutor",
        purpose: "解释题目、拆解思路、给出草稿和自查点。",
        template: "请用学习辅导的方式帮我完成下面任务：先解释题目和知识点，再给出思路和示例草稿，最后列出我需要自己完善的地方。\n\n任务："
      }
    ]
  }
];

const agents = Object.fromEntries(agentGroups.flatMap((group) => group.agents.map((agent) => [agent.id, agent])));
const templates = {
  paper: agents.paper_summary,
  review: agents.literature_review,
  polish: agents.manuscript_polish,
  proposal: agents.thesis_proposal,
  refs: agents.reference_verification
};

const state = {
  agentId: "paper_summary",
  skill: "paper_summary",
  skills: [],
  sessions: {},
  uploaded: null
};

const els = {
  skillList: document.getElementById("skillList"),
  activePurpose: document.getElementById("activePurpose"),
  selectedSkill: document.getElementById("selectedSkill"),
  taskInput: document.getElementById("taskInput"),
  output: document.getElementById("output"),
  modeBadge: document.getElementById("modeBadge"),
  baseUrl: document.getElementById("baseUrl"),
  model: document.getElementById("model"),
  apiKey: document.getElementById("apiKey"),
  keyStatus: document.getElementById("keyStatus"),
  temperature: document.getElementById("temperature"),
  temperatureValue: document.getElementById("temperatureValue"),
  generate: document.getElementById("generate"),
  verifyRefs: document.getElementById("verifyRefs"),
  copyOutput: document.getElementById("copyOutput"),
  clearInput: document.getElementById("clearInput"),
  documentFile: document.getElementById("documentFile"),
  dropZone: document.getElementById("dropZone"),
  uploadReplace: document.getElementById("uploadReplace"),
  uploadAppend: document.getElementById("uploadAppend"),
  uploadStatus: document.getElementById("uploadStatus")
};

function currentAgent() {
  return agents[state.agentId] || agents.paper_summary;
}

function currentSession() {
  if (!state.sessions[state.agentId]) {
    state.sessions[state.agentId] = [];
  }
  return state.sessions[state.agentId];
}

function drawSignal() {
  const canvas = document.getElementById("signalCanvas");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#0f766e";
  ctx.lineWidth = 2;
  for (let row = 0; row < 3; row += 1) {
    ctx.beginPath();
    for (let x = 0; x < canvas.width; x += 1) {
      const y = 10 + row * 12 + Math.sin((x + row * 12) / 8) * 5;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  ctx.fillStyle = "#8a5a18";
  for (let x = 8; x < canvas.width; x += 14) {
    ctx.fillRect(x, 8, 3, 28);
  }
}

function setBadge(text, type = "") {
  els.modeBadge.textContent = text;
  els.modeBadge.className = type;
}

function setUploadStatus(text, type = "") {
  els.uploadStatus.textContent = text;
  els.uploadStatus.className = `hint ${type}`.trim();
}

function renderConversation() {
  const session = currentSession();
  if (!session.length) {
    els.output.textContent = `# ${currentAgent().title}\n\n${currentAgent().purpose}\n\n在左侧选择不同 Agent 会保留各自的对话上下文。`;
    return;
  }
  els.output.textContent = session
    .map((item) => `${item.role === "user" ? "## User" : "## Agent"}\n\n${item.content}`)
    .join("\n\n---\n\n");
}

function selectAgent(agentId, useTemplate = true) {
  const agent = agents[agentId] || agents.paper_summary;
  state.agentId = agent.id;
  state.skill = agent.skill;
  els.selectedSkill.textContent = agent.title;
  els.activePurpose.textContent = agent.purpose;
  els.generate.textContent = agent.deterministic === "verifyRefs" ? "Generate Report" : "Generate";
  document.querySelectorAll(".agent-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.agent === agent.id);
  });
  if (useTemplate && !els.taskInput.value.trim()) {
    els.taskInput.value = agent.template;
  }
  renderConversation();
}

function selectSkill(skillId) {
  const agent = Object.values(agents).find((item) => item.skill === skillId) || agents.paper_summary;
  selectAgent(agent.id);
}

function renderSkills() {
  els.skillList.innerHTML = "";
  for (const group of agentGroups) {
    const details = document.createElement("details");
    details.className = "agent-group";
    details.open = group.id === "agent" || group.id === "reading" || group.agents.some((agent) => agent.id === state.agentId);
    const summary = document.createElement("summary");
    summary.textContent = group.title;
    details.appendChild(summary);
    const list = document.createElement("div");
    list.className = "agent-list";
    for (const agent of group.agents) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "agent-item";
      button.dataset.agent = agent.id;
      button.innerHTML = `<strong>${agent.title}</strong><span>${agent.purpose}</span>`;
      button.addEventListener("click", () => selectAgent(agent.id));
      list.appendChild(button);
    }
    details.appendChild(list);
    els.skillList.appendChild(details);
  }
  selectAgent(state.agentId, false);
}

async function loadConfig() {
  const config = await fetch("/api/config").then((response) => response.json());
  els.baseUrl.value = config.baseUrl;
  els.model.value = config.model;
  els.keyStatus.textContent = config.hasEnvApiKey
    ? "已检测到环境变量 DASHSCOPE_API_KEY。"
    : "未检测到环境变量。可在这里临时填写 API Key。";
}

async function loadSkills() {
  state.skills = await fetch("/api/skills").then((response) => response.json());
  renderSkills();
}

function uploadTemplateFor(upload) {
  if (upload.kind === "bibliography" || upload.extension === ".bib") return agents.reference_verification.template;
  return agents.paper_summary.template;
}

function uploadAgentFor(upload) {
  if (upload.kind === "bibliography" || upload.extension === ".bib") return "reference_verification";
  return "paper_summary";
}

function formatUploadBlock(upload) {
  const truncated = upload.truncated ? "\n\n[提示：文档过长，已截断到前 120000 个字符。]" : "";
  return `\n\n---\n上传文件：${upload.filename}\n字符数：${upload.chars}\n\n${upload.text}${truncated}\n---\n`;
}

function insertUploadedText(mode) {
  if (!state.uploaded) {
    setUploadStatus("请先选择并解析一个文档。", "error");
    return;
  }
  const block = formatUploadBlock(state.uploaded);
  if (mode === "replace") {
    selectAgent(uploadAgentFor(state.uploaded), false);
    els.taskInput.value = `${uploadTemplateFor(state.uploaded)}${block}`;
  } else {
    els.taskInput.value = `${els.taskInput.value.trim()}${block}`;
  }
  els.taskInput.focus();
  setUploadStatus(`已${mode === "replace" ? "替换" : "追加"}：${state.uploaded.filename}`);
}

async function uploadFile(file) {
  if (!file) return;
  setUploadStatus(`解析中：${file.name}`);
  els.dropZone.classList.add("busy");
  const form = new FormData();
  form.append("document", file);
  try {
    const response = await fetch("/api/upload", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "上传解析失败");
    }
    state.uploaded = data;
    const truncated = data.truncated ? "，已截断" : "";
    const kindLabel = data.kind === "bibliography" ? "参考文献库" : data.kind === "paper" ? "论文" : "文档";
    setUploadStatus(`已解析${kindLabel}：${data.filename}，${data.chars} 字符${truncated}`);
    insertUploadedText("replace");
  } catch (error) {
    state.uploaded = null;
    setUploadStatus(String(error), "error");
  } finally {
    els.dropZone.classList.remove("busy");
  }
}

async function verifyReferences(inputOverride = null) {
  const input = (inputOverride || els.taskInput.value).trim();
  if (!input) {
    els.taskInput.focus();
    return;
  }
  setBadge("verifying");
  els.output.textContent = "正在验证参考文献...";
  try {
    const response = await fetch("/api/verify-references", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input })
    });
    const data = await response.json();
    const content = data.content || data.error || "No verification output.";
    currentSession().push({ role: "user", content: input });
    currentSession().push({ role: "assistant", content });
    renderConversation();
    setBadge(response.ok ? "verified" : "error", response.ok ? "" : "error");
  } catch (error) {
    els.output.textContent = String(error);
    setBadge("error", "error");
  }
}

async function generate() {
  const input = els.taskInput.value.trim();
  if (!input) {
    els.taskInput.focus();
    return;
  }
  const agent = currentAgent();
  if (agent.deterministic === "verifyRefs") {
    await verifyReferences(input);
    return;
  }
  els.generate.disabled = true;
  setBadge("running");
  els.output.textContent = "生成中...";
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        skill: state.skill,
        input,
        history: currentSession(),
        apiKey: els.apiKey.value.trim(),
        baseUrl: els.baseUrl.value.trim(),
        model: els.model.value.trim(),
        temperature: els.temperature.value
      })
    });
    const data = await response.json();
    const content = data.content || data.error || "No output.";
    currentSession().push({ role: "user", content: input });
    currentSession().push({ role: "assistant", content });
    renderConversation();
    setBadge(data.mode || "done", data.ok ? "" : "error");
  } catch (error) {
    els.output.textContent = String(error);
    setBadge("error", "error");
  } finally {
    els.generate.disabled = false;
  }
}

function bindEvents() {
  document.querySelectorAll("[data-template]").forEach((button) => {
    button.addEventListener("click", () => {
      const agent = templates[button.dataset.template];
      selectAgent(agent.id, false);
      els.taskInput.value = agent.template;
      els.taskInput.focus();
    });
  });
  els.generate.addEventListener("click", generate);
  els.verifyRefs.addEventListener("click", () => {
    selectAgent("reference_verification", false);
    verifyReferences();
  });
  els.temperature.addEventListener("input", () => {
    els.temperatureValue.textContent = els.temperature.value;
  });
  els.copyOutput.addEventListener("click", async () => {
    await navigator.clipboard.writeText(els.output.textContent);
    setBadge("copied");
  });
  els.clearInput.addEventListener("click", () => {
    els.taskInput.value = currentAgent().template;
    state.sessions[state.agentId] = [];
    renderConversation();
    setBadge("ready");
  });
  els.documentFile.addEventListener("change", () => uploadFile(els.documentFile.files[0]));
  els.uploadReplace.addEventListener("click", () => insertUploadedText("replace"));
  els.uploadAppend.addEventListener("click", () => insertUploadedText("append"));
  ["dragenter", "dragover"].forEach((eventName) => {
    els.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      els.dropZone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    els.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      els.dropZone.classList.remove("dragover");
    });
  });
  els.dropZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (file) uploadFile(file);
  });
}

async function init() {
  drawSignal();
  bindEvents();
  els.taskInput.value = currentAgent().template;
  await Promise.all([loadConfig(), loadSkills()]);
}

init();
