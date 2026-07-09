from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CORE = ROOT / "core_v10"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP = ROOT / "Backups" / f"import_path_diagnostic_{STAMP}"

TARGETS = [
    CORE / "fleet_registry.py",
    CORE / "extension_manager.py",
    CORE / "conversation_shuttle.py",
    CORE / "brain" / "brain_router.py",
]

MARKER_BEGIN = "# FOXAI_IMPORT_DIAGNOSTIC_BEGIN"
MARKER_END = "# FOXAI_IMPORT_DIAGNOSTIC_END"


def patch_file(path: Path) -> None:
    if not path.exists():
        print(f"[SKIP] Missing: {path}")
        return

    BACKUP.mkdir(parents=True, exist_ok=True)
    rel = path.relative_to(ROOT)
    backup_path = BACKUP / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup_path)

    text = path.read_text(encoding="utf-8")

    if MARKER_BEGIN in text:
        print(f"[OK] Already patched: {rel}")
        return

    diagnostic = (
        f"\n{MARKER_BEGIN}\n"
        "try:\n"
        "    from pathlib import Path as _FOXAI_Path\n"
        "    print(f\"[FOXAI IMPORT DIAGNOSTIC] {__name__} loaded from {_FOXAI_Path(__file__).resolve()}\")\n"
        "except Exception:\n"
        "    pass\n"
        f"{MARKER_END}\n"
    )

    # Place after future imports when present.
    future_line = "from __future__ import annotations"
    if future_line in text:
        text = text.replace(future_line, future_line + diagnostic, 1)
    else:
        text = diagnostic + "\n" + text

    path.write_text(text, encoding="utf-8")
    print(f"[PATCHED] {rel}")


def main() -> None:
    print("FOXAI CM v3.5c Safe Import Path Diagnostic")
    print("==========================================")
    print()
    print(f"Backup folder: {BACKUP}")
    print()

    for target in TARGETS:
        patch_file(target)

    marker_file = ROOT / "Config" / "last_import_path_diagnostic_backup.txt"
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    marker_file.write_text(str(BACKUP), encoding="utf-8")

    print()
    print("Running service shuttle architecture test with import diagnostics...")
    print()

    test = ROOT / "TEST_SERVICE_SHUTTLE_ARCHITECTURE.py"
    if test.exists():
        subprocess.run([sys.executable, str(test)], cwd=str(ROOT))
    else:
        print("[WARN] TEST_SERVICE_SHUTTLE_ARCHITECTURE.py not found.")
        print("Run your normal test now and look for [FOXAI IMPORT DIAGNOSTIC] lines.")

    print()
    print("Diagnostic patch is still active.")
    print("Run RESTORE_IMPORT_PATH_DIAGNOSTIC.bat when done.")


if __name__ == "__main__":
    main()
