from pathlib import Path
import shutil
import datetime
import subprocess

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v0.3.0_before_unification_{STAMP}"

def info(msg):
    print(f"[KayocktheOS v0.3.0] {msg}")

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def copy_item(src_rel, dst_root):
    src = ROOT / src_rel
    if not src.exists():
        return
    dst = dst_root / src_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)

def append_once(rel, marker, content):
    path = ROOT / rel
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if marker not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + "\n\n" + content.strip() + "\n", encoding="utf-8")

def backup_project():
    info("Creating safety backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for item in ["manifest.yaml","Start_KayocktheOS.bat","System","Shell","Interface","00_START_HERE","Forge","Foundry","README.md"]:
        copy_item(item, BACKUP_DIR)
    info(f"Backup created: {BACKUP_DIR}")

def ensure_gitignore():
    write_text(".gitignore", """# KayocktheOS generated files
System/Logs/*.log
System/Temp/*
Backups/*
Foundry/Builds/*
Foundry/Releases/*.zip

# Python
*.pyc
__pycache__/

# Node / Electron
node_modules/
dist/
out/
*.asar

# Large AI models
AI/Models/**/*.gguf
AI/Models/**/*.safetensors
AI/Models/**/*.bin
AI/Models/**/*.ckpt
AI/Models/**/*.onnx

# OS/editor junk
.DS_Store
Thumbs.db
.vscode/.history/
""")

def create_docs():
    write_text("Docs/PROJECT_STRUCTURE.md", """# KayocktheOS Project Structure

## Core Principle

KayocktheOS is one integrated project.

The **Core** manages logic, configuration, registry, logs, API, and startup.
The **Shell** is Kayock Browser, the Operator-facing desktop environment.

## Primary Departments

- `System/` — Core launcher, API, configs, logs, registry
- `Shell/KayockBrowser/` — Browser Shell source code
- `Academy/` — Professors, colleges, lessons
- `Knowledge/` — Iron Library documents and references
- `RepairBay/` — Read-only diagnostics and future repairs
- `CreativeStudio/` — Images, video, audio, comics
- `AI/` — Engines, models, and model references
- `Forge/` — Charters, decisions, journal, milestones
- `Foundry/` — Build, patch, packaging, release tooling
- `Backups/` — Local safety backups
""")

    write_text("Docs/DEVELOPMENT_RULES.md", """# Development Rules

1. Back up before structural changes.
2. Prefer patch scripts over indentation-sensitive manual edits.
3. Every feature needs a department, owner, purpose, and documentation.
4. The Operator owns the experience.
5. Runtime personalization belongs in configuration.
6. Core and Shell remain separate.
7. Read-only diagnostics come before repair actions.
8. Large models should be referenced, not duplicated, until chosen as permanent.
9. Every milestone updates docs, changelog, and Forge records.
10. Commit working checkpoints.
""")

    write_text("Docs/GIT_START.md", """# Git Start Guide

Open Command Prompt in:

```text
Z:\\KayocktheOS
```

Then run:

```bat
git init
git add .
git commit -m "v0.3.0 project unification baseline"
```

If Git is not installed, install Git for Windows later and run these commands then.
""")

def update_manifest():
    manifest = ROOT / "manifest.yaml"
    if manifest.exists():
        text = manifest.read_text(encoding="utf-8", errors="replace")
        for old in ["version: 0.1.2","version: 0.1.1","version: 0.1.0"]:
            text = text.replace(old, "version: 0.3.0")
        for old in ["codename: Dashboard Live View","codename: Local Core API","codename: Living Bridge Shell"]:
            text = text.replace(old, "codename: Project Unification")
        if "project_unification: enabled" not in text:
            text += "\n  project_unification: enabled\n" if "features:" in text else "\nfeatures:\n  project_unification: enabled\n"
        manifest.write_text(text, encoding="utf-8")
    else:
        write_text("manifest.yaml", """project:
  name: KayocktheOS
  version: 0.3.0
  codename: Project Unification
  build: development
  usb_mode: true

core:
  launcher: System/Launchers/launch.py
  api_server: System/API/core_api.py
  api_url: http://127.0.0.1:8844

shell:
  name: Kayock Browser
  source: Shell/KayockBrowser
  role: Primary Operator-facing shell

features:
  project_unification: enabled
""")

def create_records():
    write_text("Forge/Decisions/0003_no_manual_large_edits.md", """# Decision 0003 - No Large Manual Edits

## Decision

KayocktheOS will avoid large indentation-sensitive manual edits.

## Reason

Manual placement errors are one of the easiest ways to break JavaScript, Python, and Electron projects.

## Standard

For significant changes, use one of:

- patch scripts
- complete replacement files
- small clearly-labeled edits
- Git commits with rollback
""")

    append_once("Forge/Milestones/milestones.md", "v0.3.0 Project Unification", """
- [x] v0.3.0 Project Unification
  - [x] Backup-first patch workflow
  - [x] Git prep
  - [x] Unified documentation
  - [x] No-large-manual-edits rule
""")

    append_once("00_START_HERE/CHANGELOG.md", "v0.3.0 - Project Unification", """
## v0.3.0 - Project Unification

- Added backup-first patch workflow.
- Added Git prep documentation.
- Added unified project structure documentation.
- Added no-large-manual-edits engineering rule.
- Preserved Core/Shell architecture.
""")

def create_backup_script():
    write_text("Foundry/BackupScripts/backup_project.py", 'from pathlib import Path\nimport shutil\nimport datetime\n\nROOT = Path(__file__).resolve().parents[2]\nstamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")\ntarget = ROOT / "Backups" / f"kayocktheos_backup_{stamp}"\ntarget.mkdir(parents=True, exist_ok=True)\n\nitems = ["manifest.yaml", "Start_KayocktheOS.bat", "System", "Shell", "Interface", "Academy", "Knowledge", "RepairBay", "CreativeStudio", "AI", "Forge", "Foundry", "Docs", "README.md"]\n\nfor item in items:\n    src = ROOT / item\n    dst = target / item\n    if not src.exists():\n        continue\n    if src.is_dir():\n        shutil.copytree(src, dst, dirs_exist_ok=True)\n    else:\n        dst.parent.mkdir(parents=True, exist_ok=True)\n        shutil.copy2(src, dst)\n\nprint(f"Backup complete: {target}")\n')
    write_text("Foundry/BackupScripts/backup_project.bat", """@echo off
title KayocktheOS Backup
cd /d "%~dp0..\.."
where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\BackupScripts\backup_project.py
) else (
    py Foundry\BackupScripts\backup_project.py
)
pause
""")

def maybe_init_git():
    if (ROOT / ".git").exists():
        info("Git repository already exists.")
        return
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "init"], cwd=ROOT, check=True)
        info("Git repository initialized.")
    except Exception:
        info("Git not available yet. See Docs/GIT_START.md.")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    ensure_gitignore()
    create_docs()
    update_manifest()
    create_records()
    create_backup_script()
    maybe_init_git()
    info("v0.3.0 Project Unification patch complete.")
    info("Next: test Start_KayocktheOS.bat, then commit the baseline.")

if __name__ == "__main__":
    main()
