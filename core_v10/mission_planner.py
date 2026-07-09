from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fleet_registry import FleetRegistry
from .intent_engine import IntentEngine


@dataclass
class MissionPlanner:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.fleet = FleetRegistry(self.foxai_root)
        self.intent_engine = IntentEngine()

    def _fleet_summary(self) -> dict[str, Any]:
        data = self.fleet.refresh()
        return self.fleet.summary(data)

    def find_shuttles_for_capability(self, capability: str) -> list[dict[str, Any]]:
        data = self.fleet.load()
        shuttles = list((data.get("shuttles") or {}).values())

        matches = []
        for shuttle in shuttles:
            caps = [str(c).lower() for c in shuttle.get("capabilities", [])]
            if capability.lower() in caps:
                score = 0
                if shuttle.get("service_state") == "Operational":
                    score += 100
                if shuttle.get("installed"):
                    score += 25
                if shuttle.get("reserved"):
                    score -= 50
                score += max(0, 10 - int(shuttle.get("launches", 0)))
                matches.append({**shuttle, "planner_score": score})

        return sorted(matches, key=lambda x: x.get("planner_score", 0), reverse=True)

    def create_plan(self, request: str, professor: str | None = None) -> dict[str, Any]:
        summary = self._fleet_summary()
        intent = self.intent_engine.classify(request)
        lead = professor or intent.get("lead_professor", "Professor Kayock")
        steps = []

        for i, capability in enumerate(intent.get("required_capabilities", []), start=1):
            candidates = self.find_shuttles_for_capability(capability)

            if candidates:
                chosen = candidates[0]
                steps.append({
                    "step": i,
                    "type": "capability",
                    "capability": capability,
                    "intent": f"Use capability for {intent.get('mission_type')}.",
                    "confidence": intent.get("confidence"),
                    "status": "planned",
                    "chosen_shuttle": {
                        "key": chosen.get("key"),
                        "callsign": chosen.get("callsign"),
                        "department": chosen.get("department"),
                        "service_state": chosen.get("service_state"),
                        "path": chosen.get("path"),
                    },
                    "alternatives": [
                        {
                            "key": alt.get("key"),
                            "callsign": alt.get("callsign"),
                            "service_state": alt.get("service_state"),
                            "score": alt.get("planner_score"),
                        }
                        for alt in candidates[1:4]
                    ],
                })
            else:
                steps.append({
                    "step": i,
                    "type": "capability",
                    "capability": capability,
                    "intent": f"Use capability for {intent.get('mission_type')}.",
                    "confidence": intent.get("confidence"),
                    "status": "no_shuttle_available",
                    "chosen_shuttle": None,
                    "alternatives": [],
                })

        return {
            "ok": True,
            "schema": 2,
            "planner": "Mission Planner v3.1",
            "request": request,
            "intent": intent,
            "objective": intent.get("objective"),
            "mission_type": intent.get("mission_type"),
            "department": intent.get("department"),
            "professor": lead,
            "fleet_state": {
                "updated": summary.get("updated"),
                "total": summary.get("total"),
                "states": summary.get("states"),
            },
            "steps": steps,
            "execution_mode": "plan_only",
            "safety": "No tools launched by Mission Planner v3.1.",
        }

    def render_plan_text(self, plan: dict[str, Any]) -> str:
        lines = []
        lines.append("Mission Planner v3.1 — Intent Engine")
        lines.append("====================================")
        lines.append("")
        lines.append(f"Request: {plan.get('request')}")
        lines.append(f"Objective: {plan.get('objective')}")
        lines.append(f"Mission Type: {plan.get('mission_type')}")
        lines.append(f"Department: {plan.get('department')}")
        lines.append(f"Lead Professor: {plan.get('professor')}")
        intent = plan.get("intent", {})
        lines.append(f"Confidence: {intent.get('confidence')}")
        if intent.get("needs_clarification"):
            lines.append("Clarification: recommended")
        lines.append(f"Mode: {plan.get('execution_mode')}")
        lines.append("")
        lines.append("Fleet:")
        fs = plan.get("fleet_state", {})
        lines.append(f"  Total shuttle pods: {fs.get('total')}")
        lines.append(f"  States: {fs.get('states')}")
        lines.append("")
        lines.append("Plan:")

        for step in plan.get("steps", []):
            lines.append(f"  {step['step']}. Need: {step['capability']}")
            if step.get("chosen_shuttle"):
                shuttle = step["chosen_shuttle"]
                lines.append(f"     Shuttle: {shuttle['callsign']} [{shuttle['service_state']}]")
            else:
                lines.append("     Shuttle: None available")
            lines.append(f"     Status: {step['status']}")
            lines.append("")

        lines.append(plan.get("safety", ""))
        return "\n".join(lines)
