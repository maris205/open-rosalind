const functionGroups = [
  {
    id: "research",
    standalone: true,
    items: [
      {
        id: "research_assistant",
        title: "智能研究",
        icon: "✦",
        skill: "research_assistant",
        purpose: "在一个对话中完成规划、记忆、证据、工具审计和可追溯报告。",
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
        id: "reference_verification",
        title: "参考文献验证",
        icon: "✓",
        skill: "reference_verification",
        purpose: "检查文献是否存在及 DOI、PMID 和元数据一致性。",
        template: "请验证以下参考文献是否真实存在，并检查 DOI、PMID、题名、作者、期刊和年份是否一致。每条参考文献请单独成行。",
        deterministic: "verifyRefs"
      }
    ]
  }
];

const functions = Object.fromEntries(
  functionGroups.flatMap((group) => group.items.map((item) => [item.id, item]))
);

const state = {
  functionId: "research_assistant",
  sessions: {},
  uploaded: null
};

const els = {
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
  baseUrl: document.getElementById("baseUrl"),
  model: document.getElementById("model"),
  apiKey: document.getElementById("apiKey"),
  keyStatus: document.getElementById("keyStatus"),
  temperature: document.getElementById("temperature"),
  temperatureValue: document.getElementById("temperatureValue"),
  documentFile: document.getElementById("documentFile"),
  uploadStatus: document.getElementById("uploadStatus"),
  attachmentChip: document.getElementById("attachmentChip"),
  attachmentName: document.getElementById("attachmentName"),
  attachmentMeta: document.getElementById("attachmentMeta"),
  removeAttachment: document.getElementById("removeAttachment")
};

function currentFunction() {
  return functions[state.functionId] || functions.research_assistant;
}

function currentSession() {
  if (!state.sessions[state.functionId]) {
    state.sessions[state.functionId] = [];
  }
  return state.sessions[state.functionId];
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

function setUploadStatus(text, type = "") {
  els.uploadStatus.textContent = text;
  els.uploadStatus.className = `hint ${type}`.trim();
}

function renderFunctions() {
  els.skillList.innerHTML = "";
  for (const group of functionGroups) {
    const section = document.createElement("section");
    section.className = `function-group${group.standalone ? " standalone" : ""}`;

    if (group.standalone) {
      const item = group.items[0];
      const button = document.createElement("button");
      button.type = "button";
      button.className = "standalone-function";
      button.dataset.functionId = item.id;
      button.innerHTML = `<span class="group-icon">${item.icon}</span><span>${item.title}</span>`;
      button.addEventListener("click", () => selectFunction(item.id));
      section.appendChild(button);
      els.skillList.appendChild(section);
      continue;
    }

    const heading = document.createElement("h2");
    const groupIcon = document.createElement("span");
    groupIcon.className = "group-icon";
    groupIcon.textContent = group.icon;
    const groupTitle = document.createElement("span");
    groupTitle.textContent = group.title;
    heading.append(groupIcon, groupTitle);
    section.appendChild(heading);

    const list = document.createElement("div");
    list.className = "function-list";
    for (const item of group.items) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "function-item";
      button.dataset.functionId = item.id;
      const icon = document.createElement("span");
      icon.className = "function-icon";
      icon.textContent = item.icon;
      const title = document.createElement("span");
      title.className = "function-title";
      title.textContent = item.title;
      button.append(icon, title);
      button.addEventListener("click", () => selectFunction(item.id));
      list.appendChild(button);
    }
    section.appendChild(list);
    els.skillList.appendChild(section);
  }
}

function appendMessage(role, content) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "你" : currentFunction().title;

  const body = document.createElement("pre");
  body.textContent = content;

  article.append(label, body);
  els.conversation.appendChild(article);
}

function renderConversation() {
  els.conversation.innerHTML = "";
  const session = currentSession();
  if (!session.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const title = document.createElement("h3");
    title.textContent = currentFunction().title;
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
    appendMessage(item.role, item.content);
  }
  els.conversation.scrollTop = els.conversation.scrollHeight;
}

function selectFunction(functionId) {
  state.functionId = functions[functionId] ? functionId : "research_assistant";
  const item = currentFunction();
  els.selectedSkill.textContent = item.title;
  els.activePurpose.textContent = item.purpose;
  els.taskInput.placeholder = `与“${item.title}”对话，Enter 发送，Shift+Enter 换行`;
  document.querySelectorAll(".function-item, .standalone-function").forEach((button) => {
    button.classList.toggle("active", button.dataset.functionId === item.id);
  });
  setBadge("ready");
  renderConversation();
  els.taskInput.focus();
}

async function loadConfig() {
  const config = await fetch("/api/config").then((response) => response.json());
  els.baseUrl.value = config.baseUrl;
  els.model.value = config.model;
  els.keyStatus.textContent = config.hasEnvApiKey
    ? "已检测到环境变量 DASHSCOPE_API_KEY。"
    : "未检测到环境变量，可在此临时填写 API Key。";
}

function attachmentBlock() {
  if (!state.uploaded) return "";
  const truncated = state.uploaded.truncated ? "\n[文档过长，内容已截断]" : "";
  return `\n\n---\n附件：${state.uploaded.filename}\n\n${state.uploaded.text}${truncated}\n---`;
}

function clearAttachment() {
  state.uploaded = null;
  els.documentFile.value = "";
  els.attachmentChip.hidden = true;
  setUploadStatus("支持 PDF、BibTeX、DOCX 和文本，最大 12 MB");
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
    const response = await fetch("/api/upload", { method: "POST", body: form });
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
    const response = await fetch("/api/verify-references", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: state.uploaded ? state.uploaded.text : requestInput })
    });
    const data = await response.json();
    const content = data.content || data.error || "No verification output.";
    currentSession().push({ role: "user", content: displayInput, requestContent: requestInput });
    currentSession().push({ role: "assistant", content });
    setBadge(response.ok ? "verified" : "error", response.ok ? "" : "error");
  } catch (error) {
    currentSession().push({ role: "user", content: displayInput, requestContent: requestInput });
    currentSession().push({ role: "assistant", content: String(error) });
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
    const response = await fetch("/api/generate", {
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
    currentSession().push({ role: "user", content: displayInput, requestContent: requestInput });
    currentSession().push({ role: "assistant", content });
    setBadge(data.mode || "done", data.ok ? "" : "error");
  } catch (error) {
    currentSession().push({ role: "user", content: displayInput, requestContent: requestInput });
    currentSession().push({ role: "assistant", content: String(error) });
    setBadge("error", "error");
  } finally {
    els.sendButton.disabled = false;
  }
}

async function sendMessage() {
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

  els.taskInput.value = "";
  appendMessage("user", displayInput);
  const pending = document.createElement("article");
  pending.className = "message assistant pending";
  pending.textContent = "处理中...";
  els.conversation.appendChild(pending);
  els.conversation.scrollTop = els.conversation.scrollHeight;

  if (shouldVerifyReferences(item, input)) {
    await verifyReferences(input || state.uploaded.text, displayInput);
  } else {
    await generate(requestInput, displayInput);
  }

  clearAttachment();
  renderConversation();
  els.taskInput.focus();
}

function copyLatestAnswer() {
  const latest = [...currentSession()].reverse().find((item) => item.role === "assistant");
  if (!latest) return;
  navigator.clipboard.writeText(latest.content).then(() => setBadge("copied"));
}

function bindEvents() {
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
  els.clearChat.addEventListener("click", () => {
    state.sessions[state.functionId] = [];
    clearAttachment();
    renderConversation();
    setBadge("ready");
  });
  els.openSettings.addEventListener("click", () => els.settingsDialog.showModal());
  els.settingsDialog.addEventListener("click", (event) => {
    if (event.target === els.settingsDialog) els.settingsDialog.close();
  });
  els.temperature.addEventListener("input", () => {
    els.temperatureValue.textContent = els.temperature.value;
  });
}

async function init() {
  drawSignal();
  renderFunctions();
  bindEvents();
  selectFunction(state.functionId);
  await loadConfig();
}

init();
