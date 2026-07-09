from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature002k_before_launcher_polish_{STAMP}"

LAUNCHER_BAT = '@echo off\ntitle KayocktheOS Workshop Launcher\ncolor 0A\ncd /d "%~dp0"\n\necho ==========================================\necho        KayocktheOS Workshop Launcher\necho ==========================================\necho.\necho Opening the Workshop...\necho.\n\necho [1/4] Checking Core API...\npowershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-RestMethod http://127.0.0.1:8844/api/ping -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul\nif %errorlevel% neq 0 (\n    echo Core API is not responding.\n    echo Starting KayocktheOS Core in a new window...\n    if exist Start_KayocktheOS.bat (\n        start "KayocktheOS Core" cmd /k Start_KayocktheOS.bat\n        timeout /t 4 >nul\n    ) else (\n        echo WARNING: Start_KayocktheOS.bat was not found.\n    )\n) else (\n    echo Core API online.\n)\n\necho [2/4] Checking Bridge app...\nif not exist Bridge\\package.json (\n    echo ERROR: Bridge\\package.json was not found.\n    echo Run Feature 002 Bridge toolkit first.\n    pause\n    exit /b 1\n)\n\necho [3/4] Checking Bridge dependencies...\nif not exist Bridge\\node_modules (\n    echo Installing Bridge dependencies...\n    cd /d "%~dp0Bridge"\n    npm install\n    cd /d "%~dp0"\n)\n\necho [4/4] Launching Bridge...\ncd /d "%~dp0Bridge"\nnpm start\npause\n'
DESKTOP_NOTE = '# KayocktheOS Launcher Notes\n\nRecommended user-facing launcher:\n\n```text\nZ:\\KayocktheOS\\Launch_KayocktheOS_Workshop.bat\n```\n\nThis launcher:\n\n1. Checks whether the Core API is already online.\n2. Starts the Core if needed.\n3. Checks Bridge dependencies.\n4. Opens the Bridge.\n\nThe goal is to make KayocktheOS feel like one application instead of a set of scripts.\n'

def info(msg):
    print(f"[Feature 002K Launcher Polish] {msg}")

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
    for item in ["Launch_KayocktheOS_Workshop.bat","Start_Bridge.bat","Bridge","manifest.yaml","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_launcher():
    write_text("Launch_KayocktheOS_Workshop.bat", LAUNCHER_BAT)
    write_text("Docs/WORKSHOP_LAUNCHER.md", DESKTOP_NOTE)
    write_text("00_START_HERE/LAUNCH_THE_WORKSHOP.md", """# Launch KayocktheOS

Use:

```text
Launch_KayocktheOS_Workshop.bat
```

This is now the preferred front-door launcher for the project.
""")
    info("Workshop launcher installed.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_002k_bridge_launcher_polish: enabled" not in text:
        text += "\n  feature_002k_bridge_launcher_polish: enabled\n" if "features:" in text else "\nfeatures:\n  feature_002k_bridge_launcher_polish: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Forge/Decisions/0028_workshop_launcher.md", """# Decision 0028 - Workshop Launcher

KayocktheOS should have a single preferred front-door launcher.

The Operator should not need to remember which scripts to start first.
""")
    write_text("Foundry/Releases/feature002k_bridge_launcher_polish_notes.md", "# Feature 002K - Bridge Launcher Polish\n\nAdds single Workshop launcher helper.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 002K - Bridge Launcher Polish\n\n- Added `Launch_KayocktheOS_Workshop.bat`.\n- Launcher checks Core API and starts Core if needed.\n- Launcher installs Bridge dependencies if missing.\n- Preferred front-door entry point documented.\n"
    if "Feature 002K - Bridge Launcher Polish" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_launcher()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 002K Bridge Launcher Polish complete.")
    info("Use Launch_KayocktheOS_Workshop.bat as the main entry point.")

if __name__ == "__main__":
    main()
