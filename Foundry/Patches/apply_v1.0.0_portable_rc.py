from pathlib import Path
import shutil
import datetime
import re

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v1.0.0_before_portable_rc_{STAMP}"

RC_BUILDER = 'from pathlib import Path\nimport subprocess\nimport datetime\nimport json\nimport sys\n\nROOT = Path(__file__).resolve().parents[1]\nREPORTS = ROOT / "Foundry" / "Reports"\nREPORTS.mkdir(parents=True, exist_ok=True)\n\ndef run_python_script(rel):\n    path = ROOT / rel\n    if not path.exists():\n        return {"script": rel, "ok": False, "message": "missing"}\n    try:\n        result = subprocess.run([sys.executable, str(path)], cwd=ROOT, capture_output=True, text=True, timeout=300)\n        return {\n            "script": rel,\n            "ok": result.returncode == 0,\n            "returncode": result.returncode,\n            "stdout": result.stdout[-4000:],\n            "stderr": result.stderr[-4000:]\n        }\n    except Exception as exc:\n        return {"script": rel, "ok": False, "message": str(exc)}\n\ndef build_release_candidate():\n    steps = [\n        "System/Registry/build_registry.py",\n        "AI/scan_ai_assets.py",\n        "Foundry/release_check.py",\n        "Foundry/package_release.py",\n    ]\n\n    results = []\n    for step in steps:\n        results.append(run_python_script(step))\n\n    ok = all(r.get("ok") for r in results)\n    report = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "name": "KayocktheOS Portable Release Candidate",\n        "ship_ready": ok,\n        "steps": results,\n    }\n\n    (REPORTS / "portable_rc_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")\n\n    lines = [\n        "# KayocktheOS Portable Release Candidate Report",\n        "",\n        f"Generated: {report[\'generated_at\']}",\n        f"Ship ready: {\'YES\' if ok else \'NO\'}",\n        "",\n        "## Steps",\n        ""\n    ]\n    for r in results:\n        symbol = "✅" if r.get("ok") else "❌"\n        lines.append(f"- {symbol} `{r.get(\'script\')}`")\n    (REPORTS / "PORTABLE_RC_REPORT.md").write_text("\\n".join(lines) + "\\n", encoding="utf-8")\n\n    print(json.dumps({"ship_ready": ok, "steps": len(results)}, indent=2))\n    return report\n\nif __name__ == "__main__":\n    build_release_candidate()\n'

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

def install_rc_builder():
    write_text("Foundry/build_portable_rc.py", RC_BUILDER)
    write_text("Foundry/build_portable_rc.bat", """@echo off
title KayocktheOS Portable Release Candidate
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\build_portable_rc.py
) else (
    py Foundry\build_portable_rc.py
)

echo.
pause
""")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        text = re.sub(r"version: .*", "version: 1.0.0-rc.1", text, count=1)
        text = re.sub(r"codename: .*", "codename: Portable Release Candidate", text, count=1)
        if "portable_release_candidate: enabled" not in text:
            text += "\n  portable_release_candidate: enabled\n" if "features:" in text else "\nfeatures:\n  portable_release_candidate: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/PORTABLE_RELEASE_CANDIDATE.md", """# Portable Release Candidate

v1.0.0-rc.1 adds a single Foundry command for preparing a portable release candidate.

## Run

```bat
Foundry\build_portable_rc.bat
```

## It runs

1. Dynamic module registry build
2. AI asset scanner
3. Foundry release check
4. Release packager

## Output

```text
Foundry/Reports/portable_rc_report.json
Foundry/Reports/PORTABLE_RC_REPORT.md
Foundry/Releases/KayocktheOS_*.zip
```
""")

    write_text("Forge/Decisions/0010_portable_release_candidate.md", """# Decision 0010 - Portable Release Candidate

KayocktheOS needs one Foundry command that prepares a release candidate.

The Foundry owns the release process.
""")

    write_text("Foundry/Releases/v1.0.0_rc1_release_notes.md", "# v1.0.0-rc.1 Release Notes - Portable Release Candidate\n\nAdds a one-command Foundry release candidate builder.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v1.0.0-rc.1 - Portable Release Candidate\n\n- Added `Foundry/build_portable_rc.py`.\n- Added one-command release candidate builder.\n- Release candidate builder runs registry, AI scan, release check, and release packager.\n"
    if "v1.0.0-rc.1 - Portable Release Candidate" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_rc_builder()
    update_manifest()
    create_docs()
    update_changelog()
    info("v1.0.0-rc.1 Portable Release Candidate toolkit installed.")
    info("Next: run Foundry\\build_portable_rc.bat")

if __name__ == "__main__":
    main()
