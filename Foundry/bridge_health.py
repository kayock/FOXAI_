from pathlib import Path
import json
import datetime
import re

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "Bridge"
REPORTS = ROOT / "Foundry" / "Reports"

EXPECTED_ROOMS = [
    "home",
    "academy",
    "workshop",
    "repair",
    "library",
    "observatory",
    "foundry"
]

EXPECTED_RENDER_HOOKS = [
    "renderCreativeStudioData();",
    "renderRepairBayData();",
    "renderLibraryData();",
    "renderObservatoryData();",
    "renderFoundryData();"
]

def read(path):
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

def bridge_health():
    index = read(BRIDGE / "index.html")
    renderer = read(BRIDGE / "renderer.js")
    style = read(BRIDGE / "style.css")

    checks = []

    def add(label, ok, detail):
        checks.append({"label": label, "ok": bool(ok), "detail": detail})

    add("Bridge folder", BRIDGE.exists(), str(BRIDGE))
    add("index.html", (BRIDGE / "index.html").exists(), "Bridge/index.html")
    add("renderer.js", (BRIDGE / "renderer.js").exists(), "Bridge/renderer.js")
    add("style.css", (BRIDGE / "style.css").exists(), "Bridge/style.css")
    add("package.json", (BRIDGE / "package.json").exists(), "Bridge/package.json")

    for room in EXPECTED_ROOMS:
        nav = f'data-room="{room}"' in index or f"data-room = \"{room}\"" in index or f"data-room='{room}'" in index or f"data-room = '{room}'" in index or f"data-room = {room}" in index or f"data-room=\"{room}\"" in renderer
        section = f'id="{room}"' in index or f"id='{room}'" in index or f"id = \"{room}\"" in index or f"section.id = '{room}'" in renderer or f'section.id = "{room}"' in renderer
        add(f"Room nav: {room}", nav, "navigation or dynamic nav")
        add(f"Room section: {room}", section, "static or dynamic section")

    for hook in EXPECTED_RENDER_HOOKS:
        add(f"Render hook: {hook}", hook in renderer, hook)

    duplicate_hooks = {}
    for hook in EXPECTED_RENDER_HOOKS:
        duplicate_hooks[hook] = renderer.count(hook)
    add("No excessive duplicate hooks", all(count <= 2 for count in duplicate_hooks.values()), str(duplicate_hooks))

    css_features = [
        "Feature 002D - Observatory Room",
        "Feature 002E - Foundry Room",
        "Feature 002F - Library Room",
        "Feature 002G v2 - Creative Studio Room",
        "Feature 002H - Repair Bay Room"
    ]
    for marker in css_features:
        add(f"CSS marker: {marker}", marker in style, marker)

    passed = sum(1 for c in checks if c["ok"])
    failed = len(checks) - passed
    report = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "bridge_health": "ok" if failed == 0 else "needs_review",
        "passed": passed,
        "failed": failed,
        "checks": checks
    }
    return report

def write_report():
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = bridge_health()
    (REPORTS / "bridge_health.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Bridge Health Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: {report['bridge_health']}",
        f"Passed: {report['passed']}",
        f"Failed: {report['failed']}",
        "",
        "## Checks",
        ""
    ]
    for c in report["checks"]:
        symbol = "✅" if c["ok"] else "❌"
        lines.append(f"- {symbol} **{c['label']}** — {c['detail']}")
    (REPORTS / "BRIDGE_HEALTH.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report

if __name__ == "__main__":
    report = write_report()
    print(json.dumps({"status": report["bridge_health"], "passed": report["passed"], "failed": report["failed"]}, indent=2))
