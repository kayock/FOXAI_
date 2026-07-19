from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .evidence import sha256_file, utc_now, write_json
from .policy import ensure_project_root, resolve_project_path


@dataclass(slots=True)
class SnapshotResult:
    snapshot_zip: Path
    manifest_path: Path
    snapshot_sha256: str
    entries: list[dict]


class SnapshotManager:
    def __init__(self, snapshot_root: str | Path):
        self.snapshot_root = Path(snapshot_root).expanduser().resolve()
        self.snapshot_root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        mission_id: str,
        project_root: str | Path,
        relative_paths: Iterable[str],
    ) -> SnapshotResult:
        root = ensure_project_root(Path(project_root))
        stamp = utc_now().replace(":", "").replace("-", "").replace(".", "")
        mission_dir = self.snapshot_root / mission_id
        mission_dir.mkdir(parents=True, exist_ok=True)
        zip_path = mission_dir / f"snapshot_{stamp}.zip"
        manifest_path = mission_dir / f"snapshot_{stamp}.manifest.json"
        entries: list[dict] = []

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in sorted(set(relative_paths)):
                target = resolve_project_path(root, relative)
                if target.exists():
                    if not target.is_file():
                        raise ValueError(f"Snapshot target is not a regular file: {relative}")
                    archive.write(target, arcname=f"files/{relative}")
                    entries.append(
                        {
                            "relative_path": relative,
                            "existed": True,
                            "size": target.stat().st_size,
                            "sha256": sha256_file(target),
                        }
                    )
                else:
                    entries.append(
                        {
                            "relative_path": relative,
                            "existed": False,
                            "size": None,
                            "sha256": None,
                        }
                    )
            archive.writestr(
                "snapshot_manifest.json",
                json.dumps(
                    {
                        "mission_id": mission_id,
                        "project_root": str(root),
                        "created_at": utc_now(),
                        "entries": entries,
                    },
                    indent=2,
                    sort_keys=True,
                ),
            )

        write_json(
            manifest_path,
            {
                "mission_id": mission_id,
                "project_root": str(root),
                "created_at": utc_now(),
                "snapshot_zip": str(zip_path),
                "snapshot_sha256": sha256_file(zip_path),
                "entries": entries,
            },
        )
        return SnapshotResult(zip_path, manifest_path, sha256_file(zip_path), entries)

    def restore(self, snapshot_zip: str | Path, project_root: str | Path) -> list[str]:
        root = ensure_project_root(Path(project_root))
        zip_path = Path(snapshot_zip).expanduser().resolve()
        restored: list[str] = []
        with zipfile.ZipFile(zip_path, "r") as archive:
            manifest = json.loads(archive.read("snapshot_manifest.json").decode("utf-8"))
            for entry in manifest["entries"]:
                relative = entry["relative_path"]
                target = resolve_project_path(root, relative)
                if entry["existed"]:
                    data = archive.read(f"files/{relative}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    temp = target.with_name(target.name + ".foxai-restore.tmp")
                    temp.write_bytes(data)
                    temp.replace(target)
                else:
                    target.unlink(missing_ok=True)
                restored.append(relative)
        return restored
