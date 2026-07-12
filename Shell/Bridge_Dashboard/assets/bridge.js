function dot(status) {
  if (status === "OK" || status === "enabled" || status === "ready") return "ok";
  if (status === "planned") return "wait";
  return "bad";
}

async function loadStatus() {
  const badge = document.getElementById("api-status");
  try {
    const res = await fetch("http://127.0.0.1:8844/api/status", {cache: "no-store"});
    const data = await res.json();

    badge.textContent = "CORE API ONLINE";
    badge.classList.remove("offline");

    document.getElementById("version").textContent =
      `${data.project.name} v${data.project.version} — ${data.project.codename}`;
    document.getElementById("greeting").textContent =
      `Welcome back, ${data.operator.display_name}.`;
    document.getElementById("quote").textContent =
      `“${data.operator.quote}”`;

    document.getElementById("enabled-count").textContent = data.summary.enabled_modules;
    document.getElementById("planned-count").textContent = data.summary.planned_modules;
    document.getElementById("health-count").textContent =
      `${data.summary.health_ok}/${data.summary.health_total}`;
    document.getElementById("shell-state").textContent = data.shell.status;

    const health = document.getElementById("health-list");
    health.innerHTML = "";
    data.health.forEach(item => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="${dot(item.status)}"></span>${item.label} <span class="small">— ${item.status} — ${item.path}</span>`;
      health.appendChild(li);
    });

    const modules = document.getElementById("module-list");
    modules.innerHTML = "";
    data.modules.forEach(item => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="${dot(item.status)}"></span>${item.name} <span class="small">— ${item.status} — ${item.owner}</span>`;
      modules.appendChild(li);
    });

    document.getElementById("logs").textContent =
      data.recent_logs && data.recent_logs.length ? data.recent_logs.join("\n") : "No boot log entries yet.";

    document.getElementById("updated").textContent = `Last updated: ${data.timestamp}`;
  } catch (err) {
    badge.textContent = "CORE API OFFLINE";
    badge.classList.add("offline");
    document.getElementById("logs").textContent =
      "The dashboard opened, but the local Core API is offline. Start KayocktheOS through Start_KayocktheOS.bat.";
  }
}

loadStatus();
setInterval(loadStatus, 5000);
