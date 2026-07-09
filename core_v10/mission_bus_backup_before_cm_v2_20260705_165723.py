from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .foxai_core import FoxAICore


@dataclass
class MissionBus:
    """
    Central command dispatcher for FOXAI Core v10.

    Every department should eventually talk through this one doorway:
    Mission Console, Academy, Iron Library, Repair Bay, Hangar Bay,
    Creative Studio, Red Canvas, Novel Forge, and future tools.
    """

    foxai_root: Path
    core: FoxAICore = field(init=False)

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.core = FoxAICore(self.foxai_root)

    def dispatch(self, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        command = (command or "").strip().lower()

        try:
            if command == "ping":
                return {"ok": True, "message": "Mission Bus online.", "command": command}

            if command == "professors.list":
                return {"ok": True, "professors": self.core.list_professors()}

            if command == "projects.list":
                return {"ok": True, "projects": self.core.list_projects()}

            if command == "projects.create":
                name = payload.get("name", "")
                if not name:
                    return {"ok": False, "message": "Missing project name."}
                return self.core.create_project(name)

            if command == "memory.add":
                project = payload.get("project", "")
                kind = payload.get("kind", "")
                text = payload.get("text", "")
                if not project:
                    return {"ok": False, "message": "Missing project."}
                mission = self.core.mission(project=project, professor=payload.get("professor", "fox"))
                return mission.memory.add_item(kind, text)

            if command == "memory.context":
                project = payload.get("project", "")
                professor = payload.get("professor", "fox")
                model_name = payload.get("model_name")
                if not project:
                    return {"ok": False, "message": "Missing project."}
                mission = self.core.mission(project=project, professor=professor, model_name=model_name)
                return {
                    "ok": True,
                    "project": project,
                    "context": mission.memory.build_context(
                        professor_name=mission.professor.name,
                        model_name=model_name,
                    ),
                }

            if command == "mission.ask":
                project = payload.get("project", "")
                text = payload.get("text", "")
                professor = payload.get("professor", "fox")
                model_name = payload.get("model_name")
                if not project:
                    return {"ok": False, "message": "Missing project."}
                if not text:
                    return {"ok": False, "message": "Missing message text."}
                mission = self.core.mission(project=project, professor=professor, model_name=model_name)
                return mission.ask(text)

            return {"ok": False, "message": f"Unknown Mission Bus command: {command}", "command": command}

        except Exception as exc:
            return {"ok": False, "message": f"Mission Bus error: {exc}", "command": command}
