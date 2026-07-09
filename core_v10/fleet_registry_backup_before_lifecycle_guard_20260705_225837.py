from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .extension_commissioner import commission_known_extensions
from .extension_manager import ExtensionManager


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class FleetRegistry:
    foxai_root: Path

    @property
    def registry_path(self) -> Path:
        path = Path(self.foxai_root) / "Config" / "fleet_registry.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def load(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return {"schema": 1, "updated": None, "shuttles": {}}
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("schema", 1)
                data.setdefault("updated", None)
                data.setdefault("shuttles", {})
                return data
        except Exception:
            pass
        return {"schema": 1, "updated": None, "shuttles": {}}

    def save(self, data: dict[str, Any]) -> None:
        data["updated"] = now()
        self.registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def refresh(self) -> dict[str, Any]:
        manager = ExtensionManager(Path(self.foxai_root))
        health = manager.health()
        old = self.load()
        old_shuttles = old.get("shuttles", {})
        shuttles: dict[str, Any] = {}

        for item in health.get("items", []):
            key = item.get("key")
            h = item.get("health") or {}
            prior = old_shuttles.get(key, {})

            status = h.get("status", "unknown")
            if item.get("reserved"):
                service_state = "Reserved"
            elif status in ("ready", "installed", "online"):
                service_state = "Operational"
            elif status == "missing":
                service_state = "Missing"
            elif status == "offline":
                service_state = "Docked"
            else:
                service_state = "Unknown"

            shuttles[key] = {
                "key": key,
                "name": item.get("name"),
                "callsign": item.get("callsign") or item.get("name"),
                "department": item.get("department", "General"),
                "category": item.get("category", "Utility"),
                "service_state": service_state,
                "installed": bool(item.get("installed")),
                "reserved": bool(item.get("reserved")),
                "health_status": status,
                "health_message": h.get("message"),
                "path": h.get("path") or item.get("path"),
                "capabilities": item.get("capabilities", []),
                "last_seen": now(),
                "last_used": prior.get("last_used"),
                "launches": prior.get("launches", 0),
                "manifest_path": item.get("_manifest_path"),
            }

        data = {"schema": 1, "updated": now(), "shuttles": shuttles}
        self.save(data)
        return data

    def scan_and_commission(self) -> dict[str, Any]:
        commission = commission_known_extensions(Path(self.foxai_root), overwrite=False)
        registry = self.refresh()
        return {
            "ok": True,
            "commission": commission,
            "registry": registry,
            "summary": self.summary(registry),
        }

    def summary(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        data = data or self.load()
        shuttles = list((data.get("shuttles") or {}).values())
        departments: dict[str, list[dict[str, Any]]] = {}

        for shuttle in shuttles:
            departments.setdefault(shuttle.get("department", "General"), []).append(shuttle)

        for dept in departments:
            departments[dept] = sorted(departments[dept], key=lambda x: x.get("callsign", ""))

        states: dict[str, int] = {}
        for shuttle in shuttles:
            state = shuttle.get("service_state", "Unknown")
            states[state] = states.get(state, 0) + 1

        return {
            "ok": True,
            "updated": data.get("updated"),
            "total": len(shuttles),
            "states": states,
            "departments": departments,
        }

    def mark_used(self, key: str) -> dict[str, Any]:
        data = self.load()
        shuttles = data.setdefault("shuttles", {})
        if key not in shuttles:
            return {"ok": False, "message": f"Unknown shuttle pod: {key}"}
        shuttles[key]["last_used"] = now()
        shuttles[key]["launches"] = int(shuttles[key].get("launches", 0)) + 1
        self.save(data)
        return {"ok": True, "shuttle": shuttles[key]}
