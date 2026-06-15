// ---- API helpers ---------------------------------------------------------
const API = "";  // same origin
async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ---- Globals -------------------------------------------------------------
let network = null;
let nodesDS = null;
let edgesDS = null;
let baseColors = {};   // node id -> original color
const CATEGORY_LABELS = {
  company: "Company", technology: "Technology", policy: "Policy",
  target: "Target", sector: "Sector", organization: "Org",
  country: "Country", news: "Live News", concept: "Concept",
};

// ---- Toast ---------------------------------------------------------------
let toastTimer = null;
function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 3200);
}
function setLoading(on) {
  document.getElementById("graphLoading").classList.toggle("show", on);
}

// ---- Graph rendering -----------------------------------------------------
async function loadGraph() {
  setLoading(true);
  try {
    const data = await api("/api/graph");
    baseColors = {};
    const nodes = data.nodes.map((n) => {
      baseColors[n.id] = n.color;
      return {
        id: n.id, label: n.label, group: n.group,
        value: n.value,
        color: { background: n.color, border: shade(n.color, -25),
                 highlight: { background: lighten(n.color), border: "#fff" } },
        font: { color: "#e6ecf7", size: 14, face: "Inter" },
      };
    });
    const edges = data.edges.map((e, i) => ({
      id: "e" + i, from: e.from, to: e.to, label: e.label,
      arrows: "to",
      color: { color: "rgba(120,140,180,0.35)" },
      font: { color: "#7e8db0", size: 9, strokeWidth: 0, align: "middle" },
      smooth: { type: "continuous" },
    }));

    nodesDS = new vis.DataSet(nodes);
    edgesDS = new vis.DataSet(edges);

    const container = document.getElementById("network");
    const options = {
      nodes: { shape: "dot", scaling: { min: 10, max: 45 }, borderWidth: 2 },
      edges: { color: { color: "rgba(120,140,180,0.35)" }, width: 1,
               selectionWidth: 2, hoverWidth: 2 },
      physics: {
        barnesHut: { gravitationalConstant: -9000, springLength: 130,
                     springConstant: 0.04, damping: 0.45, avoidOverlap: 0.2 },
        stabilization: { iterations: 220 },
      },
      interaction: {
        hover: true, tooltipDelay: 120, navigationButtons: false, keyboard: false,
        zoomView: true,
        zoomSpeed: 0.35,   // gentle, smooth zoom on scroll (default 1 is jumpy)
      },
    };
    network = new vis.Network(container, { nodes: nodesDS, edges: edgesDS }, options);

    // Freeze the layout once it settles so scrolling/zooming doesn't make the
    // nodes drift or jitter.
    network.once("stabilizationIterationsDone", () => {
      setLoading(false);
      network.setOptions({ physics: false });
    });
    setTimeout(() => { setLoading(false); network.setOptions({ physics: false }); }, 4000);

    // Keep the zoom within sensible bounds so a fast scroll can't shoot the
    // graph off into deep zoom-in/out.
    const MIN_ZOOM = 0.25, MAX_ZOOM = 2.8;
    let zoomGuard = false;
    network.on("zoom", () => {
      if (zoomGuard) return;
      const s = network.getScale();
      const clamped = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, s));
      if (clamped !== s) {
        zoomGuard = true;
        network.moveTo({ scale: clamped });
        zoomGuard = false;
      }
    });

    network.on("click", (params) => {
      if (params.nodes.length) focusNode(params.nodes[0]);
    });

    buildLegend(data.nodes);
  } catch (e) {
    toast("Failed to load graph: " + e.message);
    setLoading(false);
  }
}

function buildLegend(nodes) {
  const cats = [...new Set(nodes.map((n) => n.group))];
  const legend = document.getElementById("legend");
  legend.innerHTML = cats.map((c) => {
    const color = nodes.find((n) => n.group === c).color;
    return `<div class="item"><span class="swatch" style="background:${color}"></span>${CATEGORY_LABELS[c] || c}</div>`;
  }).join("");
}

// ---- Highlighting --------------------------------------------------------
function resetHighlight() {
  if (!nodesDS) return;
  const updates = nodesDS.getIds().map((id) => ({
    id, color: { background: baseColors[id], border: shade(baseColors[id], -25) },
    opacity: 1,
  }));
  nodesDS.update(updates);
  edgesDS.update(edgesDS.getIds().map((id) => ({ id, color: { color: "rgba(120,140,180,0.35)" }, width: 1 })));
}

function highlightPath(entities, paths) {
  if (!nodesDS) return;
  resetHighlight();
  const pathNodes = new Set(entities);
  paths.forEach((p) => p.nodes.forEach((n) => pathNodes.add(n)));

  // Dim everything, then light up path nodes.
  nodesDS.update(nodesDS.getIds().map((id) => ({
    id, opacity: pathNodes.has(id) ? 1 : 0.18,
    color: pathNodes.has(id)
      ? { background: lighten(baseColors[id]), border: "#ffffff" }
      : { background: baseColors[id], border: shade(baseColors[id], -25) },
  })));

  // Light up edges that lie on a path.
  const edgePairs = new Set();
  paths.forEach((p) => {
    for (let i = 0; i < p.nodes.length - 1; i++) {
      edgePairs.add(p.nodes[i] + "|" + p.nodes[i + 1]);
      edgePairs.add(p.nodes[i + 1] + "|" + p.nodes[i]);
    }
  });
  edgesDS.update(edgesDS.get().map((e) => {
    const on = edgePairs.has(e.from + "|" + e.to);
    return { id: e.id, color: { color: on ? "#2bd9a8" : "rgba(120,140,180,0.12)" },
             width: on ? 3 : 1 };
  }));

  if (pathNodes.size) network.fit({ nodes: [...pathNodes], animation: { duration: 600 } });
}

function focusNode(id) {
  network.focus(id, { scale: 1.2, animation: { duration: 500 } });
  network.selectNodes([id]);
}

// ---- Color utils ---------------------------------------------------------
function hexToRgb(hex) {
  const m = hex.replace("#", "");
  return [parseInt(m.slice(0, 2), 16), parseInt(m.slice(2, 4), 16), parseInt(m.slice(4, 6), 16)];
}
function shade(hex, amt) {
  const [r, g, b] = hexToRgb(hex);
  const c = (x) => Math.max(0, Math.min(255, x + amt));
  return `rgb(${c(r)},${c(g)},${c(b)})`;
}
function lighten(hex) { return shade(hex, 40); }

// ---- Chat ----------------------------------------------------------------
function addMessage(html, who) {
  const chat = document.getElementById("chat");
  const div = document.createElement("div");
  div.className = "msg " + who;
  div.innerHTML = html;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

async function askQuestion(q) {
  if (!q.trim()) return;
  addMessage(escapeHtml(q), "user");
  const thinking = addMessage("<i>Walking the graph…</i>", "bot");
  const sendBtn = document.getElementById("sendBtn");
  sendBtn.disabled = true;
  try {
    const r = await api("/api/ask", { method: "POST", body: JSON.stringify({ question: q }) });
    let html = `<p>${escapeHtml(r.answer)}</p>`;
    if (r.entities && r.entities.length) {
      html += `<div class="chips">` + r.entities.slice(0, 6).map((e) => `<span class="chip">${escapeHtml(e)}</span>`).join("") + `</div>`;
    }
    if (r.paths && r.paths.length) {
      const steps = r.paths[0].steps.map(prettyStep).join("  →  ");
      html += `<div class="path">${escapeHtml(steps)}</div>`;
    }
    html += `<span class="tag">${r.mode === "llm" ? "LLM" : "graph-walk"}${r.cached ? " · cached" : ""}</span>`;
    thinking.innerHTML = html;
    highlightPath(r.entities || [], r.paths || []);
  } catch (e) {
    thinking.innerHTML = `<p>⚠️ ${escapeHtml(e.message)}</p>`;
  } finally {
    sendBtn.disabled = false;
  }
}

function prettyStep(s) { return s.replace(/ --/g, " ").replace(/--> /g, " → "); }
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---- Stats / insights ----------------------------------------------------
async function loadStats() {
  try {
    const s = await api("/api/stats");
    document.getElementById("statNodes").textContent = s.nodes;
    document.getElementById("statEdges").textContent = s.edges;
    document.getElementById("statMode").textContent = (s.extractor_mode || "offline").toUpperCase();

    // Category bars
    const total = Object.values(s.by_category).reduce((a, b) => a + b, 0) || 1;
    const palette = { company: "#4C72B0", technology: "#55A868", policy: "#C44E52",
      target: "#8172B3", sector: "#CCB974", organization: "#64B5CD",
      country: "#937860", news: "#E8A33D", concept: "#999999" };
    const bars = Object.entries(s.by_category).sort((a, b) => b[1] - a[1]).map(([k, v]) => `
      <div class="bar-row">
        <span class="name">${CATEGORY_LABELS[k] || k}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${(v / total * 100).toFixed(0)}%;background:${palette[k] || "#999"}"></span></span>
        <span class="num">${v}</span>
      </div>`).join("");
    document.getElementById("categoryBars").innerHTML = bars;

    document.getElementById("hubs").innerHTML = s.top_hubs.map(([name, deg]) =>
      `<li data-node="${escapeHtml(name)}"><span>${escapeHtml(name)}</span><b>${deg}</b></li>`).join("");
    document.querySelectorAll("#hubs li").forEach((li) =>
      li.addEventListener("click", () => { switchTab("insights"); focusNode(li.dataset.node); }));

    const updated = s.last_updated ? new Date(s.last_updated * 1000).toLocaleString() : "—";
    document.getElementById("metaInfo").innerHTML =
      `Graph version: <b>${s.version}</b><br>Last updated: ${updated}<br>Engine: ${(s.extractor_mode||"offline").toUpperCase()}`;
  } catch (e) { /* silent */ }
}

async function loadSuggestions() {
  try {
    const r = await api("/api/suggestions");
    document.getElementById("suggestions").innerHTML =
      r.suggestions.map((s) => `<button>${escapeHtml(s)}</button>`).join("");
    document.querySelectorAll("#suggestions button").forEach((b) =>
      b.addEventListener("click", () => { document.getElementById("question").value = b.textContent; askQuestion(b.textContent); }));
  } catch (e) { /* silent */ }
}

async function checkHealth() {
  const el = document.getElementById("health");
  try { await api("/api/health"); el.classList.add("ok"); }
  catch { el.classList.remove("ok"); }
}

// ---- Actions -------------------------------------------------------------
async function rebuild() {
  setLoading(true);
  try {
    await api("/api/build", { method: "POST" });
    toast("Graph rebuilt from the study brief.");
    await loadGraph(); await loadStats();
  } catch (e) { toast("Rebuild failed: " + e.message); setLoading(false); }
}

async function fetchLive() {
  setLoading(true);
  const btn = document.getElementById("btnFetch");
  btn.disabled = true; btn.textContent = "Fetching…";
  try {
    const r = await api("/api/fetch", { method: "POST", body: JSON.stringify({ per_query: 6 }) });
    toast(`Pulled ${r.items} live items · added live data to the graph.`);
    renderNews(r.headlines || []);
    switchTab("news");
    await loadGraph(); await loadStats();
  } catch (e) {
    toast("Live fetch failed: " + e.message); setLoading(false);
  } finally {
    btn.disabled = false; btn.textContent = "Fetch Live Data";
  }
}

function renderNews(items) {
  const list = document.getElementById("newsList");
  if (!items.length) { list.innerHTML = `<li>No items.</li>`; return; }
  list.innerHTML = items.map((it) =>
    `<li><a href="${it.link}" target="_blank" rel="noopener">${escapeHtml(it.title)}</a>
     <span class="src">${escapeHtml(it.source || "web")}</span></li>`).join("");
}

// ---- Tabs ----------------------------------------------------------------
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".tab-body").forEach((b) => b.classList.toggle("active", b.id === "tab-" + name));
}

// ---- Wire up -------------------------------------------------------------
document.getElementById("composer").addEventListener("submit", (e) => {
  e.preventDefault();
  const inp = document.getElementById("question");
  const q = inp.value; inp.value = "";
  askQuestion(q);
});
document.getElementById("btnBuild").addEventListener("click", rebuild);
document.getElementById("btnFetch").addEventListener("click", fetchLive);
document.getElementById("btnFit").addEventListener("click", () => { resetHighlight(); network && network.fit({ animation: true }); });
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));
document.getElementById("searchBox").addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase().trim();
  if (!q || !nodesDS) { resetHighlight(); return; }
  const matches = nodesDS.getIds().filter((id) => id.toLowerCase().includes(q));
  nodesDS.update(nodesDS.getIds().map((id) => ({ id, opacity: matches.includes(id) ? 1 : 0.15 })));
  if (matches.length) network.fit({ nodes: matches, animation: true });
});

// ---- Boot ----------------------------------------------------------------
(async function init() {
  await checkHealth();
  await loadGraph();
  await loadStats();
  await loadSuggestions();
  setInterval(checkHealth, 15000);

  // If arriving from the home page with ?q=..., auto-ask that question.
  const params = new URLSearchParams(window.location.search);
  const q = params.get("q");
  if (q) {
    const inp = document.getElementById("question");
    if (inp) inp.value = q;
    askQuestion(q);
  }
})();
