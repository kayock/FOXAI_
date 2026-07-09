from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .vault import Vault


@dataclass
class DatabaseShuttle:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.vault = Vault(Path(self.foxai_root))

    def health(self) -> dict[str, Any]:
        info = self.vault.initialize()
        return {
            "ok": True,
            "key": "database",
            "callsign": "USS Database Shuttle",
            "status": "ready",
            "message": "Vault database ready.",
            "vault": info.get("vault"),
            "db": info.get("db"),
            "schema": info.get("schema"),
        }

    def log_mission_from_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        request = str(plan.get("request", ""))
        professor = str(plan.get("professor", ""))
        title = request[:80] if request else "Untitled mission"

        needs = plan.get("needs") or []
        mission_type = needs[0].get("capability", "") if needs and isinstance(needs[0], dict) else ""
        department = ""
        for step in plan.get("steps", []):
            shuttle = step.get("chosen_shuttle") or {}
            if shuttle.get("department"):
                department = shuttle["department"]
                break

        mission = self.vault.log_mission(
            title=title,
            request=request,
            professor=professor,
            mission_type=mission_type,
            department=department,
            status="planned",
        )

        mission_id = mission["mission_id"]

        for step in plan.get("steps", []):
            shuttle = step.get("chosen_shuttle") or {}
            self.vault.log_step(
                mission_id=mission_id,
                step_number=int(step.get("step", 0)),
                capability=str(step.get("capability", "")),
                shuttle_key=str(shuttle.get("key", "")),
                shuttle_callsign=str(shuttle.get("callsign", "")),
                status=str(step.get("status", "planned")),
                details=str(step.get("intent", "")),
            )

        self.vault.log_event(
            mission_id=mission_id,
            level="INFO",
            source="MissionPlanner",
            message="Mission plan logged to Vault.",
        )

        return {"ok": True, "mission_id": mission_id}
