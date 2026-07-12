const agentGroups = [
  {
    id: "planning",
    title: "Planning",
    agents: [
      {
        id: "agent_planner",
        title: "Task Planner Agent",
        skill: "agent-planner",
        purpose: "Decompose a biomedical research goal into a reviewable execution plan.",
        template: "Please decompose the following biomedical research goal into an approval-ready Agent execution plan. Include steps, inputs, tools, outputs, permission levels, risk controls, required evidence, user approvals, and final deliverables.\n\nResearch goal:"
      },
      {
        id: "memory_manager",
        title: "Memory Agent",
        skill: "memory-manager",
        purpose: "Maintain project facts, evidence, decisions, preferences, constraints, and open questions.",
        template: "Please turn the following information into a structured Open-Rosalind Agent memory update. Separate user-provided facts, evidence, inference, decisions, constraints, and open questions.\n\nInformation:"
      }
    ]
  },
  {
    id: "evidence",
    title: "Evidence",
    agents: [
      {
        id: "evidence_manager",
        title: "Evidence Agent",
        skill: "evidence-manager",
        purpose: "Extract traceable evidence records from papers, notes, RAG snippets, or tool outputs.",
        template: "Please convert the following material into traceable evidence records. Each record should include source locator, claim or observation, support level, verification status, risks, and manual-review needs. Do not invent DOI, PMID, accession IDs, sample sizes, p-values, or conclusions.\n\nMaterial:"
      },
      {
        id: "reference_verification",
        title: "Reference Verifier",
        skill: "reference-verification",
        purpose: "Check DOI, PMID, title, journal, author, and year consistency to reduce fabricated-reference risk.",
        template: "Please verify whether the following references exist and whether DOI, PMID, title, author, journal, and year metadata are consistent. Put one reference per line.\n\nReferences:\n",
        deterministic: "verifyRefs"
      }
    ]
  },
  {
    id: "execution",
    title: "Execution",
    agents: [
      {
        id: "python_analysis",
        title: "Python Analysis",
        skill: "python-sandbox",
        purpose: "Plan a short biomedical analysis and prepare reviewable Python code for the Docker sandbox.",
        template: "Please design a short, reproducible Python analysis for the following biomedical research task. First state assumptions, required inputs, expected outputs, and validation checks. Then provide one complete ```python code block that can run offline using the Python standard library. Do not claim that it has run.\n\nTask:"
      },
      {
        id: "tool_audit",
        title: "Tool Audit Agent",
        skill: "tool-audit",
        purpose: "Review tool calls for permissions, inputs, outputs, reproducibility, and unsupported conclusions.",
        template: "Please audit the following planned or completed tool calls. Check permission level, input sources, outputs, failure risks, reproducibility, required human confirmation, and conclusions that are not directly supported by the tool output.\n\nTool-call record or plan:"
      },
      {
        id: "agent_report_builder",
        title: "Traceable Report Agent",
        skill: "agent-report-builder",
        purpose: "Compile plans, evidence, tool logs, findings, and uncertainty into a traceable report.",
        template: "Please generate a traceable research report from the following task plan, evidence records, tool logs, and conclusions. Link every major conclusion to evidence or mark it unverified. Include skipped steps, uncertainty, and a reproducibility checklist.\n\nMaterials:"
      }
    ]
  }
];

const agents = Object.fromEntries(agentGroups.flatMap((group) => group.agents.map((agent) => [agent.id, agent])));

const state = {
  agentId: "agent_planner",
  skill: "agent-planner",
  sessions: {},
  uploaded: null,
  authMode: "login",
  projectId: "",
  activePlanId: ""
};

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
  currentUser: document.getElementById("currentUser"),
  logout: document.getElementById("logout"),
  projectStatus: document.getElementById("projectStatus"),
  projectSelect: document.getElementById("projectSelect"),
  projectName: document.getElementById("projectName"),
  createProject: document.getElementById("createProject"),
  projectWorkspace: document.getElementById("projectWorkspace"),
  memoryCategory: document.getElementById("memoryCategory"),
  memoryContent: document.getElementById("memoryContent"),
  addMemory: document.getElementById("addMemory"),
  memoryList: document.getElementById("memoryList"),
  taskGoal: document.getElementById("taskGoal"),
  generatePlan: document.getElementById("generatePlan"),
  taskStatus: document.getElementById("taskStatus"),
  taskPlan: document.getElementById("taskPlan"),
  skillList: document.getElementById("skillList"),
  activePurpose: document.getElementById("activePurpose"),
  selectedSkill: document.getElementById("selectedSkill"),
  inputMode: document.getElementById("inputMode"),
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
  uploadStatus: document.getElementById("uploadStatus"),
  sandboxStatus: document.getElementById("sandboxStatus"),
  sandboxProfile: document.getElementById("sandboxProfile"),
  pythonCode: document.getElementById("pythonCode"),
  preparePython: document.getElementById("preparePython"),
  confirmExecution: document.getElementById("confirmExecution"),
  runPython: document.getElementById("runPython"),
  executionOutput: document.getElementById("executionOutput"),
  executionFiles: document.getElementById("executionFiles")
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
  els.currentUser.textContent = user.email;
  drawSignal();
  renderSkills();
  els.taskInput.value = currentAgent().template;
  await Promise.all([loadConfig(), loadExecutionConfig(), loadProjects()]);
}

async function checkAuth() {
  const response = await fetch("/api/auth/me");
  if (!response.ok) {
    showAuth();
    return;
  }
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
  state.sessions = {};
  state.uploaded = null;
  state.projectId = "";
  state.activePlanId = "";
  showAuth();
}

function requireAuthenticatedResponse(response) {
  if (response.status === 401) {
    showAuth("会话已过期，请重新登录。");
    throw new Error("会话已过期，请重新登录。");
  }
  return response;
}

async function projectRequest(url, options = {}) {
  const response = await fetch(url, options);
  requireAuthenticatedResponse(response);
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || "项目操作失败。");
  return data;
}

function setTaskBusy(busy, message = "") {
  els.generatePlan.disabled = busy;
  els.taskPlan.querySelectorAll("button").forEach((button) => {
    button.disabled = busy;
  });
  if (message) els.taskStatus.textContent = message;
}

async function loadProjects(preferredId = "") {
  try {
    const data = await projectRequest("/api/projects");
    els.projectSelect.innerHTML = "";
    if (!data.projects.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "暂无项目";
      els.projectSelect.appendChild(option);
      state.projectId = "";
      state.activePlanId = "";
      els.projectStatus.textContent = "请新建";
      els.projectWorkspace.hidden = true;
      return;
    }
    for (const project of data.projects) {
      const option = document.createElement("option");
      option.value = project.id;
      option.textContent = project.name;
      els.projectSelect.appendChild(option);
    }
    const candidate = preferredId || state.projectId;
    state.projectId = data.projects.some((project) => project.id === candidate) ? candidate : data.projects[0].id;
    els.projectSelect.value = state.projectId;
    await loadProjectWorkspace();
  } catch (error) {
    els.projectStatus.textContent = "错误";
    els.taskStatus.textContent = String(error.message || error);
  }
}

async function createProject() {
  const name = els.projectName.value.trim();
  if (!name) return;
  els.createProject.disabled = true;
  try {
    const data = await projectRequest("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    });
    els.projectName.value = "";
    await loadProjects(data.project.id);
  } catch (error) {
    els.taskStatus.textContent = String(error.message || error);
  } finally {
    els.createProject.disabled = false;
  }
}

function renderMemory(memory) {
  els.memoryList.innerHTML = "";
  if (!memory.length) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = "暂无项目记忆。";
    els.memoryList.appendChild(empty);
    return;
  }
  for (const item of memory) {
    const article = document.createElement("article");
    article.className = "memory-item";
    const category = document.createElement("strong");
    category.textContent = item.category;
    const content = document.createElement("span");
    content.textContent = item.content;
    article.append(category, content);
    els.memoryList.appendChild(article);
  }
}

function pythonBlockFrom(text) {
  const blocks = [...String(text || "").matchAll(/```(?:python|py)\s*\n([\s\S]*?)```/gi)];
  return blocks.length ? blocks[blocks.length - 1][1].trim() : "";
}

function preparePythonText(text) {
  const code = pythonBlockFrom(text);
  if (!code) {
    els.executionOutput.textContent = "No Python code block was found in this step output.";
    return;
  }
  els.pythonCode.value = code;
  els.confirmExecution.checked = false;
  els.runPython.disabled = true;
  els.executionOutput.textContent = "Task-step Python code prepared. Review every line, then approve execution.";
  els.pythonCode.focus();
}

function renderTaskPlan(plan) {
  els.taskPlan.innerHTML = "";
  if (!plan) {
    els.taskStatus.textContent = "暂无任务计划。";
    return;
  }
  state.activePlanId = plan.id;
  els.taskStatus.textContent = `计划状态：${plan.status}`;
  const header = document.createElement("div");
  header.className = "plan-header";
  const title = document.createElement("strong");
  title.textContent = plan.goal;
  const actions = document.createElement("div");
  actions.className = "plan-actions";
  if (plan.status === "draft") {
    const confirm = document.createElement("button");
    confirm.type = "button";
    confirm.textContent = "确认计划";
    confirm.addEventListener("click", () => runPlanAction("confirm"));
    actions.appendChild(confirm);
  }
  if (["approved", "running"].includes(plan.status)) {
    const next = document.createElement("button");
    next.type = "button";
    next.textContent = "运行下一步";
    next.addEventListener("click", () => runPlanAction("run-next"));
    const all = document.createElement("button");
    all.type = "button";
    all.textContent = "连续运行";
    all.addEventListener("click", () => runPlanAction("run-all"));
    actions.append(next, all);
  }
  header.append(title, actions);
  els.taskPlan.appendChild(header);

  for (const step of plan.steps) {
    const article = document.createElement("article");
    article.className = `task-step status-${step.status}`;
    const stepTitle = document.createElement("strong");
    stepTitle.textContent = `${step.position}. ${step.title} · ${step.status}`;
    const instruction = document.createElement("p");
    instruction.textContent = step.instruction;
    article.append(stepTitle, instruction);
    if (step.output || step.error) {
      const output = document.createElement("pre");
      output.className = "step-output";
      output.textContent = step.output || step.error;
      article.appendChild(output);
    }
    const stepActions = document.createElement("div");
    stepActions.className = "step-actions";
    if (step.status === "failed") {
      const retry = document.createElement("button");
      retry.type = "button";
      retry.textContent = "重试此步骤";
      retry.addEventListener("click", () => retryStep(step.id));
      stepActions.appendChild(retry);
    }
    if (step.status === "completed" && step.output) {
      const remember = document.createElement("button");
      remember.type = "button";
      remember.textContent = "保存到记忆";
      remember.addEventListener("click", () => saveStepMemory(step.id));
      stepActions.appendChild(remember);
      if (pythonBlockFrom(step.output)) {
        const prepare = document.createElement("button");
        prepare.type = "button";
        prepare.textContent = "送入 Python 沙箱";
        prepare.addEventListener("click", () => preparePythonText(step.output));
        stepActions.appendChild(prepare);
      }
    }
    article.appendChild(stepActions);
    els.taskPlan.appendChild(article);
  }
}

async function loadProjectWorkspace() {
  if (!state.projectId) return;
  try {
    const data = await projectRequest(`/api/projects/${state.projectId}/workspace`);
    els.projectWorkspace.hidden = false;
    els.projectStatus.textContent = data.project.name;
    renderMemory(data.memory);
    const active = data.plans.find((plan) => plan.id === state.activePlanId) || data.plans[0] || null;
    renderTaskPlan(active);
  } catch (error) {
    els.taskStatus.textContent = String(error.message || error);
  }
}

async function addMemory() {
  const content = els.memoryContent.value.trim();
  if (!state.projectId || !content) return;
  try {
    await projectRequest(`/api/projects/${state.projectId}/memory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: els.memoryCategory.value, content })
    });
    els.memoryContent.value = "";
    await loadProjectWorkspace();
  } catch (error) {
    els.taskStatus.textContent = String(error.message || error);
  }
}

async function generatePlan() {
  const goal = els.taskGoal.value.trim();
  if (!state.projectId || !goal) return;
  setTaskBusy(true, "Qwen 正在生成可审查任务计划...");
  try {
    const data = await projectRequest(`/api/projects/${state.projectId}/plans/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal })
    });
    state.activePlanId = data.plan.id;
    renderTaskPlan(data.plan);
  } catch (error) {
    els.taskStatus.textContent = String(error.message || error);
  } finally {
    setTaskBusy(false);
  }
}

async function runPlanAction(action) {
  if (!state.activePlanId) return;
  const label = action === "confirm" ? "正在确认计划..." : action === "run-all" ? "正在连续执行任务步骤..." : "正在执行下一步...";
  setTaskBusy(true, label);
  try {
    const data = await projectRequest(`/api/plans/${state.activePlanId}/${action}`, { method: "POST" });
    renderTaskPlan(data.plan);
    if (data.task) {
      await pollBackgroundTask(data.task.jobId);
    }
  } catch (error) {
    els.taskStatus.textContent = String(error.message || error);
  } finally {
    setTaskBusy(false);
  }
}

async function pollBackgroundTask(jobId) {
  const terminal = new Set(["finished", "failed", "stopped", "canceled"]);
  for (let attempt = 0; attempt < 600; attempt += 1) {
    const data = await projectRequest(`/api/tasks/${jobId}/status`);
    const task = data.task;
    if (task.plan) renderTaskPlan(task.plan);
    els.taskStatus.textContent = `后台任务：${task.status}`;
    if (terminal.has(task.status)) {
      if (task.status === "failed" && task.error) {
        els.taskStatus.textContent = `后台任务失败：${task.error.split("\n").slice(-2).join(" ")}`;
      }
      await loadProjectWorkspace();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  els.taskStatus.textContent = "后台任务仍在运行，可稍后刷新项目查看。";
}

async function retryStep(stepId) {
  setTaskBusy(true, "正在重置失败步骤...");
  try {
    const data = await projectRequest(`/api/steps/${stepId}/retry`, { method: "POST" });
    renderTaskPlan(data.plan);
  } catch (error) {
    els.taskStatus.textContent = String(error.message || error);
  } finally {
    setTaskBusy(false);
  }
}

async function saveStepMemory(stepId) {
  try {
    await projectRequest(`/api/steps/${stepId}/memory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: "conclusion" })
    });
    await loadProjectWorkspace();
  } catch (error) {
    els.taskStatus.textContent = String(error.message || error);
  }
}

function currentAgent() {
  return agents[state.agentId] || agents.agent_planner;
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
  ctx.strokeStyle = "#116149";
  ctx.lineWidth = 2;
  for (let row = 0; row < 3; row += 1) {
    ctx.beginPath();
    for (let x = 0; x < canvas.width; x += 1) {
      const y = 10 + row * 12 + Math.sin((x + row * 10) / 7) * 4;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  ctx.fillStyle = "#b45309";
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
    els.output.textContent = `# ${currentAgent().title}\n\n${currentAgent().purpose}\n\nThis module keeps its own context. Major conclusions should link to evidence, tool logs, or be marked unverified.`;
    return;
  }
  els.output.textContent = session
    .map((item) => `${item.role === "user" ? "## User" : "## Agent"}\n\n${item.content}`)
    .join("\n\n---\n\n");
}

function selectAgent(agentId, useTemplate = true) {
  const agent = agents[agentId] || agents.agent_planner;
  state.agentId = agent.id;
  state.skill = agent.skill;
  els.selectedSkill.textContent = agent.title;
  els.activePurpose.textContent = agent.purpose;
  els.inputMode.textContent = agent.deterministic === "verifyRefs" ? "verification" : "draft";
  els.generate.textContent = agent.deterministic === "verifyRefs" ? "Verify" : "Generate";
  document.querySelectorAll(".agent-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.agent === agent.id);
  });
  if (useTemplate) {
    els.taskInput.value = agent.template;
  }
  renderConversation();
}

function renderSkills() {
  els.skillList.innerHTML = "";
  for (const group of agentGroups) {
    const groupLabel = document.createElement("div");
    groupLabel.className = "group-label";
    groupLabel.textContent = group.title;
    els.skillList.appendChild(groupLabel);
    for (const agent of group.agents) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "agent-item";
      button.dataset.agent = agent.id;
      button.innerHTML = `<strong>${agent.title}</strong><span>${agent.purpose}</span>`;
      button.addEventListener("click", () => selectAgent(agent.id));
      els.skillList.appendChild(button);
    }
  }
  selectAgent(state.agentId, false);
}

async function loadConfig() {
  const config = await fetch("/api/config").then((response) => response.json());
  els.baseUrl.value = config.baseUrl;
  els.model.value = config.model;
  els.keyStatus.textContent = config.hasEnvApiKey
    ? "OPENAI_API_KEY detected in environment."
    : "No environment API key detected. You can paste a session-only OpenAI-compatible key here.";
}

async function loadExecutionConfig() {
  try {
    const config = await fetch("/api/execution/config").then((response) => response.json());
    els.sandboxStatus.textContent = config.enabled ? "ready" : "disabled";
    els.sandboxProfile.textContent = config.enabled
      ? `${config.image} · ${config.cpu} CPU · ${config.memory} · ${config.timeoutSeconds}s · network disabled`
      : "Code execution is disabled on this server.";
    els.confirmExecution.disabled = !config.enabled;
    els.runPython.disabled = !config.enabled || !els.confirmExecution.checked;
  } catch (error) {
    els.sandboxStatus.textContent = "error";
    els.sandboxProfile.textContent = String(error);
  }
}

function renderExecutionResult(data) {
  const lines = [
    `status: ${data.status || "error"}`,
    `job: ${data.jobId || "-"}`,
    `duration: ${data.audit?.durationSeconds ?? "-"}s`,
    `exit code: ${data.audit?.exitCode ?? "-"}`,
    "",
    "stdout:",
    data.stdout || "(empty)",
    "",
    "stderr:",
    data.stderr || data.error || "(empty)"
  ];
  els.executionOutput.textContent = lines.join("\n");
  els.executionFiles.innerHTML = "";
  for (const file of data.files || []) {
    const link = document.createElement("a");
    link.href = file.url;
    link.textContent = `${file.name} (${file.size} bytes)`;
    link.title = `SHA-256: ${file.sha256}`;
    els.executionFiles.appendChild(link);
  }
}

function prepareLatestPython() {
  const session = currentSession();
  const latest = [...session].reverse().find((item) => item.role === "assistant")?.content || els.output.textContent;
  const blocks = [...latest.matchAll(/```(?:python|py)\s*\n([\s\S]*?)```/gi)];
  if (!blocks.length) {
    els.executionOutput.textContent = "No Python code block was found in the latest Agent output.";
    return;
  }
  els.pythonCode.value = blocks[blocks.length - 1][1].trim();
  els.confirmExecution.checked = false;
  els.runPython.disabled = true;
  els.executionOutput.textContent = "Python code prepared. Review every line, then approve execution.";
  els.pythonCode.focus();
}

async function runPython() {
  const code = els.pythonCode.value.trim();
  if (!code || !els.confirmExecution.checked) return;
  els.runPython.disabled = true;
  els.sandboxStatus.textContent = "running";
  els.executionOutput.textContent = "Running in an isolated Docker container...";
  els.executionFiles.innerHTML = "";
  try {
    const response = await fetch("/api/execute/python", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, confirmed: true })
    });
    requireAuthenticatedResponse(response);
    const data = await response.json();
    renderExecutionResult(data);
    els.sandboxStatus.textContent = data.status || "error";
  } catch (error) {
    renderExecutionResult({ status: "error", error: String(error) });
    els.sandboxStatus.textContent = "error";
  } finally {
    els.confirmExecution.checked = false;
    els.runPython.disabled = true;
  }
}

function uploadAgentFor(upload) {
  if (upload.kind === "bibliography" || upload.extension === ".bib") return "reference_verification";
  return "evidence_manager";
}

function uploadTemplateFor(upload) {
  return agents[uploadAgentFor(upload)].template;
}

function formatUploadBlock(upload) {
  const truncated = upload.truncated ? "\n\n[Note: document was too long and was truncated to the first 120000 characters.]" : "";
  return `\n\n---\nUploaded file: ${upload.filename}\nKind: ${upload.kind}\nCharacters: ${upload.chars}\n\n${upload.text}${truncated}\n---\n`;
}

function insertUploadedText(mode) {
  if (!state.uploaded) {
    setUploadStatus("Choose and parse a file first.", "error");
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
  setUploadStatus(`${mode === "replace" ? "Replaced" : "Appended"}: ${state.uploaded.filename}`);
}

async function uploadFile(file) {
  if (!file) return;
  setUploadStatus(`Parsing: ${file.name}`);
  els.dropZone.classList.add("busy");
  const form = new FormData();
  form.append("document", file);
  try {
    const response = await fetch("/api/upload", { method: "POST", body: form });
    requireAuthenticatedResponse(response);
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Upload parsing failed");
    }
    state.uploaded = data;
    const truncated = data.truncated ? ", truncated" : "";
    const kindLabel = data.kind === "bibliography" ? "bibliography" : data.kind === "paper" ? "PDF paper" : "document";
    setUploadStatus(`Parsed ${kindLabel}: ${data.filename}, ${data.chars} chars${truncated}`);
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
  els.output.textContent = "Verifying references...";
  try {
    const response = await fetch("/api/verify-references", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input })
    });
    requireAuthenticatedResponse(response);
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
  els.output.textContent = "Generating...";
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
    requireAuthenticatedResponse(response);
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
  els.loginMode.addEventListener("click", () => setAuthMode("login"));
  els.registerMode.addEventListener("click", () => setAuthMode("register"));
  els.authForm.addEventListener("submit", submitAuth);
  els.logout.addEventListener("click", logout);
  els.createProject.addEventListener("click", createProject);
  els.projectName.addEventListener("keydown", (event) => {
    if (event.key === "Enter") createProject();
  });
  els.projectSelect.addEventListener("change", async () => {
    state.projectId = els.projectSelect.value;
    state.activePlanId = "";
    await loadProjectWorkspace();
  });
  els.addMemory.addEventListener("click", addMemory);
  els.generatePlan.addEventListener("click", generatePlan);
  document.querySelectorAll("[data-agent]").forEach((button) => {
    button.addEventListener("click", () => selectAgent(button.dataset.agent));
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
  els.confirmExecution.addEventListener("change", () => {
    els.runPython.disabled = !els.confirmExecution.checked || els.confirmExecution.disabled;
  });
  els.preparePython.addEventListener("click", prepareLatestPython);
  els.runPython.addEventListener("click", runPython);
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
  bindEvents();
  setAuthMode("login");
  await checkAuth();
}

init();
