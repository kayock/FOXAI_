
from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
MARKER = ROOT / "Config" / "last_service_contracts_backup.txt"


def main() -> None:
    print("FOXAI Restore Service Contracts")
    print("===============================")
    print()

    if not MARKER.exists():
        print("No backup marker found.")
        return

    backup_dir = Path(MARKER.read_text(encoding="utf-8").strip())
    source = backup_dir / "core_v10" / "service_contracts.py"
    target = ROOT / "core_v10" / "service_contracts.py"

    if not source.exists():
        print(f"Backup file not found: {source}")
        return

    shutil.copy2(source, target)
    print("[RESTORED] core_v10\\service_contracts.py")
    print(f"From: {source}")


if __name__ == "__main__":
    main()
