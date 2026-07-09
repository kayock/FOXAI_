from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fleet_registry import FleetRegistry


RECOMMENDATIONS = {
    "general_reasoning": {
        "priority": "critical",
        "recommended_shuttle": "USS Conversation Shuttle",
        "department": "Academy",
        "reason": "Needed for chat, humor, teaching, general Q&A, and professor responses.",
        "install_candidate": "USS Conversation Shuttle / llama.cpp / Ollama / LiteLLM adapter",
    },
    "creative_writing": {
        "priority": "high",
        "recommended_shuttle": "Novel Forge",
        "department": "Creative Studio",
        "reason": "Needed for story planning, RPG DM behavior, chapters, characters, and worldbuilding.",
        "install_candidate": "Novel Forge / local writing module",
    },
    "story_memory": {
        "priority": "high",
        "recommended_shuttle": "Novel Forge Codex Shuttle",
        "department": "Creative Studio",
        "reason": "Needed for persistent character, timeline, continuity, and canon tracking.",
        "install_candidate": "Novel Forge + Vault tables",
    },
    "image_generation": {
        "priority": "medium",
        "recommended_shuttle": "USS Image Forge",
        "department": "Creative Studio",
        "reason": "Needed for image, logo, concept art, and visual generation missions.",
        "install_candidate": "ComfyUI / FLUX / SDXL",
    },
    "creative_studio": {
        "priority": "medium",
        "recommended_shuttle": "Creative Studio Shuttle",
        "department": "Creative Studio",
        "reason": "Needed to route creative generation tools through Mission Bus.",
        "install_candidate": "ComfyUI adapter / Novel Forge adapter",
    },
    "documents": {
        "priority": "medium",
        "recommended_shuttle": "USS Library Shuttle",
        "department": "Iron Library",
        "reason": "Needed for document research, manuals, PDFs, and offline knowledge.",
        "install_candidate": "Iron Library / LlamaIndex later",
    },
    "reference": {
        "priority": "medium",
        "recommended_shuttle": "USS Library Shuttle",
        "department": "Iron Library",
        "reason": "Needed to answer from local references instead of guessing.",
        "install_candidate": "Iron Library / Kiwix / local docs",
    },
    "diagnostics": {
        "priority": "medium",
        "recommended_shuttle": "Repair Bay Diagnostic Shuttle",
        "department": "Repair Bay",
        "reason": "Needed for system repair and health missions.",
        "install_candidate": "CrystalDiskInfo / HWMonitor / System Informer adapters",
    },
    "repair": {
        "priority": "medium",
        "recommended_shuttle": "Repair Bay Shuttle",
        "department": "Repair Bay",
        "reason": "Needed for safe system repair workflows.",
        "install_candidate": "Repair Bay read-only diagnostics first",
    },
    "automation": {
        "priority": "medium",
        "recommended_shuttle": "Automation Shuttle",
        "department": "Automation",
        "reason": "Needed for reminders, watchers, repeated tasks, and scheduled missions.",
        "install_candidate": "Watchdog + scheduler",
    },
    "watch": {
        "priority": "medium",
        "recommended_shuttle": "Watchtower Shuttle",
        "department": "Automation",
        "reason": "Needed for monitoring files, folders, models, and Hangar Bay changes.",
        "install_candidate": "Watchdog",
    },
}


@dataclass
class CapabilityGapAnalyzer:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.fleet = FleetRegistry(self.foxai_root)

    def _available_capabilities(self) -> dict[str, list[dict[str, Any]]]:
        """
        Single source of truth:
        Always refresh Fleet Registry first, then read capability providers from it.
        No local cached/hard-coded installed capability list.
        """
        data = self.fleet.refresh()
        shuttles = list((data.get("shuttles") or {}).values())
        caps: dict[str, list[dict[str, Any]]] = {}

        for shuttle in shuttles:
            if shuttle.get("service_state") != "Operational":
                continue
            for cap in shuttle.get("capabilities", []):
                caps.setdefault(str(cap), []).append(shuttle)

        return caps

    def analyze_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        available = self._available_capabilities()
        required: list[str] = []

        for step in plan.get("steps", []):
            cap = step.get("capability")
            if cap and cap not in required:
                required.append(cap)

        intent = plan.get("intent") or {}
        for cap in intent.get("required_capabilities", []):
            if cap and cap not in required:
                required.append(cap)

        gaps = []
        available_count = 0
        missing_count = 0

        for cap in required:
            shuttles = available.get(cap, [])
            if shuttles:
                available_count += 1
                chosen = shuttles[0]
                item = {
                    "capability": cap,
                    "available": True,
                    "priority": "satisfied",
                    "assigned_shuttle": chosen.get("callsign"),
                    "assigned_key": chosen.get("key"),
                    "recommended_shuttle": None,
                    "department": chosen.get("department"),
                    "reason": "Capability is available in the Fleet Registry.",
                    "install_candidate": None,
                }
            else:
                missing_count += 1
                rec = RECOMMENDATIONS.get(cap, {})
                item = {
                    "capability": cap,
                    "available": False,
                    "priority": rec.get("priority", "unknown"),
                    "assigned_shuttle": None,
                    "assigned_key": None,
                    "recommended_shuttle": rec.get("recommended_shuttle"),
                    "department": rec.get("department"),
                    "reason": rec.get("reason", "No recommendation exists yet for this missing capability."),
                    "install_candidate": rec.get("install_candidate"),
                }
            gaps.append(item)

        return {
            "ok": True,
            "source_of_truth": "FleetRegistry.refresh()",
            "request": plan.get("request", ""),
            "mission_type": plan.get("mission_type"),
            "department": plan.get("department"),
            "professor": plan.get("professor"),
            "total_required": len(required),
            "available_count": available_count,
            "missing_count": missing_count,
            "gaps": gaps,
        }

    def render_text(self, report: dict[str, Any]) -> str:
        lines = []
        lines.append("FOXAI Capability Gap Analysis")
        lines.append("=============================")
        lines.append("")
        lines.append(f"Source: {report.get('source_of_truth')}")
        lines.append(f"Request: {report.get('request')}")
        lines.append(f"Mission Type: {report.get('mission_type')}")
        lines.append(f"Department: {report.get('department')}")
        lines.append(f"Professor: {report.get('professor')}")
        lines.append("")
        lines.append(f"Required: {report.get('total_required')}")
        lines.append(f"Available: {report.get('available_count')}")
        lines.append(f"Missing: {report.get('missing_count')}")
        lines.append("")

        for gap in report.get("gaps", []):
            status = "OK" if gap.get("available") else "MISSING"
            lines.append(f"- {gap.get('capability')} [{status}]")
            if gap.get("available"):
                lines.append(f"  Assigned: {gap.get('assigned_shuttle')}")
                lines.append(f"  Key: {gap.get('assigned_key')}")
                lines.append(f"  Department: {gap.get('department')}")
            else:
                lines.append(f"  Priority: {gap.get('priority')}")
                lines.append(f"  Recommend: {gap.get('recommended_shuttle')}")
                lines.append(f"  Department: {gap.get('department')}")
                lines.append(f"  Candidate: {gap.get('install_candidate')}")
                lines.append(f"  Reason: {gap.get('reason')}")
            lines.append("")

        return "\n".join(lines)
