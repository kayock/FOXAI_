from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature002e_before_foundry_room_{STAMP}"

STYLE_APPEND = '\n/* Feature 002E - Foundry Room */\n.foundryHero {\n  margin-bottom: 18px;\n}\n\n.lawGrid {\n  display: grid;\n  gap: 14px;\n}\n\n.lawCard {\n  background: rgba(0,0,0,.24);\n  border: 1px solid rgba(0,255,102,.18);\n  border-radius: 16px;\n  padding: 16px;\n}\n\n.lawCard h5 {\n  color: var(--accent);\n  margin: 0 0 8px;\n  font-size: 17px;\n}\n\n.lawCard p {\n  color: var(--muted);\n  margin: 0;\n}\n\n.releaseGauge {\n  border: 1px solid rgba(149,215,149,.14);\n  background: rgba(0,0,0,.22);\n  border-radius: 16px;\n  padding: 16px;\n  margin-bottom: 12px;\n}\n\n.gaugeTop {\n  display: flex;\n  justify-content: space-between;\n  color: var(--muted);\n  margin-bottom: 8px;\n}\n\n.gaugeBar {\n  height: 12px;\n  background: rgba(255,255,255,.08);\n  border-radius: 999px;\n  overflow: hidden;\n}\n\n.gaugeBar span {\n  display: block;\n  height: 100%;\n  background: var(--accent);\n  box-shadow: 0 0 18px rgba(0,255,102,.35);\n}\n\n.patchTimeline {\n  display: grid;\n  gap: 10px;\n}\n\n.timelineItem {\n  display: grid;\n  grid-template-columns: 110px 1fr;\n  gap: 12px;\n  padding: 12px;\n  background: rgba(0,0,0,.2);\n  border-radius: 14px;\n  border-left: 4px solid var(--accent);\n}\n\n.timelineItem .time {\n  color: var(--warn);\n  font-weight: 900;\n}\n\n.timelineItem .desc {\n  color: var(--muted);\n}\n'
RENDERER_PATCH = '\n// Feature 002E Foundry room upgrade\nfunction renderFoundryUpgrade() {\n  const foundry = document.getElementById(\'foundry\');\n  if (!foundry || foundry.dataset.upgraded === \'true\') return;\n  foundry.dataset.upgraded = \'true\';\n  foundry.innerHTML = `\n    <article class="card wide foundryHero">\n      <div class="sectionHeader">\n        <div>\n          <p class="eyebrow">Foundry</p>\n          <h4>Build, Release, Improve</h4>\n        </div>\n        <span id="foundryStatus" class="badge">Checking</span>\n      </div>\n      <p class="roomIntro">The Foundry is where KayocktheOS becomes stronger: release checks, architecture laws, patch history, and next-build guidance.</p>\n    </article>\n\n    <div class="roomSplit">\n      <div>\n        <article class="card">\n          <h4>Release Readiness</h4>\n          <div id="foundryReleaseGauge"></div>\n          <div id="foundryReleaseDetails" class="smallList"></div>\n        </article>\n\n        <article class="card chatCard">\n          <h4>Architecture Laws</h4>\n          <div id="architectureLaws" class="lawGrid"></div>\n        </article>\n      </div>\n\n      <div>\n        <article class="card">\n          <h4>Workshop Wall</h4>\n          <div id="foundryWorkshopWall" class="smallList"></div>\n        </article>\n\n        <article class="card chatCard">\n          <h4>Next Build Guidance</h4>\n          <div id="nextBuildGuidance" class="smallList"></div>\n        </article>\n      </div>\n    </div>\n\n    <article class="card chatCard">\n      <h4>Recent Build Timeline</h4>\n      <div id="buildTimeline" class="patchTimeline"></div>\n    </article>\n  `;\n}\n\nfunction renderFoundryData() {\n  renderFoundryUpgrade();\n\n  const release = state.release || {};\n  const summary = release.summary || {};\n  const total = summary.total_checks || summary.required_checks || 1;\n  const passed = summary.passed_required || 0;\n  const failed = summary.failed_required || 0;\n  const percent = Math.max(0, Math.min(100, Math.round((passed / Math.max(1, summary.required_checks || total)) * 100)));\n  const shipReady = !!release.ship_ready;\n\n  const status = document.getElementById(\'foundryStatus\');\n  if (status) status.textContent = shipReady ? \'Ship Ready\' : \'In Progress\';\n\n  const gauge = document.getElementById(\'foundryReleaseGauge\');\n  if (gauge) {\n    gauge.innerHTML = `\n      <div class="releaseGauge">\n        <div class="gaugeTop"><span>Foundation Readiness</span><strong>${percent}%</strong></div>\n        <div class="gaugeBar"><span style="width:${percent}%"></span></div>\n      </div>\n    `;\n  }\n\n  const details = document.getElementById(\'foundryReleaseDetails\');\n  if (details) {\n    details.innerHTML = [\n      item(\'Ship Ready\', shipReady ? \'YES\' : \'NO / Unknown\', shipReady ? \'ok\' : \'wait\'),\n      item(\'Required Passed\', `${passed}/${summary.required_checks ?? \'?\'}`, failed ? \'wait\' : \'ok\'),\n      item(\'Warnings\', `${summary.warnings ?? 0}`, (summary.warnings ?? 0) ? \'wait\' : \'ok\'),\n      item(\'Version\', release.version || state.status?.project?.version || \'Unknown\', \'ok\')\n    ].join(\'\');\n  }\n\n  const laws = [\n    [\'Architecture Law #1\', \'Build complete, integrated features—not isolated components.\'],\n    [\'Architecture Law #2\', \'Capabilities are discovered, never hardcoded.\'],\n    [\'Architecture Law #3\', \'The interface teaches, assists, and builds.\'],\n    [\'Replaceability Principle\', \'Every subsystem must be independently replaceable.\'],\n    [\'Bridge Principle\', \'Every feature must be demonstrable from the Bridge.\']\n  ];\n\n  const lawsEl = document.getElementById(\'architectureLaws\');\n  if (lawsEl) {\n    lawsEl.innerHTML = laws.map(([title, text]) => `\n      <div class="lawCard"><h5>${escapeHtml(title)}</h5><p>${escapeHtml(text)}</p></div>\n    `).join(\'\');\n  }\n\n  const wall = document.getElementById(\'foundryWorkshopWall\');\n  if (wall) {\n    wall.innerHTML = [\n      item(\'Feature 001\', \'Local Chat foundation installed.\', \'ok\'),\n      item(\'Feature 001B\', \'Runtime launch helper installed.\', \'ok\'),\n      item(\'Feature 002\', \'Bridge application created.\', \'ok\'),\n      item(\'Feature 002B\', \'Living Bridge polish added.\', \'ok\'),\n      item(\'Feature 002C\', \'Professor Studies added.\', \'ok\'),\n      item(\'Feature 002D\', \'Observatory Room added.\', \'ok\'),\n      item(\'Feature 002E\', \'Foundry Room active.\', \'ok\')\n    ].join(\'\');\n  }\n\n  const fox = state.foxai?.summary || {};\n  const runtimeOnline = !!state.runtime?.online;\n  const guidance = [];\n  if (!runtimeOnline) guidance.push([\'First Contact\', \'Launch the selected local runtime and test Ask the Academy.\', \'wait\']);\n  if ((fox.image_models || 0) > 0) guidance.push([\'Creative Studio\', \'ComfyUI assets are present. Build image generation room next.\', \'ok\']);\n  guidance.push([\'Iron Library\', \'Build indexing and document search as a complete room.\', \'wait\']);\n  guidance.push([\'Repair Bay\', \'Turn Observatory data into a machine scan report.\', \'wait\']);\n\n  const guidanceEl = document.getElementById(\'nextBuildGuidance\');\n  if (guidanceEl) {\n    guidanceEl.innerHTML = guidance.map(([label, text, status]) => item(label, text, status)).join(\'\');\n  }\n\n  const timeline = document.getElementById(\'buildTimeline\');\n  if (timeline) {\n    const entries = [\n      [\'Now\', \'Foundry room added to the Bridge.\'],\n      [\'Recent\', \'Observatory gained host-machine awareness.\'],\n      [\'Recent\', \'Academy gained professor studies.\'],\n      [\'Recent\', \'Bridge gained capability cards and Workshop Bell.\'],\n      [\'Recent\', \'Runtime launcher connected Feature 001 to real local model startup.\'],\n      [\'Foundation\', \'FOXAI Discovery, Service Bus, Academy Seed, AI Gateway, and Release Checker established.\']\n    ];\n    timeline.innerHTML = entries.map(([time, desc]) => `\n      <div class="timelineItem"><div class="time">${escapeHtml(time)}</div><div class="desc">${escapeHtml(desc)}</div></div>\n    `).join(\'\');\n  }\n}\n'

def info(msg):
    print(f"[Feature 002E Foundry] {msg}")

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
        if "Feature 002E - Foundry Room" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 002E Foundry room upgrade" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderFoundryData();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderFoundryData();")
        renderer.write_text(old, encoding="utf-8")
    info("Foundry room upgraded.")

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_002e_foundry_room: enabled" not in text:
        text += "\n  feature_002e_foundry_room: enabled\n" if "features:" in text else "\nfeatures:\n  feature_002e_foundry_room: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_002E_FOUNDRY_ROOM.md", """# Feature 002E - Foundry Room

The Foundry room now shows release readiness, architecture laws, Workshop Wall progress, and next-build guidance.

## Run

```bat
Start_Bridge.bat
```

Open the Foundry room.
""")
    write_text("Forge/Decisions/0022_foundry_room.md", """# Decision 0022 - Foundry Room

The Foundry is where KayocktheOS evolves.

It should make progress, readiness, and next steps visible to the Operator.
""")
    write_text("Foundry/Releases/feature002e_foundry_room_notes.md", "# Feature 002E - Foundry Room\n\nAdds release readiness, laws, and build guidance.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 002E - Foundry Room\n\n- Added Foundry room release readiness gauge.\n- Added Architecture Laws panel.\n- Added Workshop Wall and next-build guidance.\n- Added recent build timeline.\n"
    if "Feature 002E - Foundry Room" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    patch_bridge()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 002E Foundry Room complete.")
    info("Restart Start_Bridge.bat and open Foundry.")

if __name__ == "__main__":
    main()
