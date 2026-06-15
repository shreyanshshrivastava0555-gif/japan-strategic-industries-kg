// Home / landing page logic: live stats, health, sample questions.
async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Request failed");
  return res.json();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function loadStats() {
  try {
    const s = await api("/api/stats");
    document.getElementById("hNodes").textContent = s.nodes;
    document.getElementById("hEdges").textContent = s.edges;
    document.getElementById("hMode").textContent = (s.extractor_mode || "offline").toUpperCase();
    document.getElementById("hVersion").textContent = "v" + s.version;
  } catch (e) { /* ignore */ }
}

async function checkHealth() {
  const el = document.getElementById("health");
  try { await api("/api/health"); el.classList.add("ok"); }
  catch { el.classList.remove("ok"); }
}

async function loadSamples() {
  try {
    const r = await api("/api/suggestions");
    const box = document.getElementById("sampleQs");
    box.innerHTML = r.suggestions.map((q) =>
      `<a class="sample-q" href="/graph.html?q=${encodeURIComponent(q)}">
         <span>${escapeHtml(q)}</span><i>→</i>
       </a>`).join("");
  } catch (e) { /* ignore */ }
}

(async function init() {
  await checkHealth();
  await loadStats();
  await loadSamples();
  setInterval(checkHealth, 15000);
})();
