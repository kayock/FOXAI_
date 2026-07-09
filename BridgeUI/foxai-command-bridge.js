// FOXAI Orion v9.0 — The Bridge Awakens

async function readJson(paths) {
  for (const path of paths) {
    try {
      const res = await fetch(path + "?t=" + Date.now());
      if (res.ok) return await res.json();
    } catch (err) {}
  }
  return null;
}

function el(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const node = el(id);
  if (node) node.textContent = value ?? "—";
}

function renderDepartments(feed) {
  const root = el("department-grid");
  if (!root) return;

  const cards = feed?.department_cards || [];
  root.innerHTML = cards.map(card => {
    const services = (card.services || []).length;
    const tools = Object.keys(card.tools || {}).length;
    const status = card.status || (card.ok ? "ONLINE" : "STANDBY");
    return `
      <article class="dept-card" data-accent="${card.accent || "purple"}">
        <div class="dept-head">
          <div>
            <div class="dept-title">${card.title || card.id}</div>
            <div class="dept-officer">${card.officer || "Unassigned"}</div>
          </div>
          <div class="status-pill ${card.ok ? "ok" : ""}">${status}</div>
        </div>
        <div class="dept-details">
          <div>Services<br><span class="detail-value">${services}</span></div>
          <div>Tools<br><span class="detail-value">${tools}</span></div>
        </div>
      </article>
    `;
  }).join("");
}

function renderCaptainLog(feed) {
  const root = el("captains-log");
  if (!root) return;

  const entries = ((feed?.captains_log || {}).entries || []).slice(-7).reverse();

  if (!entries.length) {
    root.innerHTML = `<div class="log-entry">No Captain's Log entries yet.</div>`;
    return;
  }

  root.innerHTML = entries.map(entry => `
    <div class="log-entry">
      <div><span class="log-time">${entry.timestamp || ""}</span></div>
      <div><span class="log-source">${entry.source || "FOXAI"}</span> — ${entry.message || ""}</div>
    </div>
  `).join("");
}

function renderFleet(feed) {
  const root = el("fleet-list");
  if (!root) return;

  const shuttles = feed?.kernel?.raw?.fleet?.data?.shuttles || {};
  const items = Object.values(shuttles).slice(0, 8);

  if (!items.length) {
    root.innerHTML = `<div class="fleet-item"><div class="fleet-name">Fleet awaiting report</div><div class="fleet-meta">—</div></div>`;
    return;
  }

  root.innerHTML = items.map(item => `
    <div class="fleet-item">
      <div>
        <div class="fleet-name">${item.callsign || item.name || item.key}</div>
        <div class="fleet-meta">${item.department || "Fleet"} · ${item.category || item.kind || ""}</div>
      </div>
      <div class="status-pill ok">${item.service_state || item.health_status || "READY"}</div>
    </div>
  `).join("");
}

function renderMission(feed) {
  const latest = feed?.latest_result;
  setText("latest-mission", latest?.request || feed?.summary?.latest_mission || "No recent mission.");
  setText("latest-event", feed?.summary?.latest_event || "Awaiting event.");
}

function renderFeed(feed) {
  setText("kernel-badge", feed?.kernel?.status || "WAITING");
  setText("metric-departments", feed?.summary?.department_count ?? "—");
  setText("metric-online", feed?.summary?.departments_online ?? "—");
  setText("metric-packages", feed?.summary?.runtime_packages ?? "—");
  setText("metric-log", feed?.summary?.captains_log_entries ?? "—");
  setText("generated-at", feed?.generated_at || "—");

  renderDepartments(feed);
  renderCaptainLog(feed);
  renderFleet(feed);
  renderMission(feed);
}

async function refreshBridge() {
  const feed = await readJson([
    "../OpsBridge/outbox/bridge_feed.json",
    "./OpsBridge/outbox/bridge_feed.json",
    "/OpsBridge/outbox/bridge_feed.json"
  ]);

  if (!feed) {
    setText("kernel-badge", "WAITING FOR BRIDGE FEED");
    return;
  }

  renderFeed(feed);
}

function openLocal(path) {
  window.location.href = path;
}

document.addEventListener("DOMContentLoaded", () => {
  refreshBridge();
  setInterval(refreshBridge, 5000);
});
