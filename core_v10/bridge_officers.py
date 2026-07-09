from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import importlib.util

from .hangar_bay_inspector import HangarBayInspector


FRAMEWORKS = {
    "crewai": {
        "label": "CrewAI",
        "use": "Optional officer/crew agent implementation.",
        "aliases": ["crewai", "crewai_tools", "crew_ai"],
    },
    "autogen": {
        "label": "AutoGen",
        "use": "Optional multi-agent discussion and review loops.",
        "aliases": ["autogen", "autogen_agentchat", "autogen_core", "pyautogen", "autogen_ext"],
    },
    "langgraph": {
        "label": "LangGraph",
        "use": "Optional stateful mission workflow graph.",
        "aliases": ["langgraph", "langgraph_sdk", "langgraph_checkpoint"],
    },
    "llama_index": {
        "label": "LlamaIndex",
        "use": "Optional knowledge index, Novel Forge Codex, Academy retrieval.",
        "aliases": ["llama_index", "llama-index", "llama_index_core"],
    },
}


OFFICER_ROSTER = {
    "xo": {
        "name": "Executive Officer",
        "callsign": "XO",
        "department": "Fleet Command",
        "responsibilities": ["Mission authorization", "Priority handling", "Retry and cancellation policy", "Mission readiness checks"],
        "preferred_frameworks": ["langgraph", "crewai"],
    },
    "operations": {
        "name": "Operations Officer",
        "callsign": "Ops",
        "department": "Fleet Command",
        "responsibilities": ["Fleet Registry", "Shuttle availability", "Health status", "Routing constraints"],
        "preferred_frameworks": ["langgraph"],
    },
    "science": {
        "name": "Science Officer",
        "callsign": "Science",
        "department": "Academy",
        "responsibilities": ["Capability matching", "Knowledge retrieval", "Research routing", "Evidence review"],
        "preferred_frameworks": ["llama_index", "autogen"],
    },
    "engineering": {
        "name": "Engineering Officer",
        "callsign": "Engineering",
        "department": "Engineering",
        "responsibilities": ["Diagnostics", "Testing", "Code quality", "Repair Bay coordination"],
        "preferred_frameworks": ["crewai", "langgraph"],
    },
    "communications": {
        "name": "Communications Officer",
        "callsign": "Comms",
        "department": "Artificial Minds",
        "responsibilities": ["Conversation Shuttle", "Professor routing", "External provider adapters", "Response formatting"],
        "preferred_frameworks": ["crewai", "autogen"],
    },
    "creative": {
        "name": "Creative Officer",
        "callsign": "Creative",
        "department": "Creative Studio",
        "responsibilities": ["Novel Forge", "Image Forge", "PromptSmith", "Story and worldbuilding missions"],
        "preferred_frameworks": ["llama_index", "crewai"],
    },
}


@dataclass
class BridgeOfficer:
    key: str
    name: str
    callsign: str
    department: str
    responsibilities: list[str] = field(default_factory=list)
    preferred_frameworks: list[str] = field(default_factory=list)

    def assign(self, mission: dict[str, Any], available_frameworks: dict[str, Any]) -> dict[str, Any]:
        usable = [
            f for f in self.preferred_frameworks
            if available_frameworks.get(f, {}).get("installed")
        ]
        return {
            "officer": self.name,
            "callsign": self.callsign,
            "department": self.department,
            "mission_type": mission.get("mission_type"),
            "assigned": True,
            "frameworks_available": usable,
            "mode": "foxai_native" if not usable else "foxai_native_with_optional_frameworks",
            "note": "Officer assignment is native FOXAI; external frameworks are optional accelerators.",
        }


@dataclass
class BridgeOfficerRegistry:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.inspector = HangarBayInspector(self.foxai_root)

    def _find_active_python(self, aliases: list[str]) -> dict[str, Any] | None:
        for alias in aliases:
            import_name = alias.replace("-", "_")
            if importlib.util.find_spec(import_name) is not None:
                return {
                    "installed": True,
                    "source": "active_python",
                    "path": "",
                    "matched_alias": alias,
                    "matched_by": "importlib",
                    "version": "",
                    "package": alias,
                }
        return None

    def _find_framework(self, key: str, meta: dict[str, Any]) -> dict[str, Any]:
        aliases = meta.get("aliases", [key])

        active = self._find_active_python(aliases)
        if active:
            return active

        hanger = self.inspector.find(aliases)
        if hanger:
            return {
                "installed": True,
                "source": "hanger_bay",
                "path": hanger.get("path", ""),
                "matched_alias": hanger.get("matched_alias", ""),
                "matched_by": hanger.get("matched_by", ""),
                "version": hanger.get("version", ""),
                "package": hanger.get("package", ""),
                "import_names": hanger.get("import_names", []),
            }

        return {
            "installed": False,
            "source": "not_found",
            "path": "",
            "matched_alias": "",
            "matched_by": "",
            "version": "",
            "package": "",
            "import_names": [],
        }

    def framework_status(self) -> dict[str, Any]:
        status = {}
        for key, meta in FRAMEWORKS.items():
            found = self._find_framework(key, meta)
            status[key] = {
                "installed": bool(found["installed"]),
                "label": meta["label"],
                "use": meta["use"],
                "status": "ready" if found["installed"] else "missing",
                "source": found["source"],
                "path": found["path"],
                "matched_alias": found["matched_alias"],
                "matched_by": found.get("matched_by", ""),
                "version": found.get("version", ""),
                "package": found.get("package", ""),
                "import_names": found.get("import_names", []),
            }
        return status

    def officers(self) -> dict[str, BridgeOfficer]:
        return {key: BridgeOfficer(key=key, **data) for key, data in OFFICER_ROSTER.items()}

    def choose_officers(self, mission: dict[str, Any]) -> list[BridgeOfficer]:
        mission_type = str(mission.get("mission_type", "")).lower()
        department = str(mission.get("department", "")).lower()
        chosen = ["xo", "operations"]

        if "engineering" in mission_type or "engineering" in department:
            chosen += ["science", "engineering", "communications"]
        elif "creative" in mission_type or "creative" in department:
            chosen += ["creative", "communications", "science"]
        elif "conversation" in mission_type or "academy" in department:
            chosen += ["communications", "science"]
        else:
            chosen += ["science", "communications"]

        roster = self.officers()
        return [roster[k] for k in dict.fromkeys(chosen) if k in roster]

    def assignment_report(self, mission: dict[str, Any]) -> dict[str, Any]:
        frameworks = self.framework_status()
        officers = self.choose_officers(mission)
        assignments = [o.assign(mission, frameworks) for o in officers]
        inventory = self.inspector.write_inventory()
        return {
            "ok": True,
            "mission": mission,
            "frameworks": frameworks,
            "officers": assignments,
            "total_officers": len(assignments),
            "runtime_detection": {
                "checks": ["active_python", "hangar_bay_package_inventory"],
                "inventory_path": inventory.get("path"),
                "package_count": inventory.get("inventory", {}).get("package_count"),
                "roots": inventory.get("inventory", {}).get("roots", []),
            },
        }

    def render_text(self, report: dict[str, Any]) -> str:
        lines = []
        lines.append("FOXAI Bridge Officer Assignment")
        lines.append("===============================")
        lines.append("")
        mission = report.get("mission", {})
        lines.append(f"Mission Type: {mission.get('mission_type')}")
        lines.append(f"Department: {mission.get('department')}")
        lines.append(f"Professor: {mission.get('professor')}")
        lines.append("")
        lines.append("Frameworks:")
        for key, item in report.get("frameworks", {}).items():
            version = f" {item.get('version')}" if item.get("version") else ""
            package = f" package={item.get('package')}" if item.get("package") else ""
            lines.append(f"- {item['label']}: {item['status']} ({item.get('source')}, {item.get('matched_alias')}){version}{package} — {item['use']}")
            if item.get("path"):
                lines.append(f"  Path: {item['path']}")
        lines.append("")
        lines.append("Assigned Officers:")
        for officer in report.get("officers", []):
            lines.append(f"- {officer['callsign']} / {officer['officer']} [{officer['department']}]")
            lines.append(f"  Mode: {officer['mode']}")
            if officer.get("frameworks_available"):
                lines.append(f"  Optional frameworks: {', '.join(officer['frameworks_available'])}")
        return "\n".join(lines)
