from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature002h_before_repair_bay_{STAMP}"

STYLE_APPEND = '\n/* Feature 002H - Repair Bay Room */\n.repairHero { margin-bottom: 18px; }\n\n.repairGrid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));\n  gap: 14px;\n}\n\n.repairCard {\n  background: rgba(0,0,0,.22);\n  border: 1px solid rgba(149,215,149,.14);\n  border-radius: 16px;\n  padding: 16px;\n}\n\n.repairCard h5 {\n  color: var(--accent);\n  margin: 8px 0;\n  font-size: 18px;\n}\n\n.repairCard p {\n  color: var(--muted);\n  margin: 0;\n}\n\n.repairScore {\n  font-size: 32px;\n  font-weight: 900;\n  color: var(--accent);\n}\n\n.ruleBox {\n  border-left: 4px solid var(--warn);\n  background: rgba(255,209,102,.06);\n  border-radius: 12px;\n  padding: 12px;\n  color: var(--muted);\n  margin-bottom: 10px;\n}\n'
RENDERER_PATCH = '\n// Feature 002H Repair Bay room\nfunction ensureRepairBayNav() {\n  const nav = document.querySelector(\'nav\');\n  if (!nav || document.querySelector(\'[data-room="repair"]\')) return;\n  const btn = document.createElement(\'button\');\n  btn.className = \'nav\';\n  btn.dataset.room = \'repair\';\n  btn.textContent = \'🛠 Repair Bay\';\n  nav.insertBefore(btn, document.querySelector(\'[data-room="library"]\'));\n  btn.addEventListener(\'click\', () => openRoom(\'repair\'));\n}\n\nfunction renderRepairBayUpgrade() {\n  ensureRepairBayNav();\n  if (document.getElementById(\'repair\')) return;\n  const section = document.createElement(\'section\');\n  section.id = \'repair\';\n  section.className = \'room\';\n  section.innerHTML = `\n    <article class="card wide repairHero">\n      <div class="sectionHeader">\n        <div>\n          <p class="eyebrow">Repair Bay</p>\n          <h4>Read-Only Diagnostics & Machine Awareness</h4>\n        </div>\n        <span id="repairStatus" class="badge">Scanning</span>\n      </div>\n      <p class="roomIntro">Repair Bay starts safe: observe first, report clearly, and require Operator approval before any future action.</p>\n    </article>\n\n    <div class="roomSplit">\n      <div>\n        <article class="card">\n          <h4>Host Health</h4>\n          <div id="repairHealthCards" class="repairGrid"></div>\n        </article>\n\n        <article class="card chatCard">\n          <h4>Read-Only Scan Rules</h4>\n          <div id="repairRules"></div>\n        </article>\n      </div>\n\n      <div>\n        <article class="card">\n          <h4>Repair Readiness</h4>\n          <div id="repairReadiness" class="smallList"></div>\n        </article>\n\n        <article class="card chatCard">\n          <h4>Recommended Next Scans</h4>\n          <div id="repairRecommendations" class="smallList"></div>\n        </article>\n      </div>\n    </div>\n  `;\n  document.querySelector(\'.main\').appendChild(section);\n}\n\nfunction renderRepairBayData() {\n  renderRepairBayUpgrade();\n\n  const sys = state.status?.system || {};\n  const cpu = sys.cpu || {};\n  const mem = sys.memory || {};\n  const disk = sys.disk || {};\n  const gpu = sys.gpu || {};\n  const tools = sys.tools || {};\n  const apiOk = !!state.status;\n  const diskOk = !disk.free_gb || disk.free_gb > 50;\n  const memOk = !mem.total_gb || mem.total_gb >= 8;\n  const score = [apiOk, diskOk, memOk, tools.python?.installed].filter(Boolean).length;\n  const pct = Math.round((score / 4) * 100);\n\n  const status = document.getElementById(\'repairStatus\');\n  if (status) status.textContent = pct >= 75 ? \'Ready\' : \'Needs Review\';\n\n  const cards = document.getElementById(\'repairHealthCards\');\n  if (cards) {\n    cards.innerHTML = [\n      repairCard(\'🧠\', \'CPU\', cpu.cores_logical ? `${cpu.cores_logical} threads` : \'Unknown\', cpu.name || \'No CPU name detected\'),\n      repairCard(\'💾\', \'Memory\', mem.total_gb ? `${mem.total_gb} GB` : \'Unknown\', memOk ? \'Looks usable for diagnostics\' : \'May be limited\'),\n      repairCard(\'🗄\', \'Storage\', disk.free_gb ? `${disk.free_gb} GB free` : \'Unknown\', diskOk ? \'Enough free space for reports\' : \'Low free space warning\'),\n      repairCard(\'🎮\', \'GPU\', (gpu.gpus || []).length ? `${gpu.gpus.length} detected` : \'Unknown\', (gpu.gpus || []).join(\' · \') || \'No GPU names detected\'),\n      repairCard(\'🐍\', \'Python\', tools.python?.version || \'Unknown\', tools.python?.path || \'Python powers the Core\'),\n      repairCard(\'🌐\', \'Node\', tools.node?.installed ? \'Installed\' : \'Missing\', tools.node?.version || \'Needed for Bridge development\')\n    ].join(\'\');\n  }\n\n  const rules = document.getElementById(\'repairRules\');\n  if (rules) {\n    rules.innerHTML = [\n      \'<div class="ruleBox"><strong>Rule 1:</strong> Repair Bay observes before it acts.</div>\',\n      \'<div class="ruleBox"><strong>Rule 2:</strong> No registry, driver, disk, or system change without Operator approval.</div>\',\n      \'<div class="ruleBox"><strong>Rule 3:</strong> First deliverable is always a readable report.</div>\',\n      \'<div class="ruleBox"><strong>Rule 4:</strong> Prefer reversible fixes and backups.</div>\'\n    ].join(\'\');\n  }\n\n  const ready = document.getElementById(\'repairReadiness\');\n  if (ready) {\n    ready.innerHTML = [\n      item(\'Repair Score\', `${pct}%`, pct >= 75 ? \'ok\' : \'wait\'),\n      item(\'Core Scanner\', apiOk ? \'Online\' : \'Offline\', apiOk ? \'ok\' : \'bad\'),\n      item(\'Read-Only Mode\', \'Enabled\', \'ok\'),\n      item(\'Report Writer\', \'Planned next\', \'wait\'),\n      item(\'Driver Scan\', \'Planned\', \'wait\'),\n      item(\'SMART Disk Scan\', \'Planned\', \'wait\')\n    ].join(\'\');\n  }\n\n  const recs = document.getElementById(\'repairRecommendations\');\n  if (recs) {\n    const rows = [];\n    rows.push(item(\'Machine Summary Report\', \'Generate a clean report from current Observatory data.\', \'ok\'));\n    rows.push(item(\'Disk Health\', \'Add SMART/status checks where tools are available.\', \'wait\'));\n    rows.push(item(\'Network Diagnostics\', \'Add ping/DNS/gateway checks.\', \'wait\'));\n    rows.push(item(\'Windows Health\', \'Add read-only system information and update status.\', \'wait\'));\n    if (!tools.git?.installed) rows.push(item(\'Git Missing\', \'Project rollback is weaker without Git.\', \'wait\'));\n    if (!tools.node?.installed) rows.push(item(\'Node Missing\', \'Bridge development may need Node available.\', \'wait\'));\n    recs.innerHTML = rows.join(\'\');\n  }\n}\n\nfunction repairCard(icon, title, value, sub) {\n  return `\n    <div class="repairCard">\n      <div class="shelfIcon">${icon}</div>\n      <h5>${escapeHtml(title)}</h5>\n      <div class="repairScore">${escapeHtml(value)}</div>\n      <p>${escapeHtml(sub)}</p>\n    </div>\n  `;\n}\n'

def info(msg):
    print(f"[Feature 002H Repair Bay] {msg}")

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
        if "Feature 002H - Repair Bay Room" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 002H Repair Bay room" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderRepairBayData();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderRepairBayData();")
        renderer.write_text(old, encoding="utf-8")
    info("Repair Bay room added to Bridge.")

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_002h_repair_bay_room: enabled" not in text:
        text += "\n  feature_002h_repair_bay_room: enabled\n" if "features:" in text else "\nfeatures:\n  feature_002h_repair_bay_room: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_002H_REPAIR_BAY_ROOM.md", """# Feature 002H - Repair Bay Room

Repair Bay is now visible in the Bridge.

## Adds

- Repair Bay navigation room
- Host health cards
- Read-only repair rules
- Repair readiness panel
- Recommended next scans

## Safety

Repair Bay is read-only first. No fixes run automatically.
""")
    write_text("Forge/Decisions/0025_repair_bay_room.md", """# Decision 0025 - Repair Bay Room

Repair Bay observes first, reports clearly, and only acts with Operator approval.

The first deliverable is always a readable diagnostic report.
""")
    write_text("Foundry/Releases/feature002h_repair_bay_room_notes.md", "# Feature 002H - Repair Bay Room\n\nAdds visible Repair Bay diagnostics room.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 002H - Repair Bay Room\n\n- Added Repair Bay room to Bridge navigation.\n- Added host health and readiness cards.\n- Added read-only diagnostic safety rules.\n- Added recommended next scan list.\n"
    if "Feature 002H - Repair Bay Room" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    patch_bridge()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 002H Repair Bay Room complete.")
    info("Restart Start_Bridge.bat and open Repair Bay.")

if __name__ == "__main__":
    main()
