from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import time

from .capability_gap_analyzer import CapabilityGapAnalyzer
from .fleet_registry import FleetRegistry
from .mission_executor import MissionExecutor
from .mission_planner import MissionPlanner
from .vault import Vault


@dataclass
class FleetCommand:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.planner = MissionPlanner(self.foxai_root)
        self.gap = CapabilityGapAnalyzer(self.foxai_root)
        self.fleet = FleetRegistry(self.foxai_root)
        self.executor = MissionExecutor(self.foxai_root)
        self.vault = Vault(self.foxai_root)
        self.vault.initialize()

    def _fleet_snapshot(self) -> dict[str, Any]:
        data = self.fleet.refresh()
        summary = self.fleet.summary(data)
        return {
            "total": summary.get("total", 0),
            "states": summary.get("states", {}),
            "kinds": summary.get("kinds", {}),
            "updated": summary.get("updated"),
        }

    def _command_decision(self, plan: dict[str, Any], gap_report: dict[str, Any]) -> dict[str, Any]:
        missing = gap_report.get("missing_count", 0)
        mission_type = str(plan.get("mission_type", "")).lower()

        if missing:
            decision = "hold"
            reason = "Mission has missing required capabilities."
        elif mission_type in ("general conversation", "engineering investigation", "creative writing"):
            decision = "execute_safe"
            reason = "Mission is eligible for safe-mode execution."
        else:
            decision = "plan_only"
            reason = "Mission type not yet authorized for execution by Fleet Command."

        assignments = []
        for gap in gap_report.get("gaps", []):
            assignments.append({
                "capability": gap.get("capability"),
                "available": gap.get("available"),
                "assigned_key": gap.get("assigned_key"),
                "assigned_shuttle": gap.get("assigned_shuttle"),
                "department": gap.get("department"),
                "status": "assigned" if gap.get("available") else "missing",
            })

        return {
            "decision": decision,
            "reason": reason,
            "assignments": assignments,
        }

    def command(self, request: str, mode: str = "safe") -> dict[str, Any]:
        started = time.perf_counter()

        plan = self.planner.create_plan(request)
        gap_report = self.gap.analyze_plan(plan)
        fleet_snapshot = self._fleet_snapshot()
        decision = self._command_decision(plan, gap_report)

        command_report: dict[str, Any] = {
            "ok": False,
            "system": "FOXAI Fleet Command",
            "version": "CM v4.0",
            "request": request,
            "plan": plan,
            "gap_report": gap_report,
            "fleet": fleet_snapshot,
            "decision": decision,
            "execution": None,
            "elapsed_ms": 0,
        }

        if decision["decision"] == "execute_safe":
            execution = self.executor.execute(request, mode=mode)
            command_report["execution"] = execution
            command_report["ok"] = bool(execution.get("ok"))
        elif decision["decision"] == "plan_only":
            command_report["ok"] = True
        else:
            command_report["ok"] = False

        command_report["elapsed_ms"] = int((time.perf_counter() - started) * 1000)

        # Log Fleet Command decision as its own event when an execution mission exists.
        execution = command_report.get("execution") or {}
        mission_id = execution.get("mission_id")
        if mission_id:
            self.vault.log_event(
                mission_id=mission_id,
                level="INFO",
                source="Fleet Command",
                message="Fleet Command issued mission decision.",
                data=json.dumps({
                    "decision": decision,
                    "fleet": fleet_snapshot,
                    "elapsed_ms": command_report["elapsed_ms"],
                }, ensure_ascii=False),
            )

        return command_report

    def render_text(self, report: dict[str, Any]) -> str:
        lines = []
        lines.append("FOXAI Fleet Command Report")
        lines.append("==========================")
        lines.append("")
        lines.append(f"Version: {report.get('version')}")
        lines.append(f"OK: {report.get('ok')}")
        lines.append(f"Elapsed: {report.get('elapsed_ms')} ms")
        lines.append("")

        plan = report.get("plan", {})
        lines.append("Mission Order:")
        lines.append(f"- Request: {plan.get('request')}")
        lines.append(f"- Mission Type: {plan.get('mission_type')}")
        lines.append(f"- Department: {plan.get('department')}")
        lines.append(f"- Professor: {plan.get('professor')}")
        lines.append("")

        fleet = report.get("fleet", {})
        lines.append("Fleet Snapshot:")
        lines.append(f"- Total: {fleet.get('total')}")
        lines.append(f"- States: {fleet.get('states')}")
        lines.append(f"- Kinds: {fleet.get('kinds')}")
        lines.append("")

        decision = report.get("decision", {})
        lines.append("Command Decision:")
        lines.append(f"- Decision: {decision.get('decision')}")
        lines.append(f"- Reason: {decision.get('reason')}")
        lines.append("")

        lines.append("Assignments:")
        for a in decision.get("assignments", []):
            state = "OK" if a.get("available") else "MISSING"
            lines.append(f"- {a.get('capability')} [{state}] -> {a.get('assigned_shuttle') or a.get('assigned_key') or 'None'}")

        execution = report.get("execution")
        if execution:
            lines.append("")
            lines.append("Execution:")
            lines.append(f"- Mission ID: {execution.get('mission_id')}")
            lines.append(f"- Status: {execution.get('status')}")
            lines.append(f"- OK: {execution.get('ok')}")
            for idx, result in enumerate(execution.get("results", []), start=1):
                lines.append(f"  {idx}. {result.get('capability')} via {result.get('shuttle')} [{result.get('status')}]")
                inner = result.get("result")
                if isinstance(inner, dict) and inner.get("answer"):
                    lines.append(f"     Answer: {inner.get('answer')}")
                elif isinstance(inner, dict):
                    lines.append(f"     Message: {inner.get('message', '')}")
                else:
                    lines.append(f"     Message: {result.get('message', '')}")

        return "\n".join(lines)
