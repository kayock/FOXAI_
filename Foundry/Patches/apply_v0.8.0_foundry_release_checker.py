from pathlib import Path
import shutil
import datetime
import re
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v0.8.0_before_release_checker_{STAMP}"

RELEASE_CHECKER = 'from pathlib import Path\nimport json\nimport datetime\n\nROOT = Path(__file__).resolve().parents[2]\n\nCHECKS = [\n    {"id": "manifest", "label": "Manifest", "path": "manifest.yaml", "required": True},\n    {"id": "launcher", "label": "Start Launcher", "path": "Start_KayocktheOS.bat", "required": True},\n    {"id": "core_api", "label": "Core API", "path": "System/API/core_api.py", "required": True},\n    {"id": "service_bus", "label": "Service Bus", "path": "System/Services/service_bus.py", "required": True},\n    {"id": "module_registry", "label": "Module Registry", "path": "System/Registry/modules", "required": True},\n    {"id": "registry_builder", "label": "Registry Builder", "path": "System/Registry/build_registry.py", "required": True},\n    {"id": "operator_profile", "label": "Operator Profile", "path": "System/Config/operator.yaml", "required": True},\n    {"id": "shell_source", "label": "Browser Shell Source", "path": "Shell/KayockBrowser", "required": True},\n    {"id": "shell_index", "label": "Browser Shell index.html", "path": "Shell/KayockBrowser/index.html", "required": True},\n    {"id": "shell_renderer", "label": "Browser Shell renderer.js", "path": "Shell/KayockBrowser/renderer.js", "required": True},\n    {"id": "docs", "label": "Docs Folder", "path": "Docs", "required": True},\n    {"id": "changelog", "label": "Changelog", "path": "00_START_HERE/CHANGELOG.md", "required": True},\n    {"id": "forge_decisions", "label": "Forge Decisions", "path": "Forge/Decisions", "required": True},\n    {"id": "foundry_releases", "label": "Foundry Releases", "path": "Foundry/Releases", "required": True},\n    {"id": "ai_scanner", "label": "AI Asset Scanner", "path": "AI/scan_ai_assets.py", "required": False},\n    {"id": "ai_inventory", "label": "AI Inventory", "path": "AI/Inventory/ai_assets.json", "required": False},\n]\n\ndef read_text(path):\n    try:\n        return Path(path).read_text(encoding="utf-8", errors="replace")\n    except Exception:\n        return ""\n\ndef manifest_version():\n    text = read_text(ROOT / "manifest.yaml")\n    version = "unknown"\n    codename = "unknown"\n    for line in text.splitlines():\n        if line.strip().startswith("version:") and version == "unknown":\n            version = line.split(":", 1)[1].strip()\n        if line.strip().startswith("codename:") and codename == "unknown":\n            codename = line.split(":", 1)[1].strip()\n    return version, codename\n\ndef run_checks():\n    results = []\n    for check in CHECKS:\n        path = ROOT / check["path"]\n        exists = path.exists()\n        status = "PASS" if exists else ("FAIL" if check["required"] else "WARN")\n        results.append({\n            "id": check["id"],\n            "label": check["label"],\n            "path": check["path"],\n            "required": check["required"],\n            "exists": exists,\n            "status": status\n        })\n\n    version, codename = manifest_version()\n    required = [r for r in results if r["required"]]\n    passed_required = [r for r in required if r["status"] == "PASS"]\n    failed_required = [r for r in required if r["status"] == "FAIL"]\n    warnings = [r for r in results if r["status"] == "WARN"]\n\n    return {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "project": "KayocktheOS",\n        "version": version,\n        "codename": codename,\n        "ship_ready": len(failed_required) == 0,\n        "summary": {\n            "total_checks": len(results),\n            "required_checks": len(required),\n            "passed_required": len(passed_required),\n            "failed_required": len(failed_required),\n            "warnings": len(warnings)\n        },\n        "results": results\n    }\n\ndef write_report():\n    report = run_checks()\n    out = ROOT / "Foundry" / "Reports"\n    out.mkdir(parents=True, exist_ok=True)\n    (out / "release_check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")\n\n    md = [\n        "# KayocktheOS Release Check",\n        "",\n        f"Generated: {report[\'generated_at\']}",\n        f"Version: {report[\'version\']}",\n        f"Codename: {report[\'codename\']}",\n        f"Ship ready: {\'YES\' if report[\'ship_ready\'] else \'NO\'}",\n        "",\n        "## Summary",\n        "",\n        f"- Total checks: {report[\'summary\'][\'total_checks\']}",\n        f"- Required checks: {report[\'summary\'][\'required_checks\']}",\n        f"- Passed required: {report[\'summary\'][\'passed_required\']}",\n        f"- Failed required: {report[\'summary\'][\'failed_required\']}",\n        f"- Warnings: {report[\'summary\'][\'warnings\']}",\n        "",\n        "## Results",\n        ""\n    ]\n    for r in report["results"]:\n        symbol = "✅" if r["status"] == "PASS" else ("❌" if r["status"] == "FAIL" else "⚠️")\n        md.append(f"- {symbol} **{r[\'label\']}** — `{r[\'path\']}` — {r[\'status\']}")\n    (out / "RELEASE_CHECK.md").write_text("\\n".join(md) + "\\n", encoding="utf-8")\n    return report\n\nif __name__ == "__main__":\n    report = write_report()\n    print(json.dumps(report["summary"], indent=2))\n    print("Ship ready:", "YES" if report["ship_ready"] else "NO")\n'

def info(msg):
    print(f"[KayocktheOS v0.8.0] {msg}")

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

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
    for item in ["manifest.yaml","System","AI","Forge","Foundry","Docs","00_START_HERE","Shell"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_release_checker():
    write_text("Foundry/release_check.py", RELEASE_CHECKER)
    write_text("Foundry/run_release_check.bat", """@echo off
title KayocktheOS Release Check
cd /d "%~dp0.."
where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\release_check.py
) else (
    py Foundry\release_check.py
)
pause
""")
    spec = importlib.util.spec_from_file_location("kayock_release_check", ROOT / "Foundry/release_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report = mod.write_report()
    info("Release check complete: " + ("SHIP READY" if report["ship_ready"] else "NOT READY"))

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; release checker installed but API patch skipped.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")

    if "def release_check(" not in old:
        insert = """
def release_check():
    try:
        checker = ROOT / "Foundry" / "release_check.py"
        if checker.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_release_check", checker)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.write_report()
    except Exception as exc:
        return {"error": str(exc), "ship_ready": False}
    return {"ship_ready": False, "error": "release checker missing"}
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"release_check": release_check(),' not in old:
        old = old.replace('"services": service_bus(),', '"services": service_bus(),\n        "release_check": release_check(),')

    if 'elif path == "/api/release-check":' not in old:
        old = old.replace(
            'elif path == "/api/bridge":\n            self._json(bridge_payload())',
            'elif path == "/api/bridge":\n            self._json(bridge_payload())\n        elif path == "/api/release-check":\n            self._json(release_check())'
        )
        old = old.replace('"/api/bridge"]', '"/api/bridge", "/api/release-check"]')

    path.write_text(old, encoding="utf-8")
    info("Core API patched with /api/release-check support.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        text = re.sub(r"version: .*", "version: 0.8.0", text, count=1)
        text = re.sub(r"codename: .*", "codename: Foundry Release Checker", text, count=1)
        if "foundry_release_checker: enabled" not in text:
            text += "\n  foundry_release_checker: enabled\n" if "features:" in text else "\nfeatures:\n  foundry_release_checker: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FOUNDRY_RELEASE_CHECKER.md", """# Foundry Release Checker

v0.8.0 gives the Foundry a first release readiness check.

## Run manually

```bat
Foundry\run_release_check.bat
```

## API endpoint

```text
http://127.0.0.1:8844/api/release-check
```

## Output

```text
Foundry/Reports/release_check.json
Foundry/Reports/RELEASE_CHECK.md
```
""")
    write_text("Forge/Decisions/0008_foundry_release_checker.md", """# Decision 0008 - Foundry Release Checker

KayocktheOS should be able to ask whether a release is ready.

The Foundry owns release readiness checks.
""")
    write_text("Foundry/Releases/v0.8.0_release_notes.md", "# v0.8.0 Release Notes - Foundry Release Checker\n\nAdds release readiness reports and `/api/release-check`.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v0.8.0 - Foundry Release Checker\n\n- Added `Foundry/release_check.py`.\n- Added release readiness reports.\n- Added `/api/release-check`.\n- The Foundry can now answer whether a build is ship-ready.\n"
    if "v0.8.0 - Foundry Release Checker" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_release_checker()
    patch_core_api()
    update_manifest()
    create_docs()
    update_changelog()
    info("v0.8.0 Foundry Release Checker patch complete.")
    info("Restart KayocktheOS and test /api/release-check.")

if __name__ == "__main__":
    main()
