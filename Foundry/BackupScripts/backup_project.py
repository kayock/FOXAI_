from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
target = ROOT / "Backups" / f"kayocktheos_backup_{stamp}"
target.mkdir(parents=True, exist_ok=True)

items = ["manifest.yaml", "Start_KayocktheOS.bat", "System", "Shell", "Interface", "Academy", "Knowledge", "RepairBay", "CreativeStudio", "AI", "Forge", "Foundry", "Docs", "README.md"]

for item in items:
    src = ROOT / item
    dst = target / item
    if not src.exists():
        continue
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

print(f"Backup complete: {target}")
