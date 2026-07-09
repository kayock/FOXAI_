from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature004b_before_kobold_panel_{STAMP}"

STYLE_APPEND = '\n/* Feature 004B - Kobold Engine Check Panel */\n.koboldPanel {\n  border: 1px solid rgba(0,255,102,.24);\n  background: linear-gradient(135deg, rgba(0,255,102,.06), rgba(0,0,0,.24));\n}\n.koboldSteps {\n  display: grid;\n  gap: 10px;\n  margin-top: 12px;\n}\n.koboldStep {\n  display: grid;\n  grid-template-columns: 34px 1fr;\n  gap: 10px;\n  padding: 10px;\n  background: rgba(0,0,0,.22);\n  border-radius: 12px;\n}\n.koboldBadgeGood { color: var(--accent); }\n.koboldBadgeWarn { color: var(--warn); }\n'
RENDERER_PATCH = '\n// Feature 004B Kobold Engine Check Panel\nasync function fetchKoboldStatus() {\n  try {\n    return await fetchJson(\'/api/kobold\');\n  } catch {\n    return null;\n  }\n}\n\nfunction renderKoboldPanelShell() {\n  const home = document.getElementById(\'home\');\n  if (!home || document.getElementById(\'koboldEnginePanel\')) return;\n\n  const panel = document.createElement(\'article\');\n  panel.id = \'koboldEnginePanel\';\n  panel.className = \'card chatCard koboldPanel\';\n  panel.innerHTML = `\n    <div class="sectionHeader">\n      <div>\n        <p class="eyebrow">Feature 004</p>\n        <h4>KoboldCpp Engine Adapter</h4>\n      </div>\n      <span id="koboldEngineBadge" class="badge">Checking</span>\n    </div>\n    <div id="koboldEngineDetails" class="smallList"></div>\n    <div class="koboldSteps">\n      <div class="koboldStep">\n        <div class="stepNumber">1</div>\n        <div><strong>Install Engine</strong><br><span class="pathText">Z:\\\\KayocktheOS\\\\Engine\\\\KoboldCpp\\\\koboldcpp.exe</span></div>\n      </div>\n      <div class="koboldStep">\n        <div class="stepNumber">2</div>\n        <div><strong>Start Engine</strong><br><span class="pathText">Z:\\\\KayocktheOS\\\\AI\\\\Gateway\\\\START_KOBOLD_ENGINE.bat</span></div>\n      </div>\n      <div class="koboldStep">\n        <div class="stepNumber">3</div>\n        <div><strong>Ask the Academy</strong><br><span>Bridge chat uses the engine adapter when available.</span></div>\n      </div>\n    </div>\n  `;\n\n  const firstContact = document.getElementById(\'firstContactPanel\');\n  if (firstContact) firstContact.insertAdjacentElement(\'afterend\', panel);\n  else {\n    const chatCard = document.querySelector(\'#home .chatCard\');\n    if (chatCard) home.insertBefore(panel, chatCard);\n    else home.appendChild(panel);\n  }\n}\n\nasync function renderKoboldPanel() {\n  renderKoboldPanelShell();\n\n  const badge = document.getElementById(\'koboldEngineBadge\');\n  const details = document.getElementById(\'koboldEngineDetails\');\n  if (!badge || !details) return;\n\n  const st = await fetchKoboldStatus();\n\n  if (!st) {\n    badge.textContent = \'Core Restart Needed\';\n    details.innerHTML = item(\'Kobold Adapter\', \'Restart KayocktheOS Core so /api/kobold becomes available.\', \'wait\');\n    return;\n  }\n\n  const online = !!st.health?.online;\n  const engineExists = !!st.engine_exists;\n  const modelExists = !!st.model_exists;\n\n  badge.textContent = online ? \'Engine Online\' : (engineExists ? \'Ready to Start\' : \'Engine Missing\');\n\n  details.innerHTML = [\n    item(\'KoboldCpp EXE\', st.engine_path || \'Missing: put koboldcpp.exe in Engine\\\\KoboldCpp\', engineExists ? \'ok\' : \'bad\'),\n    item(\'Selected Model\', st.model_path || \'No GGUF model found\', modelExists ? \'ok\' : \'bad\'),\n    item(\'Server\', st.health?.base || \'http://127.0.0.1:5001\', online ? \'ok\' : \'wait\'),\n    item(\'Launcher\', st.launcher || \'AI\\\\Gateway\\\\START_KOBOLD_ENGINE.bat\', \'ok\'),\n    item(\'Status\', online ? \'Online — Ask the Academy now\' : \'Offline — start Kobold engine first\', online ? \'ok\' : \'wait\')\n  ].join(\'\');\n}\n'

def info(msg):
    print(f"[Feature 004B Kobold Panel] {msg}")

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
    info("Creating safety backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for item in ["Bridge","Foundry","Docs","Forge","00_START_HERE","manifest.yaml"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def patch_bridge():
    style = ROOT / "Bridge" / "style.css"
    renderer = ROOT / "Bridge" / "renderer.js"

    if style.exists():
        old = style.read_text(encoding="utf-8", errors="replace")
        if "Feature 004B - Kobold Engine Check Panel" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")

    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 004B Kobold Engine Check Panel" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderKoboldPanel();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderKoboldPanel();")
        renderer.write_text(old, encoding="utf-8")

    info("Kobold Engine panel added to Bridge Home.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_004b_kobold_engine_check_panel: enabled" not in text:
        text += "\n  feature_004b_kobold_engine_check_panel: enabled\n" if "features:" in text else "\nfeatures:\n  feature_004b_kobold_engine_check_panel: enabled\n"
        path.write_text(text, encoding="utf-8")

def docs():
    write_text("Docs/FEATURE_004B_KOBOLD_ENGINE_CHECK_PANEL.md", """# Feature 004B - Kobold Engine Check Panel

Adds a visible KoboldCpp engine status panel to the Bridge Home room.

## Shows

- Whether `koboldcpp.exe` was found
- Which GGUF model was selected
- Whether the Kobold server is online
- The launcher path

## Expected launcher

```text
Z:\\KayocktheOS\\AI\\Gateway\\START_KOBOLD_ENGINE.bat
```
""")
    write_text("Forge/Decisions/0037_kobold_panel.md", """# Decision 0037 - Kobold Engine Check Panel

Engine adapters must be visible and diagnosable from the Bridge.
""")
    write_text("Foundry/Releases/feature004b_kobold_engine_check_panel_notes.md", "# Feature 004B - Kobold Panel\n\nAdds visible Bridge panel for KoboldCpp readiness.\n")

def changelog():
    path = ROOT / "00_START_HERE" / "CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 004B - Kobold Engine Check Panel\n\n- Added visible KoboldCpp status panel to Bridge Home.\n- Shows engine path, selected model, server status, and launcher path.\n"
    if "Feature 004B - Kobold Engine Check Panel" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    patch_bridge()
    update_manifest()
    docs()
    changelog()
    info("Feature 004B Kobold Engine Check Panel complete.")
    info("Restart the Bridge and check Home.")

if __name__ == "__main__":
    main()
