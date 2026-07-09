
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core_v10" / "service_contracts.py"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"service_contracts_repair_{STAMP}"
BACKUP_FILE = BACKUP_DIR / "core_v10" / "service_contracts.py"

PATCH = """
# ---------------------------------------------------------------------------
# CM v6.2 compatibility exports
# ---------------------------------------------------------------------------
# service_container.py expects ServiceContract and ServiceHealth.
# These compatibility models keep the Service Container importable while the
# newer service contract schema continues to evolve.

try:
    BaseModel
except NameError:
    from pydantic import BaseModel, Field
    from typing import Any


class ServiceHealth(BaseModel):
    key: str = ""
    ok: bool = True
    status: str = "ready"
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class ServiceContract(BaseModel):
    key: str
    kind: str = "service"
    provides: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    health: ServiceHealth | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


try:
    __all__
except NameError:
    __all__ = []

for _name in ["ServiceHealth", "ServiceContract"]:
    if _name not in __all__:
        __all__.append(_name)
"""


def main() -> None:
    print("FOXAI CM v6.2 Service Contract Repair Patch")
    print("===========================================")
    print()

    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}")
        raise SystemExit(1)

    BACKUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TARGET, BACKUP_FILE)

    marker = ROOT / "Config" / "last_service_contracts_backup.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(BACKUP_DIR), encoding="utf-8")

    text = TARGET.read_text(encoding="utf-8", errors="replace")

    if "CM v6.2 compatibility exports" in text:
        print("Patch appears to already be installed.")
    else:
        TARGET.write_text(text.rstrip() + "\n\n" + PATCH + "\n", encoding="utf-8")
        print("[PATCHED] core_v10\\service_contracts.py")

    print("[BACKUP]", BACKUP_FILE)
    print()

    for script in ["DEPENDENCY_ARBITER.py", "FOXKERNEL_STATUS.py"]:
        path = ROOT / script
        if path.exists():
            print("=" * 72)
            print(f"RUNNING {script}")
            print("=" * 72)
            subprocess.run([sys.executable, str(path)], cwd=str(ROOT))
            print()
        else:
            print(f"[SKIP] {script} not found.")

    print("Patch complete.")
    print("If needed, run RESTORE_SERVICE_CONTRACTS.bat.")


if __name__ == "__main__":
    main()
