from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature007_before_academy_bridge_{STAMP}"

STYLE_APPEND = '\n/* Feature 007 - Academy Bridge Dashboard */\n.academyBridgeHero {\n  border: 1px solid rgba(0,255,102,.28);\n  background:\n    radial-gradient(circle at top left, rgba(0,255,102,.13), transparent 36%),\n    linear-gradient(135deg, rgba(0,35,15,.75), rgba(0,0,0,.55));\n  border-radius: 24px;\n  padding: 28px;\n  margin-bottom: 18px;\n}\n\n.academyBridgeHero h2 {\n  margin: 8px 0 10px;\n  font-size: clamp(32px, 4vw, 56px);\n  line-height: .95;\n}\n\n.academyBridgeHero .motto {\n  color: var(--muted);\n  font-size: 16px;\n  max-width: 760px;\n}\n\n.academyGrid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(245px, 1fr));\n  gap: 16px;\n  margin-top: 18px;\n}\n\n.academyCard {\n  border: 1px solid rgba(149,215,149,.16);\n  background: rgba(0,0,0,.25);\n  border-radius: 20px;\n  padding: 18px;\n  min-height: 160px;\n}\n\n.academyCard h4 {\n  color: var(--accent);\n  margin: 0 0 8px;\n}\n\n.academyCard .professor {\n  color: var(--warn);\n  font-weight: 800;\n  margin-bottom: 10px;\n}\n\n.academyCard p {\n  color: var(--muted);\n  margin: 0 0 12px;\n}\n\n.academyActions {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 8px;\n}\n\n.academyButton {\n  border: 1px solid rgba(0,255,102,.36);\n  background: rgba(0,255,102,.08);\n  color: var(--text);\n  border-radius: 999px;\n  padding: 8px 12px;\n  font-weight: 800;\n  cursor: default;\n}\n\n.academyStatusLine {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 10px;\n  margin-top: 16px;\n}\n\n.academyPill {\n  border: 1px solid rgba(149,215,149,.18);\n  border-radius: 999px;\n  padding: 8px 12px;\n  background: rgba(0,0,0,.24);\n  color: var(--muted);\n}\n\n.academyPill.ok {\n  color: var(--accent);\n}\n\n.academyPill.wait {\n  color: var(--warn);\n}\n'
RENDERER_PATCH = '\n// Feature 007 Academy Bridge Dashboard\nasync function fetchAcademyBridgeStatus() {\n  try { return await fetchJson(\'/api/core-working\'); } catch { return null; }\n}\n\nfunction renderAcademyBridgeDashboard() {\n  const home = document.getElementById(\'home\');\n  if (!home || document.getElementById(\'academyBridgeDashboard\')) return;\n\n  const dash = document.createElement(\'section\');\n  dash.id = \'academyBridgeDashboard\';\n  dash.className = \'academyBridgeHero\';\n  dash.innerHTML = `\n    <p class="eyebrow">KayocktheOS Academy Bridge</p>\n    <h2>Welcome back, Commander.</h2>\n    <p class="motto">The Academy is open. Today\'s lesson awaits. KayocktheOS now acts as the command bridge over mature local AI tools instead of reinventing them.</p>\n    <div id="academyStatusLine" class="academyStatusLine">\n      <span class="academyPill wait">Checking AnythingLLM</span>\n      <span class="academyPill wait">Checking ComfyUI</span>\n      <span class="academyPill wait">Checking Runtime</span>\n    </div>\n    <div class="academyGrid">\n      <article class="academyCard">\n        <h4>Engineering Academy</h4>\n        <div class="professor">Professor Asimov</div>\n        <p>Code scanning, architecture reports, project memory, and engineering review through AnythingLLM.</p>\n        <div class="academyActions">\n          <span class="academyButton">Open AnythingLLM</span>\n          <span class="academyButton">Engineering Snapshot</span>\n        </div>\n      </article>\n      <article class="academyCard">\n        <h4>Creative Studio</h4>\n        <div class="professor">Professor Roddenberry</div>\n        <p>Image generation, workflows, galleries, and future motion-comic tools through FOXAI ComfyUI.</p>\n        <div class="academyActions">\n          <span class="academyButton">Launch ComfyUI</span>\n          <span class="academyButton">Open Gallery</span>\n        </div>\n      </article>\n      <article class="academyCard">\n        <h4>Knowledge Wing</h4>\n        <div class="professor">Professor Sagan</div>\n        <p>Iron Library, prompts, mission archive, manuals, and searchable local documents.</p>\n        <div class="academyActions">\n          <span class="academyButton">Open Library</span>\n          <span class="academyButton">Refresh Index</span>\n        </div>\n      </article>\n      <article class="academyCard">\n        <h4>Repair Bay</h4>\n        <div class="professor">Professor Kayock</div>\n        <p>Diagnostics, launch cleanup, system health, runtime checks, and safe repair plans.</p>\n        <div class="academyActions">\n          <span class="academyButton">Run Diagnostics</span>\n          <span class="academyButton">View Logs</span>\n        </div>\n      </article>\n    </div>\n  `;\n\n  const firstCard = home.querySelector(\'.card\');\n  if (firstCard) home.insertBefore(dash, firstCard);\n  else home.prepend(dash);\n\n  updateAcademyBridgeStatus();\n}\n\nasync function updateAcademyBridgeStatus() {\n  const line = document.getElementById(\'academyStatusLine\');\n  if (!line) return;\n\n  const st = await fetchAcademyBridgeStatus();\n  if (!st) {\n    line.innerHTML = `\n      <span class="academyPill wait">Core status unavailable</span>\n      <span class="academyPill wait">Restart Core API</span>\n    `;\n    return;\n  }\n\n  const anything = st.anythingllm?.found;\n  const comfy = st.comfyui?.found;\n  const runtime = st.koboldcpp?.found;\n\n  line.innerHTML = `\n    <span class="academyPill ${anything ? \'ok\' : \'wait\'}">AnythingLLM ${anything ? \'Found\' : \'Missing\'}</span>\n    <span class="academyPill ${comfy ? \'ok\' : \'wait\'}">ComfyUI ${comfy ? \'Found\' : \'Use FOXAI launcher\'}</span>\n    <span class="academyPill ${runtime ? \'ok\' : \'wait\'}">Runtime ${runtime ? \'Found\' : \'Optional\'}</span>\n    <span class="academyPill ok">Legacy First Contact Redirected</span>\n  `;\n}\n'

def info(msg):
    print(f"[Feature 007 Academy Bridge] {msg}")

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

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def backup_project():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for item in ["Bridge", "Foundry", "Docs", "Forge", "00_START_HERE", "manifest.yaml"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def patch_bridge():
    style = ROOT / "Bridge" / "style.css"
    renderer = ROOT / "Bridge" / "renderer.js"

    if style.exists():
        old = style.read_text(encoding="utf-8", errors="replace")
        if "Feature 007 - Academy Bridge Dashboard" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    else:
        info("Bridge/style.css missing; skipped style patch.")

    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 007 Academy Bridge Dashboard" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderAcademyBridgeDashboard();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderAcademyBridgeDashboard();")
        renderer.write_text(old, encoding="utf-8")
    else:
        info("Bridge/renderer.js missing; skipped renderer patch.")

    info("Academy Bridge Dashboard added to Home.")

def docs():
    write_text("Docs/FEATURE_007_ACADEMY_BRIDGE_DASHBOARD.md", """# Feature 007 - Academy Bridge Dashboard

Adds the Academy Bridge as the top-level Home experience.

## Purpose

KayocktheOS is the command bridge over mature local AI tools:

- AnythingLLM: engineering knowledge and project scanning
- ComfyUI / FOXAI: creative workflows
- KoboldCpp / runtime adapters: optional local model serving
- Repair Bay: diagnostics and health

## Philosophy

Do not reinvent mature tools. Orchestrate them.
""")
    write_text("Forge/Decisions/0042_academy_bridge_dashboard.md", """# Decision 0042 - Academy Bridge Dashboard

KayocktheOS should present itself as the Academy Bridge, not as a replacement for every AI subsystem.
""")
    write_text("Foundry/Releases/feature007_academy_bridge_dashboard_notes.md", "# Feature 007 - Academy Bridge Dashboard\n\nAdds command-bridge style Home dashboard.\n")

def changelog():
    path = ROOT / "00_START_HERE" / "CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 007 - Academy Bridge Dashboard\n\n- Added Academy Bridge hero to Home.\n- Added Engineering Academy, Creative Studio, Knowledge Wing, and Repair Bay cards.\n- Added status line for AnythingLLM, ComfyUI, and local runtime.\n- Reinforces KayocktheOS as orchestration layer rather than reinvented runtime.\n"
    if "Feature 007 - Academy Bridge Dashboard" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    patch_bridge()
    docs()
    changelog()
    info("Feature 007 Academy Bridge Dashboard complete.")
    info("Restart the Bridge and open Home.")

if __name__ == "__main__":
    main()
