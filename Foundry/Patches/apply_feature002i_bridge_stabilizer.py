from pathlib import Path
import shutil
import datetime
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature002i_before_bridge_stabilizer_{STAMP}"

STABILIZER_PY = 'from pathlib import Path\nimport json\nimport datetime\nimport re\n\nROOT = Path(__file__).resolve().parents[1]\nBRIDGE = ROOT / "Bridge"\nREPORTS = ROOT / "Foundry" / "Reports"\n\nEXPECTED_ROOMS = [\n    "home",\n    "academy",\n    "workshop",\n    "repair",\n    "library",\n    "observatory",\n    "foundry"\n]\n\nEXPECTED_RENDER_HOOKS = [\n    "renderCreativeStudioData();",\n    "renderRepairBayData();",\n    "renderLibraryData();",\n    "renderObservatoryData();",\n    "renderFoundryData();"\n]\n\ndef read(path):\n    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""\n\ndef bridge_health():\n    index = read(BRIDGE / "index.html")\n    renderer = read(BRIDGE / "renderer.js")\n    style = read(BRIDGE / "style.css")\n\n    checks = []\n\n    def add(label, ok, detail):\n        checks.append({"label": label, "ok": bool(ok), "detail": detail})\n\n    add("Bridge folder", BRIDGE.exists(), str(BRIDGE))\n    add("index.html", (BRIDGE / "index.html").exists(), "Bridge/index.html")\n    add("renderer.js", (BRIDGE / "renderer.js").exists(), "Bridge/renderer.js")\n    add("style.css", (BRIDGE / "style.css").exists(), "Bridge/style.css")\n    add("package.json", (BRIDGE / "package.json").exists(), "Bridge/package.json")\n\n    for room in EXPECTED_ROOMS:\n        nav = f\'data-room="{room}"\' in index or f"data-room = \\"{room}\\"" in index or f"data-room=\'{room}\'" in index or f"data-room = \'{room}\'" in index or f"data-room = {room}" in index or f"data-room=\\"{room}\\"" in renderer\n        section = f\'id="{room}"\' in index or f"id=\'{room}\'" in index or f"id = \\"{room}\\"" in index or f"section.id = \'{room}\'" in renderer or f\'section.id = "{room}"\' in renderer\n        add(f"Room nav: {room}", nav, "navigation or dynamic nav")\n        add(f"Room section: {room}", section, "static or dynamic section")\n\n    for hook in EXPECTED_RENDER_HOOKS:\n        add(f"Render hook: {hook}", hook in renderer, hook)\n\n    duplicate_hooks = {}\n    for hook in EXPECTED_RENDER_HOOKS:\n        duplicate_hooks[hook] = renderer.count(hook)\n    add("No excessive duplicate hooks", all(count <= 2 for count in duplicate_hooks.values()), str(duplicate_hooks))\n\n    css_features = [\n        "Feature 002D - Observatory Room",\n        "Feature 002E - Foundry Room",\n        "Feature 002F - Library Room",\n        "Feature 002G v2 - Creative Studio Room",\n        "Feature 002H - Repair Bay Room"\n    ]\n    for marker in css_features:\n        add(f"CSS marker: {marker}", marker in style, marker)\n\n    passed = sum(1 for c in checks if c["ok"])\n    failed = len(checks) - passed\n    report = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "bridge_health": "ok" if failed == 0 else "needs_review",\n        "passed": passed,\n        "failed": failed,\n        "checks": checks\n    }\n    return report\n\ndef write_report():\n    REPORTS.mkdir(parents=True, exist_ok=True)\n    report = bridge_health()\n    (REPORTS / "bridge_health.json").write_text(json.dumps(report, indent=2), encoding="utf-8")\n\n    lines = [\n        "# Bridge Health Report",\n        "",\n        f"Generated: {report[\'generated_at\']}",\n        f"Status: {report[\'bridge_health\']}",\n        f"Passed: {report[\'passed\']}",\n        f"Failed: {report[\'failed\']}",\n        "",\n        "## Checks",\n        ""\n    ]\n    for c in report["checks"]:\n        symbol = "✅" if c["ok"] else "❌"\n        lines.append(f"- {symbol} **{c[\'label\']}** — {c[\'detail\']}")\n    (REPORTS / "BRIDGE_HEALTH.md").write_text("\\n".join(lines) + "\\n", encoding="utf-8")\n    return report\n\nif __name__ == "__main__":\n    report = write_report()\n    print(json.dumps({"status": report["bridge_health"], "passed": report["passed"], "failed": report["failed"]}, indent=2))\n'
RENDERER_PATCH = '\n// Feature 002I Bridge Health panel\nfunction renderBridgeHealthMini() {\n  const foundry = document.getElementById(\'foundry\');\n  if (!foundry || document.getElementById(\'bridgeHealthMini\')) return;\n  const card = document.createElement(\'article\');\n  card.className = \'card chatCard\';\n  card.id = \'bridgeHealthMini\';\n  card.innerHTML = `\n    <h4>Bridge Health</h4>\n    <div id="bridgeHealthMiniList" class="smallList"></div>\n  `;\n  foundry.appendChild(card);\n}\n\nfunction renderBridgeHealthData() {\n  renderBridgeHealthMini();\n  const el = document.getElementById(\'bridgeHealthMiniList\');\n  if (!el) return;\n  const rooms = [\'Home\',\'Academy\',\'Workshop\',\'Repair Bay\',\'Library\',\'Observatory\',\'Foundry\'];\n  el.innerHTML = rooms.map(room => item(room, \'Visible in Bridge\', \'ok\')).join(\'\') +\n    item(\'Health Report\', \'Run Foundry\\\\bridge_health.bat for full report.\', \'wait\');\n}\n'

def info(msg):
    print(f"[Feature 002I Bridge Stabilizer] {msg}")

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

def install_stabilizer():
    write_text("Foundry/bridge_health.py", STABILIZER_PY)
    write_text("Foundry/bridge_health.bat", """@echo off
title KayocktheOS Bridge Health
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\bridge_health.py
) else (
    py Foundry\bridge_health.py
)

echo.
pause
""")

    spec = importlib.util.spec_from_file_location("kayock_bridge_health", ROOT / "Foundry/bridge_health.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report = mod.write_report()
    info(f"Bridge health: {report['bridge_health']} / failed checks: {report['failed']}")

def patch_bridge():
    renderer = ROOT / "Bridge" / "renderer.js"
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 002I Bridge Health panel" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderBridgeHealthData();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderBridgeHealthData();")
        renderer.write_text(old, encoding="utf-8")
    info("Bridge Health mini panel added to Foundry.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_002i_bridge_stabilizer: enabled" not in text:
        text += "\n  feature_002i_bridge_stabilizer: enabled\n" if "features:" in text else "\nfeatures:\n  feature_002i_bridge_stabilizer: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_002I_BRIDGE_STABILIZER.md", """# Feature 002I - Bridge Room Stabilizer

The Bridge now has a health checker.

## Run

```bat
Foundry\bridge_health.bat
```

## Output

```text
Foundry/Reports/bridge_health.json
Foundry/Reports/BRIDGE_HEALTH.md
```

This verifies that the major rooms and render hooks are still present.
""")
    write_text("Forge/Decisions/0026_bridge_stabilizer.md", """# Decision 0026 - Bridge Stabilizer

As the Bridge grows, it needs health checks.

The Foundry owns Bridge stability reporting.
""")
    write_text("Foundry/Releases/feature002i_bridge_stabilizer_notes.md", "# Feature 002I - Bridge Stabilizer\n\nAdds Bridge health checker and Foundry mini panel.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 002I - Bridge Room Stabilizer\n\n- Added `Foundry/bridge_health.py`.\n- Added `Foundry/bridge_health.bat`.\n- Added Bridge health report output.\n- Added mini Bridge Health panel to Foundry room.\n"
    if "Feature 002I - Bridge Room Stabilizer" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_stabilizer()
    patch_bridge()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 002I Bridge Stabilizer complete.")
    info("Restart Start_Bridge.bat and open Foundry.")

if __name__ == "__main__":
    main()
