from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import time

from .capability_gap_analyzer import CapabilityGapAnalyzer
from .extension_manager import ExtensionManager
from .fleet_registry import FleetRegistry
from .mission_planner import MissionPlanner
from .vault import Vault


SAFE_EXECUTION_CAPABILITIES = {
    "general_reasoning",
    "conversation",
    "brainstorming",
    "teaching",
    "planning",
    "summarization",
    "creative_writing",
    "mission_history",
}


@dataclass
class MissionExecutor:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.planner = MissionPlanner(self.foxai_root)
        self.gap = CapabilityGapAnalyzer(self.foxai_root)
        self.fleet = FleetRegistry(self.foxai_root)
        self.extensions = ExtensionManager(self.foxai_root)
        self.vault = Vault(self.foxai_root)
        self.vault.initialize()

    def _new_mission(self, plan: dict[str, Any]) -> int:
        result = self.vault.log_mission(
            title=plan.get("request", "Mission")[:80],
            request=plan.get("request", ""),
            professor=plan.get("professor", "Professor Kayock"),
            mission_type=plan.get("mission_type", "unknown"),
            department=plan.get("department", "General"),
            status="running",
        )
        return int(result["mission_id"])

    def _log(self, mission_id: int, level: str, source: str, message: str, data: dict[str, Any] | None = None) -> None:
        self.vault.log_event(
            mission_id=mission_id,
            level=level,
            source=source,
            message=message,
            data=json.dumps(data or {}, ensure_ascii=False),
        )

    def execute(self, request: str, mode: str = "safe") -> dict[str, Any]:
        started = time.perf_counter()
        plan = self.planner.create_plan(request)
        mission_id = self._new_mission(plan)

        self._log(mission_id, "INFO", "MissionExecutor", "Mission planning complete.", {"plan": plan})

        gap_report = self.gap.analyze_plan(plan)
        self._log(mission_id, "INFO", "MissionExecutor", "Capability gap analysis complete.", {"gap_report": gap_report})

        if gap_report.get("missing_count", 0):
            self._log(mission_id, "WARN", "MissionExecutor", "Mission has missing capabilities.", {"missing": gap_report.get("gaps", [])})
            return {
                "ok": False,
                "mission_id": mission_id,
                "status": "blocked_missing_capability",
                "plan": plan,
                "gap_report": gap_report,
                "results": [],
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }

        results = []
        executed = set()

        for gap in gap_report.get("gaps", []):
            capability = gap.get("capability")
            shuttle_key = gap.get("assigned_key")

            if not shuttle_key:
                continue

            if capability not in SAFE_EXECUTION_CAPABILITIES and mode == "safe":
                item = {
                    "capability": capability,
                    "shuttle": shuttle_key,
                    "status": "planned_only",
                    "message": "Capability not executed in safe mode.",
                }
                results.append(item)
                self._log(mission_id, "INFO", "MissionExecutor", "Step left plan-only in safe mode.", item)
                continue

            # Avoid double-dispatching the same service for multiple related capabilities.
            dispatch_key = f"{shuttle_key}:chat" if shuttle_key == "conversation" else f"{shuttle_key}:{capability}"
            if dispatch_key in executed:
                continue
            executed.add(dispatch_key)

            if shuttle_key == "conversation":
                payload = {
                    "prompt": request,
                    "professor": plan.get("professor", "Professor Kayock"),
                    "mission_id": mission_id,
                    "metadata": {
                        "mission_type": plan.get("mission_type"),
                        "department": plan.get("department"),
                        "capability": capability,
                    },
                }
                result = self.extensions.invoke("conversation", "chat", payload)
                results.append({
                    "capability": capability,
                    "shuttle": "conversation",
                    "status": "executed",
                    "result": result,
                })
                self._log(mission_id, "INFO" if result.get("ok") else "ERROR", "USS Conversation Shuttle", "Conversation step executed.", result)
            elif shuttle_key == "database":
                item = {
                    "capability": capability,
                    "shuttle": shuttle_key,
                    "status": "already_logged",
                    "message": "Mission history is represented by Vault logging.",
                }
                results.append(item)
                self._log(mission_id, "INFO", "USS Database Shuttle", "Mission history step satisfied by Vault logging.", item)
            else:
                item = {
                    "capability": capability,
                    "shuttle": shuttle_key,
                    "status": "planned_only",
                    "message": "Executor foundation does not invoke this shuttle yet.",
                }
                results.append(item)
                self._log(mission_id, "INFO", "MissionExecutor", "Step planned but not invoked.", item)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        ok = all((r.get("result", r).get("ok", True) if isinstance(r.get("result", r), dict) else True) for r in results)

        self._log(mission_id, "INFO" if ok else "ERROR", "MissionExecutor", "Mission execution complete.", {
            "ok": ok,
            "elapsed_ms": elapsed_ms,
            "result_count": len(results),
        })

        return {
            "ok": ok,
            "mission_id": mission_id,
            "status": "complete" if ok else "complete_with_errors",
            "plan": plan,
            "gap_report": gap_report,
            "results": results,
            "elapsed_ms": elapsed_ms,
        }

    def render_text(self, report: dict[str, Any]) -> str:
        lines = []
        lines.append("FOXAI Mission Execution Report")
        lines.append("==============================")
        lines.append("")
        lines.append(f"Mission ID: {report.get('mission_id')}")
        lines.append(f"Status: {report.get('status')}")
        lines.append(f"OK: {report.get('ok')}")
        lines.append(f"Elapsed: {report.get('elapsed_ms')} ms")
        lines.append("")

        plan = report.get("plan", {})
        lines.append("Plan:")
        lines.append(f"- Request: {plan.get('request')}")
        lines.append(f"- Mission Type: {plan.get('mission_type')}")
        lines.append(f"- Department: {plan.get('department')}")
        lines.append(f"- Professor: {plan.get('professor')}")
        lines.append("")

        gap = report.get("gap_report", {})
        lines.append("Capabilities:")
        lines.append(f"- Required: {gap.get('total_required')}")
        lines.append(f"- Available: {gap.get('available_count')}")
        lines.append(f"- Missing: {gap.get('missing_count')}")
        lines.append("")

        lines.append("Results:")
        for idx, result in enumerate(report.get("results", []), start=1):
            lines.append(f"{idx}. {result.get('capability')} via {result.get('shuttle')} [{result.get('status')}]")
            inner = result.get("result")
            if isinstance(inner, dict):
                if inner.get("answer"):
                    lines.append(f"   Answer: {inner.get('answer')}")
                else:
                    lines.append(f"   Message: {inner.get('message', inner.get('status', ''))}")
            else:
                lines.append(f"   Message: {result.get('message', '')}")
        return "\n".join(lines)
