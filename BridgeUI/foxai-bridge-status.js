/* FOXAI Project Orion v7.4 Bridge Status Panel - Live Captain's Log */

async function foxaiReadJson(path) {
  try {
    const response = await fetch(path + "?t=" + Date.now());
    if (!response.ok) throw new Error(response.statusText);
    return await response.json();
  } catch (error) {
    return null;
  }
}

async function foxaiReadFirstJson(paths) {
  for (const path of paths) {
    const data = await foxaiReadJson(path);
    if (data) return data;
  }
  return null;
}

function foxaiEl(id) {
  return document.getElementById(id);
}

function foxaiSet(id, value) {
  const el = foxaiEl(id);
  if (el) el.textContent = value ?? "—";
}

function foxaiStatusClass(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("active") || text.includes("ready") || text.includes("pass") || text.includes("online") || text.includes("ok") || text === "true") return "foxai-status-active";
  if (text.includes("error") || text.includes("fail") || text.includes("missing") || text.includes("attention") || text === "false") return "foxai-status-error";
  return "foxai-status-standby";
}

function foxaiApplyStatus(id, value) {
  const el = foxaiEl(id);
  if (!el) return;
  el.textContent = value ?? "—";
  el.className = foxaiStatusClass(value);
}

function foxaiRenderTools(tools) {
  const target = foxaiEl("foxai-engineering-tools");
  if (!target) return;

  target.innerHTML = "";

  const entries = Object.entries(tools || {});
  if (!entries.length) {
    target.textContent = "No tool report found.";
    return;
  }

  for (const [name, item] of entries) {
    const div = document.createElement("div");
    const ready = item.ok || item.status === "ready";
    div.className = "foxai-tool " + (ready ? "ready" : "missing");
    div.textContent = `${name}: ${item.status || (ready ? "ready" : "missing")}`;
    target.appendChild(div);
  }
}

function foxaiRenderCaptainLog(log) {
  const target = foxaiEl("foxai-captains-log");
  if (!target) return;

  const entries = (log && Array.isArray(log.entries)) ? log.entries.slice(-8).reverse() : [];

  if (!entries.length) {
    target.textContent = "No Captain's Log entries yet.";
    return;
  }

  target.textContent = entries.map(entry => {
    const time = entry.timestamp || "unknown time";
    const source = entry.source || "FOXAI";
    const severity = String(entry.severity || "info").toUpperCase();
    const message = entry.message || "";
    return `${time} — ${source}\n[${severity}] ${message}`;
  }).join("\n\n");
}

function foxaiRenderLatestEvent(event) {
  if (!event) {
    foxaiSet("foxai-latest-event", "—");
    return;
  }
  foxaiSet("foxai-latest-event", `${event.source || "FOXAI"}: ${event.message || event.type || "event"}`);
}

async function foxaiUpdateBridgeStatus() {
  const paths = {
    department: [
      "./OpsBridge/outbox/department_registry_status.json",
      "../OpsBridge/outbox/department_registry_status.json",
      "/OpsBridge/outbox/department_registry_status.json"
    ],
    engineering: [
      "./OpsBridge/outbox/engineering_commissioning_certificate.json",
      "../OpsBridge/outbox/engineering_commissioning_certificate.json",
      "/OpsBridge/outbox/engineering_commissioning_certificate.json"
    ],
    kernel: [
      "./OpsBridge/outbox/kernel_status.json",
      "../OpsBridge/outbox/kernel_status.json",
      "/OpsBridge/outbox/kernel_status.json"
    ],
    latest: [
      "./OpsBridge/outbox/latest_result.json",
      "../OpsBridge/outbox/latest_result.json",
      "/OpsBridge/outbox/latest_result.json"
    ],
    captainsLog: [
      "./OpsBridge/outbox/captains_log.json",
      "../OpsBridge/outbox/captains_log.json",
      "/OpsBridge/outbox/captains_log.json"
    ],
    latestEvent: [
      "./OpsBridge/outbox/latest_event.json",
      "../OpsBridge/outbox/latest_event.json",
      "/OpsBridge/outbox/latest_event.json"
    ]
  };

  const deptStatus = await foxaiReadFirstJson(paths.department);
  const engineeringCert = await foxaiReadFirstJson(paths.engineering);
  const kernel = await foxaiReadFirstJson(paths.kernel);
  const latest = await foxaiReadFirstJson(paths.latest);
  const captainsLog = await foxaiReadFirstJson(paths.captainsLog);
  const latestEvent = await foxaiReadFirstJson(paths.latestEvent);

  foxaiSet("foxai-last-refresh", new Date().toLocaleTimeString());

  if (kernel) {
    foxaiApplyStatus("foxai-kernel-status", kernel.ok ? "KERNEL READY" : "KERNEL NEEDS ATTENTION");
    foxaiSet("foxai-fleet-count", kernel.fleet?.summary?.total ?? "—");
    foxaiSet("foxai-runtime-packages", kernel.runtime?.package_count ?? "—");
  } else {
    foxaiApplyStatus("foxai-kernel-status", "BRIDGE WAITING");
  }

  let engineering = null;
  if (deptStatus?.departments) {
    engineering = deptStatus.departments.find(d => d.id === "engineering");
  }

  if (engineeringCert) {
    foxaiApplyStatus("foxai-engineering-status", engineeringCert.status || "UNKNOWN");
    foxaiSet("foxai-engineering-officer", engineeringCert.officer || "Chief Engineer Ada");
  } else if (engineering) {
    foxaiApplyStatus("foxai-engineering-status", engineering.health?.status || (engineering.health?.ok ? "ACTIVE" : "NEEDS_ATTENTION"));
    foxaiSet("foxai-engineering-officer", engineering.officer?.name || "Chief Engineer Ada");
  } else {
    foxaiApplyStatus("foxai-engineering-status", "NOT DISCOVERED");
    foxaiSet("foxai-engineering-officer", "Chief Engineer Ada");
  }

  const certEngineering = engineeringCert?.registry_status?.departments?.find(d => d.id === "engineering");
  foxaiRenderTools(engineering?.health?.tools || certEngineering?.health?.tools);

  foxaiApplyStatus("foxai-science-status", "PLANNED");
  foxaiSet("foxai-science-officer", "Professor Carl Sagan");

  if (latest) {
    foxaiApplyStatus("foxai-latest-mission-status", latest.ok ? "MISSION OK" : "MISSION FAILED");
    foxaiSet("foxai-latest-mission", latest.request || latest.report?.request || "—");
  } else {
    foxaiApplyStatus("foxai-latest-mission-status", "NO RECENT MISSION");
    foxaiSet("foxai-latest-mission", "—");
  }

  foxaiRenderLatestEvent(latestEvent);
  foxaiRenderCaptainLog(captainsLog);
}

document.addEventListener("DOMContentLoaded", () => {
  foxaiUpdateBridgeStatus();
  setInterval(foxaiUpdateBridgeStatus, 5000);
});
