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
  uploaded: null
};

const els = {
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
  uploadStatus: document.getElementById("uploadStatus")
};

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
  renderSkills();
  bindEvents();
  els.taskInput.value = currentAgent().template;
  await loadConfig();
}

init();