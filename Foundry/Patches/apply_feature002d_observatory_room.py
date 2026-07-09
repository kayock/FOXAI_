from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature002d_before_observatory_room_{STAMP}"

STYLE_APPEND = '\n/* Feature 002D - Observatory Room */\n.metricGrid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));\n  gap: 14px;\n}\n\n.metricCard {\n  background: rgba(0,0,0,.22);\n  border: 1px solid rgba(149,215,149,.14);\n  border-radius: 16px;\n  padding: 16px;\n}\n\n.metricCard h5 {\n  margin: 0 0 8px;\n  color: var(--muted);\n  font-size: 13px;\n  text-transform: uppercase;\n  letter-spacing: .12em;\n}\n\n.metricValue {\n  font-size: 26px;\n  font-weight: 900;\n  color: var(--accent);\n  margin-bottom: 8px;\n}\n\n.metricSub {\n  color: var(--muted);\n  font-size: 13px;\n}\n\n.recommendation {\n  border-left: 4px solid var(--accent);\n  background: rgba(0,255,102,.07);\n  border-radius: 12px;\n  padding: 12px;\n  margin-bottom: 10px;\n}\n\n.recommendation.warn {\n  border-left-color: var(--warn);\n  background: rgba(255,209,102,.06);\n}\n\n.recommendation.bad {\n  border-left-color: var(--bad);\n  background: rgba(255,92,92,.06);\n}\n\n.observatoryHero {\n  margin-bottom: 18px;\n}\n\n.roomSplit {\n  display: grid;\n  grid-template-columns: 1.4fr .9fr;\n  gap: 18px;\n}\n\n@media (max-width: 1100px) {\n  .roomSplit { grid-template-columns: 1fr; }\n}\n'
RENDERER_PATCH = '\n// Feature 002D Observatory upgrade\nfunction renderObservatoryUpgrade() {\n  const observatory = document.getElementById(\'observatory\');\n  if (!observatory || observatory.dataset.upgraded === \'true\') return;\n  observatory.dataset.upgraded = \'true\';\n  observatory.innerHTML = `\n    <article class="card wide observatoryHero">\n      <div class="sectionHeader">\n        <div>\n          <p class="eyebrow">Observatory</p>\n          <h4>Host Computer & Workshop Awareness</h4>\n        </div>\n        <span id="observatoryStatus" class="badge">Scanning</span>\n      </div>\n      <p class="roomIntro">The Observatory watches the current computer, FOXAI, runtime status, and what KayocktheOS can do in this session.</p>\n    </article>\n\n    <div class="roomSplit">\n      <div>\n        <article class="card">\n          <h4>Host Machine</h4>\n          <div id="observatoryMetrics" class="metricGrid"></div>\n        </article>\n\n        <article class="card chatCard">\n          <h4>Session Capabilities</h4>\n          <div id="sessionCapabilities" class="capabilityCards"></div>\n        </article>\n      </div>\n\n      <div>\n        <article class="card">\n          <h4>Recommendations</h4>\n          <div id="observatoryRecommendations"></div>\n        </article>\n\n        <article class="card chatCard">\n          <h4>Runtime & AI</h4>\n          <div id="observatoryRuntime" class="smallList"></div>\n        </article>\n      </div>\n    </div>\n  `;\n}\n\nfunction metricCard(label, value, sub=\'\') {\n  return `<div class="metricCard"><h5>${escapeHtml(label)}</h5><div class="metricValue">${escapeHtml(value ?? \'--\')}</div><div class="metricSub">${escapeHtml(sub ?? \'\')}</div></div>`;\n}\n\nfunction rec(text, type=\'ok\') {\n  const cls = type === \'bad\' ? \'bad\' : (type === \'warn\' ? \'warn\' : \'\');\n  return `<div class="recommendation ${cls}">${escapeHtml(text)}</div>`;\n}\n\nfunction renderObservatoryData() {\n  renderObservatoryUpgrade();\n  const sys = state.status?.system || {};\n  const cpu = sys.cpu || {};\n  const mem = sys.memory || {};\n  const disk = sys.disk || {};\n  const gpu = sys.gpu || {};\n  const tools = sys.tools || {};\n  const fox = state.foxai?.summary || {};\n  const runtime = state.runtime || {};\n  const metrics = document.getElementById(\'observatoryMetrics\');\n  const status = document.getElementById(\'observatoryStatus\');\n\n  if (status) {\n    const healthy = !!state.status && !!state.foxai?.exists;\n    status.textContent = healthy ? \'Watching\' : \'Needs Setup\';\n  }\n\n  if (metrics) {\n    metrics.innerHTML = [\n      metricCard(\'Operating System\', sys.os?.release || \'Unknown\', sys.os?.platform || \'\'),\n      metricCard(\'CPU\', cpu.cores_logical ? `${cpu.cores_logical} threads` : \'Unknown\', cpu.name || \'\'),\n      metricCard(\'Memory\', mem.total_gb ? `${mem.total_gb} GB` : \'Unknown\', \'Detected RAM\'),\n      metricCard(\'Disk Free\', disk.free_gb ? `${disk.free_gb} GB` : \'Unknown\', disk.drive || disk.root || \'\'),\n      metricCard(\'GPU\', (gpu.gpus || []).length || \'None\', (gpu.gpus || []).join(\' · \') || \'No GPU names detected\'),\n      metricCard(\'Python\', tools.python?.version || \'Unknown\', tools.python?.path || \'\'),\n      metricCard(\'Node\', tools.node?.installed ? \'Installed\' : \'Missing\', tools.node?.version || \'\'),\n      metricCard(\'Git\', tools.git?.installed ? \'Installed\' : \'Missing\', tools.git?.version || \'\')\n    ].join(\'\');\n  }\n\n  const capsEl = document.getElementById(\'sessionCapabilities\');\n  if (capsEl) {\n    const caps = capabilityData();\n    capsEl.innerHTML = caps.map(c => `\n      <div class="capabilityCard">\n        <div class="icon">${c.icon}</div>\n        <h5>${escapeHtml(c.label)}</h5>\n        <p>${escapeHtml(c.detail)}</p>\n        <div class="score">${c.value ? c.value + \' available\' : \'Unavailable\'}</div>\n      </div>\n    `).join(\'\');\n  }\n\n  const runtimeEl = document.getElementById(\'observatoryRuntime\');\n  if (runtimeEl) {\n    runtimeEl.innerHTML = [\n      item(\'Runtime\', runtime.online ? \'Online\' : \'Offline\', runtime.online ? \'ok\' : \'bad\'),\n      item(\'Runtime Base\', runtime.base || \'http://127.0.0.1:8845\', runtime.base ? \'ok\' : \'wait\'),\n      item(\'FOXAI Assets\', `${fox.total_assets ?? 0} discovered`, (fox.total_assets ?? 0) ? \'ok\' : \'wait\'),\n      item(\'LLM Models\', `${fox.llm_models ?? 0}`, (fox.llm_models ?? 0) ? \'ok\' : \'wait\'),\n      item(\'Image Models\', `${fox.image_models ?? 0}`, (fox.image_models ?? 0) ? \'ok\' : \'wait\')\n    ].join(\'\');\n  }\n\n  const recommendations = [];\n  if (!state.foxai?.exists) recommendations.push([\'FOXAI was not detected at Z:\\\\FOXAI. Discovery needs that warehouse path.\', \'bad\']);\n  if (!runtime.online) recommendations.push([\'Start the selected local model runtime to activate Ask the Academy.\', \'warn\']);\n  if ((fox.llm_models || 0) > 0 && !runtime.online) recommendations.push([\'Models are available. Runtime launch is the next step toward First Contact.\', \'ok\']);\n  if ((fox.image_models || 0) > 0) recommendations.push([\'Image models are discovered. Creative Studio can be wired to ComfyUI next.\', \'ok\']);\n  if (!tools.git?.installed) recommendations.push([\'Git was not detected. Install Git for reliable project history.\', \'warn\']);\n  if (!tools.node?.installed) recommendations.push([\'Node was not detected by Core. Bridge development may need Node available.\', \'warn\']);\n  if (disk.free_gb && disk.free_gb < 80) recommendations.push([\'Disk space is getting low for AI work. Avoid copying large models.\', \'warn\']);\n  if (!recommendations.length) recommendations.push([\'Workshop looks healthy. Continue building from the Bridge.\', \'ok\']);\n\n  const recEl = document.getElementById(\'observatoryRecommendations\');\n  if (recEl) recEl.innerHTML = recommendations.map(([text,type]) => rec(text,type)).join(\'\');\n}\n'

def info(msg):
    print(f"[Feature 002D Observatory] {msg}")

def copy_item(src_rel):
    src = ROOT / src_rel
    if not src.exists():
        return
    dst = BACKUP_DIR / src_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)

def backup_project():
    info("Creating safety backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for item in ["Bridge","manifest.yaml","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def patch_bridge():
    style = ROOT / "Bridge" / "style.css"
    renderer = ROOT / "Bridge" / "renderer.js"
    if style.exists():
        old = style.read_text(encoding="utf-8", errors="replace")
        if "Feature 002D - Observatory Room" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 002D Observatory upgrade" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        # Hook into render if not already hooked
        if "renderObservatoryData();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderObservatoryData();")
        renderer.write_text(old, encoding="utf-8")
    info("Observatory room upgraded.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_002d_observatory_room: enabled" not in text:
        text += "\n  feature_002d_observatory_room: enabled\n" if "features:" in text else "\nfeatures:\n  feature_002d_observatory_room: enabled\n"
        path.write_text(text, encoding="utf-8")

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_002D_OBSERVATORY_ROOM.md", """# Feature 002D - Observatory Room

The Observatory now shows live host-machine and session awareness.

## Adds

- Host machine metric cards
- Runtime and FOXAI status
- Session capability cards
- Recommendations based on current environment

## Run

```bat
Start_Bridge.bat
```

Open the Observatory room.
""")
    write_text("Forge/Decisions/0021_observatory_room.md", """# Decision 0021 - Observatory Room

The Observatory watches the current host computer and recommends what the Operator can do next.

It should notice opportunities, not just report raw data.
""")
    write_text("Foundry/Releases/feature002d_observatory_room_notes.md", "# Feature 002D - Observatory Room\n\nAdds live host/session cards and recommendations.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 002D - Observatory Room\n\n- Added Observatory metric cards.\n- Added runtime and FOXAI session status.\n- Added recommendation panel.\n- Reinforces Observatory as the room that watches and advises.\n"
    if "Feature 002D - Observatory Room" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    patch_bridge()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 002D Observatory Room complete.")
    info("Restart Start_Bridge.bat and open Observatory.")

if __name__ == "__main__":
    main()
