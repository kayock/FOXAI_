from pathlib import Path
import shutil
import datetime
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v0.9.0_before_git_packager_{STAMP}"

PACKAGER = 'from pathlib import Path\nimport zipfile\nimport datetime\nimport json\nimport shutil\n\nROOT = Path(__file__).resolve().parents[1]\nRELEASES = ROOT / "Foundry" / "Releases"\nREPORTS = ROOT / "Foundry" / "Reports"\n\nEXCLUDE_DIRS = {\n    ".git",\n    "node_modules",\n    "dist",\n    "out",\n    "__pycache__",\n    "Backups",\n    "System/Temp",\n}\n\nEXCLUDE_SUFFIXES = {\n    ".pyc",\n    ".log",\n}\n\nLARGE_MODEL_SUFFIXES = {\n    ".gguf",\n    ".safetensors",\n    ".ckpt",\n    ".bin",\n    ".onnx",\n    ".pt",\n    ".pth",\n}\n\ndef read_manifest():\n    text = (ROOT / "manifest.yaml").read_text(encoding="utf-8", errors="replace") if (ROOT / "manifest.yaml").exists() else ""\n    version = "unknown"\n    codename = "unknown"\n    for line in text.splitlines():\n        if line.strip().startswith("version:") and version == "unknown":\n            version = line.split(":", 1)[1].strip()\n        if line.strip().startswith("codename:") and codename == "unknown":\n            codename = line.split(":", 1)[1].strip()\n    return version, codename\n\ndef should_exclude(path):\n    rel = path.relative_to(ROOT).as_posix()\n    parts = rel.split("/")\n    for i in range(1, len(parts) + 1):\n        if "/".join(parts[:i]) in EXCLUDE_DIRS:\n            return True\n    if path.suffix.lower() in EXCLUDE_SUFFIXES:\n        return True\n    if path.suffix.lower() in LARGE_MODEL_SUFFIXES:\n        return True\n    return False\n\ndef create_release_zip():\n    RELEASES.mkdir(parents=True, exist_ok=True)\n    REPORTS.mkdir(parents=True, exist_ok=True)\n    version, codename = read_manifest()\n    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")\n    safe_codename = "".join(c if c.isalnum() else "_" for c in codename).strip("_")\n    zip_path = RELEASES / f"KayocktheOS_{version}_{safe_codename}_{stamp}.zip"\n\n    included = []\n    skipped = []\n\n    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:\n        for path in ROOT.rglob("*"):\n            if path.is_dir():\n                continue\n            if should_exclude(path):\n                skipped.append(path.relative_to(ROOT).as_posix())\n                continue\n            rel = path.relative_to(ROOT)\n            z.write(path, rel)\n            included.append(rel.as_posix())\n\n    report = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "version": version,\n        "codename": codename,\n        "zip": str(zip_path),\n        "included_files": len(included),\n        "skipped_files": len(skipped),\n        "skipped_examples": skipped[:50],\n    }\n    (REPORTS / "last_release_package.json").write_text(json.dumps(report, indent=2), encoding="utf-8")\n    print(json.dumps(report, indent=2))\n    return zip_path\n\nif __name__ == "__main__":\n    create_release_zip()\n'

def info(msg):
    print(f"[KayocktheOS v0.9.0] {msg}")

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
    for item in ["manifest.yaml","System","AI","Forge","Foundry","Docs","00_START_HERE","Shell",".gitignore"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_git_docs():
    write_text("Foundry/git_baseline.bat", """@echo off
title KayocktheOS Git Baseline
cd /d "%~dp0.."

echo ==========================================
echo KayocktheOS Git Baseline
echo ==========================================
echo.

git --version
if %errorlevel% neq 0 (
  echo Git was not found. Install Git for Windows first.
  pause
  exit /b 1
)

if not exist .git (
  git init
)

git status
echo.
echo Suggested commands:
echo git add .
echo git commit -m "v0.9.0 git baseline and release packager"
echo git tag v0.9.0
echo.
pause
""")

    write_text("Docs/GIT_BASELINE.md", """# Git Baseline

v0.9.0 formalizes Git as the project memory.

## Run

```bat
Foundry\git_baseline.bat
```

Then:

```bat
git add .
git commit -m "v0.9.0 git baseline and release packager"
git tag v0.9.0
```

## Rule

Commit working checkpoints before major experiments.
""")

def install_packager():
    write_text("Foundry/package_release.py", PACKAGER)
    write_text("Foundry/package_release.bat", """@echo off
title KayocktheOS Package Release
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\package_release.py
) else (
    py Foundry\package_release.py
)
pause
""")

def update_gitignore():
    path = ROOT / ".gitignore"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    additions = """
# KayocktheOS release/build exclusions
Backups/
System/Temp/
System/Logs/*.log
Foundry/Releases/*.zip
Foundry/Reports/last_release_package.json

# Node/Electron
node_modules/
dist/
out/

# Large AI assets
AI/Models/**/*.gguf
AI/Models/**/*.safetensors
AI/Models/**/*.ckpt
AI/Models/**/*.bin
AI/Models/**/*.onnx
AI/Models/**/*.pt
AI/Models/**/*.pth
"""
    if "KayocktheOS release/build exclusions" not in old:
        path.write_text(old.rstrip() + "\n\n" + additions.strip() + "\n", encoding="utf-8")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        text = re.sub(r"version: .*", "version: 0.9.0", text, count=1)
        text = re.sub(r"codename: .*", "codename: Git Baseline Release Packager", text, count=1)
        if "release_packager: enabled" not in text:
            text += "\n  release_packager: enabled\n" if "features:" in text else "\nfeatures:\n  release_packager: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/RELEASE_PACKAGER.md", """# Release Packager

v0.9.0 adds a Foundry release packager.

## Run

```bat
Foundry\package_release.bat
```

## Output

```text
Foundry/Releases/KayocktheOS_<version>_<codename>_<timestamp>.zip
Foundry/Reports/last_release_package.json
```

## Excludes

- `.git`
- `node_modules`
- `dist`
- `out`
- `Backups`
- logs
- temp files
- large model files
""")

    write_text("Forge/Decisions/0009_git_and_release_packager.md", """# Decision 0009 - Git and Release Packager

KayocktheOS will use Git for project history and the Foundry for release packaging.

Large model files are excluded from source releases by default.
""")

    write_text("Foundry/Releases/v0.9.0_release_notes.md", "# v0.9.0 Release Notes - Git Baseline & Release Packager\n\nAdds Git baseline helpers and Foundry release packaging.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v0.9.0 - Git Baseline & Release Packager\n\n- Added Git baseline helper.\n- Added Foundry release packager.\n- Added release packaging documentation.\n- Updated `.gitignore` for releases, temp files, logs, node_modules, and large AI assets.\n"
    if "v0.9.0 - Git Baseline" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_git_docs()
    install_packager()
    update_gitignore()
    update_manifest()
    create_docs()
    update_changelog()
    info("v0.9.0 Git Baseline & Release Packager patch complete.")
    info("Next: run Foundry\\git_baseline.bat and Foundry\\package_release.bat.")

if __name__ == "__main__":
    main()
