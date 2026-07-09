from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import time
import traceback

from .fleet_registry import FleetRegistry
from .mission_bus import MissionBus
from .mission_executor import MissionExecutor
from .fleet_command_bridge import FleetCommandBridge
from .bridge_officers import BridgeOfficerRegistry
from .hangar_bay_inspector import HangarBayInspector
from .vault import Vault


@dataclass
class FOXKernel:
    """
    FOXAI Command OS Kernel Foundation.

    The kernel is the one stable entry point for FOXAI core systems.
    Future modules should plug into the kernel instead of wiring directly
    to each other.
    """

    foxai_root: Path
    booted: bool = False
    boot_errors: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.started_at = time.time()

        self.vault: Vault | None = None
        self.mission_bus: MissionBus | None = None
        self.fleet_registry: FleetRegistry | None = None
        self.mission_executor: MissionExecutor | None = None
        self.fleet_command: FleetCommandBridge | None = None
        self.bridge_officers: BridgeOfficerRegistry | None = None
        self.hangar_bay: HangarBayInspector | None = None

    @property
    def outbox(self) -> Path:
        path = self.foxai_root / "OpsBridge" / "outbox"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _safe_init(self, name: str, factory) -> Any:
        try:
            obj = factory()
            return obj
        except Exception as exc:
            self.boot_errors.append({
                "component": name,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            })
            return None

    def boot(self) -> dict[str, Any]:
        self.boot_errors = []

        self.vault = self._safe_init("Vault", lambda: Vault(self.foxai_root))
        if self.vault:
            try:
                self.vault.initialize()
            except Exception as exc:
                self.boot_errors.append({
                    "component": "Vault.initialize",
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                })

        self.mission_bus = self._safe_init("MissionBus", lambda: MissionBus(self.foxai_root))
        self.fleet_registry = self._safe_init("FleetRegistry", lambda: FleetRegistry(self.foxai_root))
        self.hangar_bay = self._safe_init("HangarBayInspector", lambda: HangarBayInspector(self.foxai_root))
        self.bridge_officers = self._safe_init("BridgeOfficerRegistry", lambda: BridgeOfficerRegistry(self.foxai_root))
        self.mission_executor = self._safe_init("MissionExecutor", lambda: MissionExecutor(self.foxai_root))
        self.fleet_command = self._safe_init("FleetCommandBridge", lambda: FleetCommandBridge(self.foxai_root))

        self.booted = len(self.boot_errors) == 0
        report = self.status()
        self.write_status(report)
        return report

    def fleet_status(self) -> dict[str, Any]:
        if not self.fleet_registry:
            return {"ok": False, "message": "FleetRegistry not initialized."}
        data = self.fleet_registry.refresh()
        summary = self.fleet_registry.summary(data)
        return {
            "ok": True,
            "summary": summary,
            "data": data,
        }

    def runtime_status(self) -> dict[str, Any]:
        if not self.hangar_bay:
            return {"ok": False, "message": "HangarBayInspector not initialized."}
        inventory = self.hangar_bay.scan()
        return {
            "ok": True,
            "roots": inventory.get("roots", []),
            "package_count": inventory.get("package_count", 0),
            "import_count": inventory.get("import_count", 0),
        }

    def officer_status(self) -> dict[str, Any]:
        if not self.bridge_officers:
            return {"ok": False, "message": "BridgeOfficerRegistry not initialized."}

        report = self.bridge_officers.assignment_report({
            "mission_type": "Kernel Status",
            "department": "Fleet Command",
            "professor": "Technology Officer",
        })
        return {
            "ok": True,
            "frameworks": report.get("frameworks", {}),
            "officer_count": report.get("total_officers", 0),
            "runtime_detection": report.get("runtime_detection", {}),
        }

    def status(self) -> dict[str, Any]:
        uptime = int(time.time() - self.started_at)

        components = {
            "vault": self.vault is not None,
            "mission_bus": self.mission_bus is not None,
            "fleet_registry": self.fleet_registry is not None,
            "hangar_bay": self.hangar_bay is not None,
            "bridge_officers": self.bridge_officers is not None,
            "mission_executor": self.mission_executor is not None,
            "fleet_command": self.fleet_command is not None,
        }

        fleet = self.fleet_status() if self.fleet_registry else {"ok": False}
        runtime = self.runtime_status() if self.hangar_bay else {"ok": False}
        officers = self.officer_status() if self.bridge_officers else {"ok": False}

        return {
            "ok": all(components.values()) and not self.boot_errors,
            "kernel": "FOXKernel",
            "version": "Command OS v6.0",
            "root": str(self.foxai_root),
            "booted": self.booted,
            "uptime_seconds": uptime,
            "components": components,
            "fleet": fleet,
            "runtime": runtime,
            "officers": officers,
            "errors": self.boot_errors,
        }

    def command(self, request: str, mode: str = "safe") -> dict[str, Any]:
        if not self.booted:
            self.boot()

        if not self.fleet_command:
            return {
                "ok": False,
                "message": "FleetCommandBridge is not initialized.",
                "request": request,
            }

        result = self.fleet_command.command(request, mode=mode)
        self.write_latest_command(result)
        return result

    def write_status(self, report: dict[str, Any]) -> None:
        (self.outbox / "kernel_status.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.outbox / "kernel_status.txt").write_text(
            self.render_status(report),
            encoding="utf-8",
        )

    def write_latest_command(self, report: dict[str, Any]) -> None:
        (self.outbox / "kernel_latest_command.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def render_status(self, report: dict[str, Any]) -> str:
        lines = []
        lines.append("FOXAI Command OS v6.0")
        lines.append("FOXKernel Status")
        lines.append("====================")
        lines.append("")
        lines.append(f"OK: {report.get('ok')}")
        lines.append(f"Booted: {report.get('booted')}")
        lines.append(f"Root: {report.get('root')}")
        lines.append(f"Uptime: {report.get('uptime_seconds')} seconds")
        lines.append("")

        lines.append("Components:")
        for key, value in report.get("components", {}).items():
            lines.append(f"- {key}: {'READY' if value else 'MISSING'}")
        lines.append("")

        fleet = report.get("fleet", {})
        summary = fleet.get("summary", {}) if isinstance(fleet, dict) else {}
        if summary:
            lines.append("Fleet:")
            lines.append(f"- Total: {summary.get('total')}")
            lines.append(f"- States: {summary.get('states')}")
            lines.append(f"- Kinds: {summary.get('kinds')}")
            lines.append("")

        runtime = report.get("runtime", {})
        if runtime.get("ok"):
            lines.append("Runtime:")
            lines.append(f"- Roots: {runtime.get('roots')}")
            lines.append(f"- Packages: {runtime.get('package_count')}")
            lines.append(f"- Imports: {runtime.get('import_count')}")
            lines.append("")

        officers = report.get("officers", {})
        if officers.get("ok"):
            lines.append("Bridge Officers:")
            lines.append(f"- Officer Count: {officers.get('officer_count')}")
            lines.append("Frameworks:")
            for key, item in officers.get("frameworks", {}).items():
                lines.append(f"  - {item.get('label')}: {item.get('status')} ({item.get('source')})")
            lines.append("")

        if report.get("errors"):
            lines.append("Errors:")
            for err in report.get("errors", []):
                lines.append(f"- {err.get('component')}: {err.get('error')}")

        return "\n".join(lines)
