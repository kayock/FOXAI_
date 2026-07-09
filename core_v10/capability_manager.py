from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .capability_adapter import CapabilityAdapter


@dataclass
class CapabilityManager:
    foxai_root: Path

    @property
    def capabilities_root(self) -> Path:
        path = self.foxai_root / "Capabilities"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def discover(self) -> dict[str, CapabilityAdapter]:
        adapters: dict[str, CapabilityAdapter] = {}
        for path in sorted(self.capabilities_root.rglob("adapter.json")):
            try:
                adapter = CapabilityAdapter.load(self.foxai_root, path)
                adapters[adapter.key] = adapter
            except Exception as exc:
                print(f"[CapabilityManager] Failed to load {path}: {exc}")
        return adapters

    def list(self) -> list[dict[str, Any]]:
        return [adapter.summary() for adapter in self.discover().values()]

    def get(self, key: str) -> CapabilityAdapter | None:
        return self.discover().get(key)

    def health(self, key: str | None = None) -> dict[str, Any]:
        if key:
            adapter = self.get(key)
            if not adapter:
                return {"ok": False, "message": f"Unknown capability: {key}"}
            return adapter.health()
        items = self.list()
        return {"ok": True, "total": len(items), "installed": sum(1 for x in items if x["installed"]), "reserved": sum(1 for x in items if x["reserved"]), "items": items}

    def launch(self, key: str) -> dict[str, Any]:
        adapter = self.get(key)
        if not adapter:
            return {"ok": False, "message": f"Unknown capability: {key}"}
        return adapter.launch()

    def by_capability(self, capability: str) -> list[dict[str, Any]]:
        cap = capability.lower().strip()
        return [a.summary() for a in self.discover().values() if cap in [c.lower() for c in a.capabilities]]
