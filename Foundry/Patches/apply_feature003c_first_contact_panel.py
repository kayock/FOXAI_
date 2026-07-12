from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature003c_before_first_contact_panel_{STAMP}"

STYLE_APPEND = '\n/* Feature 003C - First Contact Bridge Panel */\n.firstContactPanel {\n  border: 1px solid rgba(0,255,102,.24);\n  background: linear-gradient(135deg, rgba(0,255,102,.07), rgba(0,0,0,.22));\n}\n\n.firstContactSteps {\n  display: grid;\n  gap: 10px;\n  margin-top: 12px;\n}\n\n.firstContactStep {\n  display: grid;\n  grid-template-columns: 34px 1fr;\n  gap: 10px;\n  align-items: start;\n  padding: 10px;\n  background: rgba(0,0,0,.22);\n  border-radius: 12px;\n}\n\n.stepNumber {\n  width: 26px;\n  height: 26px;\n  border-radius: 999px;\n  border: 1px solid var(--accent);\n  color: var(--accent);\n  display: grid;\n  place-items: center;\n  font-weight: 900;\n}\n\n.pathText {\n  font-family: Consolas, monospace;\n  color: var(--warn);\n  word-break: break-all;\n}\n'
RENDERER_PATCH = '\n// Feature 003C First Contact Bridge Panel\nasync function fetchFirstContactStatus() {\n  try {\n    return await fetchJson(\'/api/first-contact\');\n  } catch {\n    return null;\n  }\n}\n\nfunction renderFirstContactPanelShell() {\n  const home = document.getElementById(\'home\');\n  if (!home || document.getElementById(\'firstContactPanel\')) return;\n\n  const panel = document.createElement(\'article\');\n  panel.id = \'firstContactPanel\';\n  panel.className = \'card chatCard firstContactPanel\';\n  panel.innerHTML = `\n    <div class="sectionHeader">\n      <div>\n        <p class="eyebrow">Feature 003</p>\n        <h4>First Contact</h4>\n      </div>\n      <span id="firstContactBadge" class="badge">Checking</span>\n    </div>\n    <div id="firstContactDetails" class="smallList"></div>\n    <div class="firstContactSteps">\n      <div class="firstContactStep">\n        <div class="stepNumber">1</div>\n        <div><strong>Start Runtime</strong><br><span class="pathText" id="firstContactLauncher">AI\\\\Gateway\\\\FIRST_CONTACT_START_RUNTIME.bat</span></div>\n      </div>\n      <div class="firstContactStep">\n        <div class="stepNumber">2</div>\n        <div><strong>Wait for Server</strong><br><span>Leave the runtime window open once llama-server finishes loading.</span></div>\n      </div>\n      <div class="firstContactStep">\n        <div class="stepNumber">3</div>\n        <div><strong>Ask the Academy</strong><br><span>Use the chat box below when the badge turns online.</span></div>\n      </div>\n    </div>\n  `;\n\n  const chatCard = document.querySelector(\'#home .chatCard\');\n  if (chatCard) home.insertBefore(panel, chatCard);\n  else home.appendChild(panel);\n}\n\nasync function renderFirstContactPanel() {\n  renderFirstContactPanelShell();\n  const fc = await fetchFirstContactStatus();\n  const badge = document.getElementById(\'firstContactBadge\');\n  const details = document.getElementById(\'firstContactDetails\');\n  const launcher = document.getElementById(\'firstContactLauncher\');\n\n  if (!badge || !details) return;\n\n  if (!fc) {\n    badge.textContent = \'API Missing\';\n    details.innerHTML = item(\'First Contact\', \'Endpoint not available yet. Restart KayocktheOS Core.\', \'bad\');\n    return;\n  }\n\n  const online = !!fc.runtime?.online;\n  badge.textContent = online ? \'Academy Online\' : (fc.ready_for_contact ? \'Ready to Start\' : \'Needs Setup\');\n  if (launcher && fc.launcher) launcher.textContent = fc.launcher.replace(/^.*KayocktheOS[\\\\\\\\/]/, \'\');\n\n  details.innerHTML = [\n    item(\'Runtime\', fc.runtime_path || \'Not found\', fc.runtime_path ? \'ok\' : \'bad\'),\n    item(\'Model\', fc.model || \'Not selected\', fc.model ? \'ok\' : \'bad\'),\n    item(\'Server\', fc.runtime?.base || \'http://127.0.0.1:8845\', online ? \'ok\' : \'wait\'),\n    item(\'Status\', online ? \'Online — Ask the Academy now\' : \'Offline — run the First Contact runtime launcher\', online ? \'ok\' : \'wait\')\n  ].join(\'\');\n}\n'

def info(msg):
    print(f"[Feature 003C First Contact Panel] {msg}")

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
    for item in ["Bridge","manifest.yaml","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def patch_bridge():
    style = ROOT / "Bridge" / "style.css"
    renderer = ROOT / "Bridge" / "renderer.js"
    if style.exists():
        old = style.read_text(encoding="utf-8", errors="replace")
        if "Feature 003C - First Contact Bridge Panel" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 003C First Contact Bridge Panel" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderFirstContactPanel();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderFirstContactPanel();")
        renderer.write_text(old, encoding="utf-8")
    info("First Contact panel added to Home.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_003c_first_contact_bridge_panel: enabled" not in text:
        text += "\n  feature_003c_first_contact_bridge_panel: enabled\n" if "features:" in text else "\nfeatures:\n  feature_003c_first_contact_bridge_panel: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_003C_FIRST_CONTACT_BRIDGE_PANEL.md", """# Feature 003C - First Contact Bridge Panel

Adds a visible First Contact panel to the Home room.

## Shows

- Correct runtime path
- Selected model
- Runtime online/offline status
- First Contact launcher path
- Step-by-step launch flow

## Use

Restart the Bridge and look at Home.
""")
    write_text("Forge/Decisions/0031_first_contact_bridge_panel.md", """# Decision 0031 - First Contact Bridge Panel

First Contact must be visible from the Bridge.

The Operator should not have to inspect JSON endpoints to know whether the Academy is ready.
""")
    write_text("Foundry/Releases/feature003c_first_contact_bridge_panel_notes.md", "# Feature 003C - First Contact Bridge Panel\n\nAdds visible Home panel for First Contact readiness.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 003C - First Contact Bridge Panel\n\n- Added First Contact panel to Bridge Home room.\n- Shows selected model, runtime path, server status, and launch steps.\n- Makes First Contact status visible without opening raw API JSON.\n"
    if "Feature 003C - First Contact Bridge Panel" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    patch_bridge()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 003C First Contact Bridge Panel complete.")
    info("Restart Start_Bridge.bat and open Home.")

if __name__ == "__main__":
    main()
