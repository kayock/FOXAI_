from pathlib import Path
import shutil
import datetime
import re
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v1.0.0_before_release_finalizer_{STAMP}"

FINALIZER = 'from pathlib import Path\nimport json\nimport datetime\nimport re\nimport subprocess\nimport sys\n\nROOT = Path(__file__).resolve().parents[1]\nREPORTS = ROOT / "Foundry" / "Reports"\nRELEASES = ROOT / "Foundry" / "Releases"\n\nREQUIRED_FOR_FINAL = [\n    "manifest.yaml",\n    "Start_KayocktheOS.bat",\n    "System/API/core_api.py",\n    "System/Services/service_bus.py",\n    "System/Registry/build_registry.py",\n    "AI/scan_ai_assets.py",\n    "Foundry/release_check.py",\n    "Foundry/package_release.py",\n    "Foundry/build_portable_rc.py",\n    "Shell/KayockBrowser/index.html",\n    "Shell/KayockBrowser/renderer.js",\n    "Docs",\n    "Forge/Decisions",\n]\n\ndef exists(rel):\n    return (ROOT / rel).exists()\n\ndef read_text(path):\n    return Path(path).read_text(encoding="utf-8", errors="replace") if Path(path).exists() else ""\n\ndef write_text(path, content):\n    Path(path).parent.mkdir(parents=True, exist_ok=True)\n    Path(path).write_text(content, encoding="utf-8")\n\ndef update_manifest_final():\n    path = ROOT / "manifest.yaml"\n    text = read_text(path)\n    if not text:\n        return False\n    text = re.sub(r"version: .*", "version: 1.0.0", text, count=1)\n    text = re.sub(r"codename: .*", "codename: Portable Foundation", text, count=1)\n    if "portable_foundation: enabled" not in text:\n        text += "\\n  portable_foundation: enabled\\n" if "features:" in text else "\\nfeatures:\\n  portable_foundation: enabled\\n"\n    write_text(path, text)\n    return True\n\ndef run_optional(rel):\n    path = ROOT / rel\n    if not path.exists():\n        return {"script": rel, "ok": False, "message": "missing"}\n    try:\n        result = subprocess.run([sys.executable, str(path)], cwd=ROOT, capture_output=True, text=True, timeout=300)\n        return {\n            "script": rel,\n            "ok": result.returncode == 0,\n            "returncode": result.returncode,\n            "stdout": result.stdout[-2000:],\n            "stderr": result.stderr[-2000:]\n        }\n    except Exception as exc:\n        return {"script": rel, "ok": False, "message": str(exc)}\n\ndef finalize_release():\n    missing = [rel for rel in REQUIRED_FOR_FINAL if not exists(rel)]\n    preflight_ok = not missing\n\n    report = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "version": "1.0.0",\n        "codename": "Portable Foundation",\n        "preflight_ok": preflight_ok,\n        "missing": missing,\n        "actions": []\n    }\n\n    if preflight_ok:\n        report["actions"].append({"action": "manifest_finalized", "ok": update_manifest_final()})\n        report["actions"].append(run_optional("System/Registry/build_registry.py"))\n        report["actions"].append(run_optional("AI/scan_ai_assets.py"))\n        report["actions"].append(run_optional("Foundry/release_check.py"))\n        report["actions"].append(run_optional("Foundry/package_release.py"))\n        final_ready = all(a.get("ok", False) for a in report["actions"] if "script" in a) and report["actions"][0].get("ok")\n    else:\n        final_ready = False\n\n    report["final_ready"] = final_ready\n\n    REPORTS.mkdir(parents=True, exist_ok=True)\n    RELEASES.mkdir(parents=True, exist_ok=True)\n\n    write_text(REPORTS / "final_release_report.json", json.dumps(report, indent=2))\n\n    lines = [\n        "# KayocktheOS v1.0.0 Final Release Report",\n        "",\n        f"Generated: {report[\'generated_at\']}",\n        f"Final ready: {\'YES\' if final_ready else \'NO\'}",\n        "",\n        "## Preflight",\n        ""\n    ]\n\n    if missing:\n        lines.append("Missing required items:")\n        lines += [f"- `{m}`" for m in missing]\n    else:\n        lines.append("All required foundation files are present.")\n\n    lines += ["", "## Actions", ""]\n    for action in report["actions"]:\n        label = action.get("script") or action.get("action")\n        symbol = "✅" if action.get("ok") else "❌"\n        lines.append(f"- {symbol} `{label}`")\n\n    write_text(REPORTS / "FINAL_RELEASE_REPORT.md", "\\n".join(lines) + "\\n")\n\n    release_notes = """# KayocktheOS v1.0.0 - Portable Foundation\n\n## What this release is\n\nKayocktheOS v1.0.0 establishes the portable foundation:\n\n- Core launcher\n- Local Core API\n- Browser Shell integration\n- Bridge Desktop\n- Dynamic module registry\n- Living system scanner\n- AI asset scanner\n- Service Bus\n- Foundry release checker\n- Git baseline helpers\n- Release packager\n- Portable release candidate builder\n\n## What this release is not yet\n\nThis is not the final AI Academy.\nThis is not the finished Repair Bay.\nThis is not the finished Creative Studio.\n\nIt is the foundation those systems will plug into.\n"""\n    write_text(RELEASES / "KayocktheOS_v1.0.0_FINAL_RELEASE_NOTES.md", release_notes)\n\n    print(json.dumps({"final_ready": final_ready, "missing": missing}, indent=2))\n    return report\n\nif __name__ == "__main__":\n    finalize_release()\n'

def info(msg):
    print(f"[KayocktheOS v1.0.0] {msg}")

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

def install_finalizer():
    write_text("Foundry/finalize_v1_release.py", FINALIZER)
    write_text("Foundry/finalize_v1_release.bat", """@echo off
title KayocktheOS v1.0.0 Release Finalizer
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\finalize_v1_release.py
) else (
    py Foundry\finalize_v1_release.py
)

echo.
pause
""")

def create_docs():
    write_text("Docs/RELEASE_FINALIZER.md", """# Release Finalizer

v1.0.0 adds a finalizer that promotes the project from release candidate to foundation release.

## Run

```bat
Foundry\finalize_v1_release.bat
```

## Output

```text
Foundry/Reports/final_release_report.json
Foundry/Reports/FINAL_RELEASE_REPORT.md
Foundry/Releases/KayocktheOS_v1.0.0_FINAL_RELEASE_NOTES.md
```
""")
    write_text("Forge/Decisions/0011_release_finalizer.md", """# Decision 0011 - Release Finalizer

The Foundry owns the final release promotion process.

v1.0.0 is the Portable Foundation release, not the completed Academy/Repair Bay/Creative Studio.
""")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v1.0.0 - Portable Foundation Release Finalizer\n\n- Added `Foundry/finalize_v1_release.py`.\n- Added final release readiness report.\n- Added final release notes.\n- Establishes v1.0.0 as the Portable Foundation.\n"
    if "v1.0.0 - Portable Foundation Release Finalizer" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_finalizer()
    create_docs()
    update_changelog()
    info("v1.0.0 Release Finalizer toolkit installed.")
    info("Next: run Foundry\\finalize_v1_release.bat")

if __name__ == "__main__":
    main()
