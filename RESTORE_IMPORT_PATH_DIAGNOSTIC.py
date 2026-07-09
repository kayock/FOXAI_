from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
MARKER = ROOT / "Config" / "last_import_path_diagnostic_backup.txt"


def main() -> None:
    print("FOXAI Restore Import Path Diagnostic")
    print("====================================")
    print()

    if not MARKER.exists():
        print("No diagnostic backup marker found.")
        return

    backup = Path(MARKER.read_text(encoding="utf-8").strip())
    if not backup.exists():
        print(f"Backup folder not found: {backup}")
        return

    restored = 0
    for source in backup.rglob("*.py"):
        rel = source.relative_to(backup)
        dest = ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        restored += 1
        print(f"[RESTORED] {rel}")

    print()
    print(f"Restored {restored} files from:")
    print(backup)
    print()
    print("FOXAI diagnostic changes removed.")


if __name__ == "__main__":
    main()
