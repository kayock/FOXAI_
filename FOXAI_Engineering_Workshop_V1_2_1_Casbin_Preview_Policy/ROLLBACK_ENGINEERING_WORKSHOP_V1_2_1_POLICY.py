from __future__ import annotations
import argparse
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path

TARGET = Path("Config") / "engineering_airlock_policy.csv"

def write_atomic(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup_zip")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()
    root = Path(r"Z:\FOXAI")
    backup = Path(args.backup_zip)
    print(f"Target: {root / TARGET}")
    print(f"Backup: {backup}")
    if not args.approve:
        print("Preview only. Re-run with --approve.")
        return 0
    with zipfile.ZipFile(backup, "r") as archive:
        data = archive.read(str(TARGET).replace("\\", "/"))
    write_atomic(root / TARGET, data)
    print("Policy rollback completed. Restart FOXAI WebUI.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
