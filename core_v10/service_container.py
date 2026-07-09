from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from dependency_injector import containers
except Exception:
    containers = None

from .capability_gap_analyzer import CapabilityGapAnalyzer
from .extension_manager import ExtensionManager
from .fleet_registry import FleetRegistry
from .foxai_signals import FoxAISignals
from .mission_planner import MissionPlanner
from .service_contracts import ServiceContract, ServiceHealth
from .vault import Vault


@dataclass
class ServiceContainer:
    foxai_root: Path
    services: dict[str, Any] = field(default_factory=dict)
    contracts: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.signals = FoxAISignals()
        self._register_core_services()

    def _contract(self, **kwargs):
        try:
            return ServiceContract(**kwargs)
        except Exception:
            return kwargs

    def _health(self, **kwargs):
        try:
            return ServiceHealth(**kwargs)
        except Exception:
            return kwargs

    def register(self, key: str, service: Any, contract: Any) -> None:
        self.services[key] = service
        self.contracts[key] = contract
        self.signals.emit("service_registered", sender="ServiceContainer", key=key)

    def _register_core_services(self) -> None:
        self.register("vault", Vault(self.foxai_root), self._contract(
            key="vault", name="FOXAI Vault", kind="storage", department="Engineering",
            provides=["mission_history", "mission_logs", "database_update", "database_query"],
            consumes=[], methods=["initialize", "log_mission", "log_step", "log_event", "list_missions"],
            version="1.0", status="ready"))

        self.register("fleet_registry", FleetRegistry(self.foxai_root), self._contract(
            key="fleet_registry", name="Fleet Registry", kind="registry", department="Engineering",
            provides=["fleet_status", "shuttle_inventory", "capability_inventory"],
            consumes=["extension_manager"], methods=["refresh", "scan_and_commission", "summary", "mark_used"],
            version="1.0", status="ready"))

        self.register("extension_manager", ExtensionManager(self.foxai_root), self._contract(
            key="extension_manager", name="Extension Manager", kind="extension_system", department="Engineering",
            provides=["extension_discovery", "plugin_hooks", "shuttle_launch", "shuttle_invoke"],
            consumes=["pluggy"], methods=["list_extensions", "passive_health", "diagnostic_health", "launch", "invoke"],
            version="1.0", status="ready"))

        self.register("mission_planner", MissionPlanner(self.foxai_root), self._contract(
            key="mission_planner", name="Mission Planner", kind="planner", department="Mission Control",
            provides=["mission_planning", "intent_routing", "capability_planning"],
            consumes=["fleet_registry", "intent_engine"], methods=["create_plan", "render_plan_text"],
            version="3.1", status="ready"))

        self.register("capability_gap_analyzer", CapabilityGapAnalyzer(self.foxai_root), self._contract(
            key="capability_gap_analyzer", name="Capability Gap Analyzer", kind="analysis", department="Engineering",
            provides=["capability_gap_analysis", "upgrade_recommendations"],
            consumes=["fleet_registry", "mission_planner"], methods=["analyze_plan", "render_text"],
            version="3.2", status="ready"))

    def get(self, key: str) -> Any:
        return self.services.get(key)

    def contract_dicts(self) -> list[dict[str, Any]]:
        out = []
        for c in self.contracts.values():
            if hasattr(c, "model_dump"):
                out.append(c.model_dump())
            elif isinstance(c, dict):
                out.append(c)
            else:
                out.append(dict(c))
        return out

    def health(self) -> dict[str, Any]:
        items = []
        for key, service in self.services.items():
            ok = True
            status = "ready"
            message = "Service registered."
            try:
                if key == "vault":
                    service.initialize()
                    message = "Vault initialized."
                elif key == "fleet_registry":
                    service.summary(service.refresh())
                    message = "Fleet registry refresh successful."
                elif key == "extension_manager":
                    service.passive_health()
                    message = "Extension manager passive health successful."
                elif key == "mission_planner":
                    service.create_plan("Technology Officer service health check.")
                    message = "Mission planner created test plan."
                elif key == "capability_gap_analyzer":
                    planner = self.services.get("mission_planner")
                    plan = planner.create_plan("Technology Officer service health check.") if planner else {}
                    service.analyze_plan(plan)
                    message = "Gap analyzer completed test analysis."
            except Exception as exc:
                ok = False
                status = "error"
                message = str(exc)

            h = self._health(key=key, ok=ok, status=status, message=message, data={})
            if hasattr(h, "model_dump"):
                items.append(h.model_dump())
            elif isinstance(h, dict):
                items.append(h)
            else:
                items.append(dict(h))

        return {"ok": all(x.get("ok") for x in items), "total": len(items), "items": items, "dependency_injector_available": containers is not None}
