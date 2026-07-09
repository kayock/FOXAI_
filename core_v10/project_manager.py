from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def slugify(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9 _.-]", "", name).strip().replace(" ", "_")
    return clean[:80] or "New_Project"


@dataclass
class ProjectManager:
    foxai_root: Path

    @property
    def projects_root(self) -> Path:
        path = self.foxai_root / "Projects"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def project_path(self, name: str) -> Path:
        path = (self.projects_root / slugify(name)).resolve()
        path.relative_to(self.projects_root.resolve())
        return path

    def ensure_project(self, name: str) -> Path:
        path = self.project_path(name)
        path.mkdir(parents=True, exist_ok=True)
        notes = path / "FOXAI_PROJECT_NOTES.md"
        if not notes.exists():
            notes.write_text(
                f"# {path.name}\n\nCreated: {datetime.now().isoformat(timespec='seconds')}\n\n## Notes\n\n",
                encoding="utf-8",
            )
        return path

    def list_projects(self) -> list[dict]:
        results: list[dict] = []
        for path in sorted([p for p in self.projects_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
            files = sum(1 for p in path.rglob("*") if p.is_file())
            results.append(
                {
                    "name": path.name,
                    "files": files,
                    "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="minutes"),
                    "path": str(path),
                }
            )
        return results
