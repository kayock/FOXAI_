/* FOXAI Operation Bridge Alive v8.0 Bridge Feed Renderer */

async function foxaiLoadBridgeFeed() {
  const paths = [
    "./OpsBridge/outbox/bridge_feed.json",
    "../OpsBridge/outbox/bridge_feed.json",
    "/OpsBridge/outbox/bridge_feed.json"
  ];

  for (const path of paths) {
    try {
      const res = await fetch(path + "?t=" + Date.now());
      if (res.ok) return await res.json();
    } catch (e) {}
  }
  return null;
}

function foxaiBridgeAccentClass(accent) {
  return "foxai-card-accent-" + (accent || "purple");
}

function foxaiRenderBridgeFeed(feed) {
  const root = document.getElementById("foxai-bridge-feed");
  if (!root) return;

  if (!feed) {
    root.innerHTML = `<div class="foxai-card"><h3>Bridge Feed</h3><p>Waiting for bridge_feed.json...</p></div>`;
    return;
  }

  const cards = (feed.department_cards || []).map(card => {
    const toolCount = Object.keys(card.tools || {}).length;
    const svcCount = (card.services || []).length;
    const statusClass = card.ok ? "foxai-status-active" : "foxai-status-standby";
    return `
      <div class="foxai-card ${foxaiBridgeAccentClass(card.accent)}">
        <h3>${card.title}</h3>
        <div class="foxai-row"><span>Status</span><strong class="${statusClass}">${card.status}</strong></div>
        <div class="foxai-row"><span>Officer</span><strong>${card.officer}</strong></div>
        <div class="foxai-row"><span>Services</span><strong>${svcCount}</strong></div>
        <div class="foxai-row"><span>Tools</span><strong>${toolCount}</strong></div>
      </div>
    `;
  }).join("");

  const entries = ((feed.captains_log || {}).entries || []).slice(-6).reverse().map(entry => {
    return `${entry.timestamp || ""} — ${entry.source || "FOXAI"}\n[${String(entry.severity || "info").toUpperCase()}] ${entry.message || ""}`;
  }).join("\n\n");

  root.innerHTML = `
    <section class="foxai-bridge-status">
      <div class="foxai-bridge-header">
        <div>
          <div class="foxai-title">${feed.identity?.name || "FOXAI Command OS"}</div>
          <div class="foxai-subtitle">${feed.identity?.subtitle || "Ultimate Edifier Platform"} — Operation Bridge Alive</div>
        </div>
        <div class="foxai-kernel-pill">${feed.kernel?.status || "WAITING"}</div>
      </div>

      <div class="foxai-grid">
        <div class="foxai-card foxai-card-accent-purple">
          <h3>System Summary</h3>
          <div class="foxai-row"><span>Departments</span><strong>${feed.summary?.department_count ?? "—"}</strong></div>
          <div class="foxai-row"><span>Online</span><strong>${feed.summary?.departments_online ?? "—"}</strong></div>
          <div class="foxai-row"><span>Runtime Packages</span><strong>${feed.summary?.runtime_packages ?? "—"}</strong></div>
          <div class="foxai-row"><span>Update Center</span><strong>${feed.summary?.update_status ?? "—"}</strong></div>
        </div>
        ${cards}
      </div>

      <div class="foxai-card" style="margin-top:14px;">
        <h3>Captain's Log</h3>
        <div class="foxai-log">${entries || "No entries yet."}</div>
      </div>

      <div class="foxai-bridge-footer">Bridge feed generated: ${feed.generated_at || "—"}</div>
    </section>
  `;
}

async function foxaiRefreshBridgeFeed() {
  foxaiRenderBridgeFeed(await foxaiLoadBridgeFeed());
}

document.addEventListener("DOMContentLoaded", () => {
  foxaiRefreshBridgeFeed();
  setInterval(foxaiRefreshBridgeFeed, 5000);
});
