from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
CORE = ROOT / "core"
TARGET = CORE / "foxai_web.py"

def main():
    if not TARGET.exists():
        print("[ERROR] core\\foxai_web.py not found.")
        return 1

    backups = sorted(
        CORE.glob("foxai_web_backup_before_capability_api_*.py"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not backups:
        backups = sorted(
            CORE.glob("foxai_web_backup_*.py"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

    if not backups:
        print("[ERROR] No foxai_web backup found in core folder.")
        print("Look manually in Z:\\FOXAI\\core for a file named foxai_web_backup_*.py")
        return 1

    chosen = backups[0]
    safety = CORE / "foxai_web_broken_before_rollback.py"
    shutil.copy2(TARGET, safety)
    shutil.copy2(chosen, TARGET)

    print("[OK] Rolled back foxai_web.py")
    print(f"Restored from: {chosen.name}")
    print(f"Broken file saved as: {safety.name}")
    print()
    print("Now restart FOXAI.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
