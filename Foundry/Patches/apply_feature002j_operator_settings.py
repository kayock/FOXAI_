from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature002j_before_operator_settings_{STAMP}"

STYLE_APPEND = '\n/* Feature 002J - Operator Settings Room */\n.settingsGrid {\n  display: grid;\n  grid-template-columns: 1fr 1fr;\n  gap: 18px;\n}\n\n.settingField {\n  display: grid;\n  gap: 8px;\n  margin-bottom: 14px;\n}\n\n.settingField label {\n  color: var(--muted);\n  font-size: 13px;\n  text-transform: uppercase;\n  letter-spacing: .12em;\n}\n\n.settingField input, .settingField textarea {\n  background: rgba(0,0,0,.35);\n  color: var(--text);\n  border: 1px solid rgba(149,215,149,.2);\n  border-radius: 12px;\n  padding: 12px;\n  font-family: inherit;\n}\n\n.settingField textarea {\n  min-height: 90px;\n  resize: vertical;\n}\n\n.settingsNote {\n  border-left: 4px solid var(--accent);\n  background: rgba(0,255,102,.06);\n  border-radius: 12px;\n  padding: 12px;\n  color: var(--muted);\n  margin-bottom: 10px;\n}\n\n@media (max-width: 1000px) {\n  .settingsGrid { grid-template-columns: 1fr; }\n}\n'
RENDERER_PATCH = '\n// Feature 002J Operator Settings Room\nfunction ensureSettingsNav() {\n  const nav = document.querySelector(\'nav\');\n  if (!nav || document.querySelector(\'[data-room="settings"]\')) return;\n  const btn = document.createElement(\'button\');\n  btn.className = \'nav\';\n  btn.dataset.room = \'settings\';\n  btn.textContent = \'⚙ Settings\';\n  nav.appendChild(btn);\n  btn.addEventListener(\'click\', () => openRoom(\'settings\'));\n}\n\nfunction renderSettingsRoomUpgrade() {\n  ensureSettingsNav();\n  if (document.getElementById(\'settings\')) return;\n  const section = document.createElement(\'section\');\n  section.id = \'settings\';\n  section.className = \'room\';\n  section.innerHTML = `\n    <article class="card wide">\n      <div class="sectionHeader">\n        <div>\n          <p class="eyebrow">Operator Settings</p>\n          <h4>Portable Preferences</h4>\n        </div>\n        <span class="badge">USB-first</span>\n      </div>\n      <p class="roomIntro">These settings prepare the Bridge to carry the Operator\'s preferences with the USB instead of depending on a single computer.</p>\n    </article>\n\n    <div class="settingsGrid">\n      <article class="card">\n        <h4>Operator Identity</h4>\n        <div class="settingField">\n          <label for="settingsDisplayName">Display Name</label>\n          <input id="settingsDisplayName" placeholder="Operator" />\n        </div>\n        <div class="settingField">\n          <label for="settingsNickname">Preferred Nickname</label>\n          <input id="settingsNickname" placeholder="Eric" />\n        </div>\n        <div class="settingField">\n          <label for="settingsGreeting">Startup Greeting</label>\n          <textarea id="settingsGreeting"></textarea>\n        </div>\n        <button id="saveSettingsBtn" class="primaryBtn" type="button">Save Locally</button>\n      </article>\n\n      <article class="card">\n        <h4>Workshop Paths</h4>\n        <div id="settingsPaths" class="smallList"></div>\n      </article>\n    </div>\n\n    <article class="card chatCard">\n      <h4>Design Parameters</h4>\n      <div id="settingsDesignLaws" class="smallList"></div>\n    </article>\n  `;\n  document.querySelector(\'.main\').appendChild(section);\n\n  document.getElementById(\'saveSettingsBtn\')?.addEventListener(\'click\', () => {\n    const prefs = {\n      display_name: document.getElementById(\'settingsDisplayName\')?.value || \'Operator\',\n      nickname: document.getElementById(\'settingsNickname\')?.value || \'\',\n      greeting: document.getElementById(\'settingsGreeting\')?.value || \'\'\n    };\n    localStorage.setItem(\'kayock_operator_settings\', JSON.stringify(prefs));\n    notify(\'Settings\', \'Operator settings saved locally in the Bridge.\', \'ok\');\n    renderNotifications();\n    renderSettingsData();\n  });\n}\n\nfunction renderSettingsData() {\n  renderSettingsRoomUpgrade();\n  let prefs = {};\n  try { prefs = JSON.parse(localStorage.getItem(\'kayock_operator_settings\') || \'{}\'); } catch {}\n  const operator = state.status?.operator || {};\n  const academy = state.academy || {};\n\n  const display = document.getElementById(\'settingsDisplayName\');\n  const nick = document.getElementById(\'settingsNickname\');\n  const greeting = document.getElementById(\'settingsGreeting\');\n\n  if (display && !display.value) display.value = prefs.display_name || operator.display_name || \'Operator\';\n  if (nick && !nick.value) nick.value = prefs.nickname || operator.display_name || \'\';\n  if (greeting && !greeting.value) greeting.value = prefs.greeting || academy.startup_greeting || "The Academy is open. Today\'s lesson awaits.";\n\n  const paths = document.getElementById(\'settingsPaths\');\n  if (paths) {\n    paths.innerHTML = [\n      item(\'KayocktheOS Root\', \'Z:\\\\KayocktheOS\', \'ok\'),\n      item(\'FOXAI Warehouse\', state.foxai?.foxai_root || \'Z:\\\\FOXAI\', state.foxai?.exists ? \'ok\' : \'wait\'),\n      item(\'Core API\', \'http://127.0.0.1:8844\', state.status ? \'ok\' : \'bad\'),\n      item(\'Local Runtime\', state.runtime?.base || \'http://127.0.0.1:8845\', state.runtime?.online ? \'ok\' : \'wait\'),\n      item(\'Preference Storage\', \'Bridge localStorage now; USB config file later\', \'wait\')\n    ].join(\'\');\n  }\n\n  const laws = document.getElementById(\'settingsDesignLaws\');\n  if (laws) {\n    laws.innerHTML = [\n      item(\'Feature-first\', \'Build complete, integrated features—not isolated components.\', \'ok\'),\n      item(\'Capability discovery\', \'Capabilities are discovered, never hardcoded.\', \'ok\'),\n      item(\'Living Workshop\', \'The interface teaches, assists, and builds.\', \'ok\'),\n      item(\'Replaceability\', \'Every subsystem must be independently replaceable.\', \'ok\'),\n      item(\'Bridge-visible\', \'Every feature must be demonstrable from the Bridge.\', \'ok\'),\n      item(\'Operator approval\', \'No AI writes to the project without approval.\', \'ok\')\n    ].join(\'\');\n  }\n}\n'

def info(msg):
    print(f"[Feature 002J Settings] {msg}")

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
        if "Feature 002J - Operator Settings Room" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 002J Operator Settings Room" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderSettingsData();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderSettingsData();")
        renderer.write_text(old, encoding="utf-8")
    info("Operator Settings room added.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_002j_operator_settings_room: enabled" not in text:
        text += "\n  feature_002j_operator_settings_room: enabled\n" if "features:" in text else "\nfeatures:\n  feature_002j_operator_settings_room: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_002J_OPERATOR_SETTINGS_ROOM.md", """# Feature 002J - Operator Settings Room

Adds a visible Settings room to the Bridge.

## Adds

- Operator display name field
- Nickname field
- Startup greeting field
- Workshop path display
- Architecture/design parameter panel

Current save target is Bridge localStorage. Later this should write to `System/Config/operator.yaml` with Operator approval.
""")
    write_text("Forge/Decisions/0027_operator_settings_room.md", """# Decision 0027 - Operator Settings Room

Operator preferences should travel with the USB.

The Settings room starts visible preference management; file-backed config comes later.
""")
    write_text("Foundry/Releases/feature002j_operator_settings_room_notes.md", "# Feature 002J - Operator Settings Room\n\nAdds visible portable settings room.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 002J - Operator Settings Room\n\n- Added Settings room to Bridge navigation.\n- Added Operator identity and greeting fields.\n- Added Workshop path display.\n- Added design parameter panel.\n"
    if "Feature 002J - Operator Settings Room" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    patch_bridge()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 002J Operator Settings Room complete.")
    info("Restart Start_Bridge.bat and open Settings.")

if __name__ == "__main__":
    main()
