from __future__ import annotations

from pathlib import Path

from .academy import list_professors
from .mission_engine import MissionEngine
from .project_manager import ProjectManager


class FoxAICore:
    def __init__(self, foxai_root: str | Path):
        self.foxai_root = Path(foxai_root).resolve()
        self.project_manager = ProjectManager(self.foxai_root)

    def list_professors(self) -> list[dict]:
        return list_professors()

    def list_projects(self) -> list[dict]:
        return self.project_manager.list_projects()

    def create_project(self, name: str) -> dict:
        path = self.project_manager.ensure_project(name)
        return {"ok": True, "name": path.name, "path": str(path)}

    def mission(self, project: str, professor: str = "fox", model_name: str | None = None) -> MissionEngine:
        return MissionEngine(
            foxai_root=self.foxai_root,
            project_name=project,
            professor_key=professor,
            model_name=model_name,
        )
