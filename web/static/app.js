const $ = (sel) => document.querySelector(sel);

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderAnnotation(ann) {
  const rows = [];
  const kv = (k, v) => rows.push(`<div class="k">${escapeHtml(k)}</div><div class="v">${v == null || v === "" ? "—" : escapeHtml(String(v))}</div>`);
  if (ann.kind === "protein") {
    kv("Name", ann.name);
    kv("Accession", ann.accession);
    kv("Organism", ann.organism);
    kv("Length", ann.length);
    kv("Function", ann.function);
  } else if (ann.kind === "literature") {
    kv("Hits", ann.n_hits);
    kv("Query used", ann.query_used);
    kv("Top PMIDs", (ann.top_pmids || []).join(", "));
  } else if (ann.kind === "mutation") {
    kv("Differences", ann.n_differences);
    kv("Assessment", ann.overall_assessment);
    kv("Notable flags", (ann.notable_flags || []).join(" · "));
  }
  let html = `<div class="kv">${rows.join("")}</div>`;
  if (ann.homology_hint && ann.homology_hint.length) {
    const items = ann.homology_hint.map(h => `<code>${escapeHtml(h.accession || "?")}</code>${h.organism ? " <em>(" + escapeHtml(h.organism) + ")</em>" : ""}`).join("&nbsp;&nbsp;");
    html += `<div class="homology">homology hint: ${items}</div>`;
  }
  return html;
}

function renderMarkdown(md) {
  if (!md) return "";
  let h = md
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^# (.*)$/gm, "<h1>$1</h1>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
  return h;
}

$("#demo").addEventListener("change", (e) => {
  const opt = e.target.selectedOptions[0];
  if (opt && opt.value) {
    $("#q").value = opt.value;
    const m = opt.dataset.mode;
    if (m) $("#mode").value = m;
  }
  e.target.value = "";
});

$("#run").addEventListener("click", async () => {
  const q = $("#q").value.trim();
  if (!q) return;
  const mode = $("#mode").value || "auto";
  $("#run").disabled = true;
  $("#status").textContent = "thinking…";
  $("#results").hidden = true;
  try {
    const r = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: q, mode }),
    });
    if (!r.ok) {
      const txt = await r.text();
      throw new Error(`HTTP ${r.status}: ${txt}`);
    }
    const data = await r.json();
    $("#meta").textContent = `· skill: ${data.skill} · session: ${data.session_id}`;

    // confidence bar
    if (typeof data.confidence === "number") {
      $("#confidence-row").hidden = false;
      const pct = Math.max(0, Math.min(1, data.confidence)) * 100;
      $("#conf-fill").style.width = pct + "%";
      $("#conf-value").textContent = data.confidence.toFixed(2);
    } else {
      $("#confidence-row").hidden = true;
    }

    // notes (fallback messages, etc.)
    const notes = data.notes || [];
    if (notes.length) {
      $("#notes").hidden = false;
      $("#notes").innerHTML = "<ul>" + notes.map(n => `<li>${escapeHtml(n)}</li>`).join("") + "</ul>";
    } else {
      $("#notes").hidden = true;
    }

    // annotation card
    const ann = data.annotation || {};
    const annCard = $("#annotation-card");
    if (ann && ann.kind && ann.kind !== "unknown") {
      annCard.hidden = false;
      $("#annotation").innerHTML = renderAnnotation(ann);
    } else {
      annCard.hidden = true;
    }

    $("#summary").innerHTML = renderMarkdown(data.summary || "(no summary)");
    $("#evidence").textContent = JSON.stringify(data.evidence, null, 2);
    const ol = $("#trace");
    ol.innerHTML = "";
    const steps = data.trace_steps || [];
    if (steps.length) {
      for (const s of steps) {
        const li = document.createElement("li");
        const k = document.createElement("span");
        k.className = "kind";
        k.textContent = s.skill;
        li.appendChild(k);
        const inp = JSON.stringify(s.input).slice(0, 120);
        const out = JSON.stringify(s.output).slice(0, 200);
        const span = document.createElement("span");
        span.textContent = ` ← ${inp} → ${out}`;
        li.appendChild(span);
        ol.appendChild(li);
      }
    } else {
      for (const ev of (data.trace || [])) {
        const li = document.createElement("li");
        const k = document.createElement("span");
        k.className = "kind";
        k.textContent = ev.kind;
        li.appendChild(k);
        const copy = { ...ev }; delete copy.kind; delete copy.ts;
        const span = document.createElement("span");
        span.textContent = " " + JSON.stringify(copy).slice(0, 240);
        li.appendChild(span);
        ol.appendChild(li);
      }
    }
    $("#results").hidden = false;
    $("#status").textContent = "done.";
  } catch (e) {
    $("#status").textContent = "error: " + e.message;
  } finally {
    $("#run").disabled = false;
  }
});
