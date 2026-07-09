from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
MARKER = ROOT / "Config" / "last_extension_health_arbiter_backup.txt"


def main() -> None:
    print("FOXAI Restore Extension Health Arbiter")
    print("======================================")
    print()

    if not MARKER.exists():
        print("No backup marker found.")
        return

    backup_dir = Path(MARKER.read_text(encoding="utf-8").strip())
    source = backup_dir / "core_v10" / "extension_manager.py"
    target = ROOT / "core_v10" / "extension_manager.py"

    if not source.exists():
        print(f"Backup file not found: {source}")
        return

    shutil.copy2(source, target)
    print("[RESTORED] core_v10\\extension_manager.py")
    print(f"From: {source}")


if __name__ == "__main__":
    main()
