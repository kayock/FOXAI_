from pathlib import Path
import json
import datetime

ROOT = Path(__file__).resolve().parents[2]

CHECKS = [
    {"id": "manifest", "label": "Manifest", "path": "manifest.yaml", "required": True},
    {"id": "launcher", "label": "Start Launcher", "path": "Start_KayocktheOS.bat", "required": True},
    {"id": "core_api", "label": "Core API", "path": "System/API/core_api.py", "required": True},
    {"id": "service_bus", "label": "Service Bus", "path": "System/Services/service_bus.py", "required": True},
    {"id": "module_registry", "label": "Module Registry", "path": "System/Registry/modules", "required": True},
    {"id": "registry_builder", "label": "Registry Builder", "path": "System/Registry/build_registry.py", "required": True},
    {"id": "operator_profile", "label": "Operator Profile", "path": "System/Config/operator.yaml", "required": True},
    {"id": "shell_source", "label": "Browser Shell Source", "path": "Shell/KayockBrowser", "required": True},
    {"id": "shell_index", "label": "Browser Shell index.html", "path": "Shell/KayockBrowser/index.html", "required": True},
    {"id": "shell_renderer", "label": "Browser Shell renderer.js", "path": "Shell/KayockBrowser/renderer.js", "required": True},
    {"id": "docs", "label": "Docs Folder", "path": "Docs", "required": True},
    {"id": "changelog", "label": "Changelog", "path": "00_START_HERE/CHANGELOG.md", "required": True},
    {"id": "forge_decisions", "label": "Forge Decisions", "path": "Forge/Decisions", "required": True},
    {"id": "foundry_releases", "label": "Foundry Releases", "path": "Foundry/Releases", "required": True},
    {"id": "ai_scanner", "label": "AI Asset Scanner", "path": "AI/scan_ai_assets.py", "required": False},
    {"id": "ai_inventory", "label": "AI Inventory", "path": "AI/Inventory/ai_assets.json", "required": False},
]

def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def manifest_version():
    text = read_text(ROOT / "manifest.yaml")
    version = "unknown"
    codename = "unknown"
    for line in text.splitlines():
        if line.strip().startswith("version:") and version == "unknown":
            version = line.split(":", 1)[1].strip()
        if line.strip().startswith("codename:") and codename == "unknown":
            codename = line.split(":", 1)[1].strip()
    return version, codename

def run_checks():
    results = []
    for check in CHECKS:
        path = ROOT / check["path"]
        exists = path.exists()
        status = "PASS" if exists else ("FAIL" if check["required"] else "WARN")
        results.append({
            "id": check["id"],
            "label": check["label"],
            "path": check["path"],
            "required": check["required"],
            "exists": exists,
            "status": status
        })

    version, codename = manifest_version()
    required = [r for r in results if r["required"]]
    passed_required = [r for r in required if r["status"] == "PASS"]
    failed_required = [r for r in required if r["status"] == "FAIL"]
    warnings = [r for r in results if r["status"] == "WARN"]

    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "project": "KayocktheOS",
        "version": version,
        "codename": codename,
        "ship_ready": len(failed_required) == 0,
        "summary": {
            "total_checks": len(results),
            "required_checks": len(required),
            "passed_required": len(passed_required),
            "failed_required": len(failed_required),
            "warnings": len(warnings)
        },
        "results": results
    }

def write_report():
    report = run_checks()
    out = ROOT / "Foundry" / "Reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / "release_check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = [
        "# KayocktheOS Release Check",
        "",
        f"Generated: {report['generated_at']}",
        f"Version: {report['version']}",
        f"Codename: {report['codename']}",
        f"Ship ready: {'YES' if report['ship_ready'] else 'NO'}",
        "",
        "## Summary",
        "",
        f"- Total checks: {report['summary']['total_checks']}",
        f"- Required checks: {report['summary']['required_checks']}",
        f"- Passed required: {report['summary']['passed_required']}",
        f"- Failed required: {report['summary']['failed_required']}",
        f"- Warnings: {report['summary']['warnings']}",
        "",
        "## Results",
        ""
    ]
    for r in report["results"]:
        symbol = "✅" if r["status"] == "PASS" else ("❌" if r["status"] == "FAIL" else "⚠️")
        md.append(f"- {symbol} **{r['label']}** — `{r['path']}` — {r['status']}")
    (out / "RELEASE_CHECK.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report

if __name__ == "__main__":
    report = write_report()
    print(json.dumps(report["summary"], indent=2))
    print("Ship ready:", "YES" if report["ship_ready"] else "NO")
