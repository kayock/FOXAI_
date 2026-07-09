from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from .bridge_officers import BridgeOfficerRegistry
from .fleet_command import FleetCommand


@dataclass
class FleetCommandBridge:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.commander = FleetCommand(self.foxai_root)
        self.officers = BridgeOfficerRegistry(self.foxai_root)

    def command(self, request: str, mode: str = "safe") -> dict[str, Any]:
        report = self.commander.command(request, mode=mode)
        officer_report = self.officers.assignment_report(report.get("plan", {}))
        report["bridge_officers"] = officer_report

        execution = report.get("execution") or {}
        mission_id = execution.get("mission_id")
        if mission_id:
            self.commander.vault.log_event(
                mission_id=mission_id,
                level="INFO",
                source="Bridge Officer Registry",
                message="Bridge officers assigned to mission.",
                data=json.dumps(officer_report, ensure_ascii=False),
            )

        return report

    def render_text(self, report: dict[str, Any]) -> str:
        base = self.commander.render_text(report)
        bridge = self.officers.render_text(report.get("bridge_officers", {}))
        return base + "\n\n" + bridge
