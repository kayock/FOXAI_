from __future__ import annotations

import argparse
import json
import os
import tempfile
import zipfile
from pathlib import Path


def atomic_write(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(delete=False, dir=path.parent, prefix=path.name + ".", suffix=".tmp") as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--foxai-root", default=r"Z:\FOXAI")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()
    root = Path(args.foxai_root).resolve(strict=False)
    backups = root / "System" / "EngineeringWorkshop" / "InstallBackups"
    matches = sorted(backups.rglob("before_engineering_workshop_v1_2.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        print("No V1.2 backup was found. Nothing changed.")
        return 2
    archive = matches[0]
    print(json.dumps({"backup": str(archive), "target": "core/engineer_agent.py", "approved": args.approve}, indent=2))
    if not args.approve:
        print("Preview only. Re-run with --approve to restore this exact backup.")
        return 0
    with zipfile.ZipFile(archive, "r") as bundle:
        manifest = json.loads(bundle.read("manifest.json").decode("utf-8"))
        item = manifest["entries"][0]
        atomic_write(root / item["path"], bundle.read(f"files/{item['path']}"))
    print("Engineering Workshop V1.2 rollback completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
