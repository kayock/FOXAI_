from __future__ import annotations

import importlib.util
import inspect
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .extension_context import ExtensionContext
from .extension_manifest import read_manifest
from .fleet_registry import FleetRegistry

try:
    import stevedore
except Exception:
    stevedore = None


HOOK_NAMES = ["extension_health", "extension_launch", "extension_invoke"]


@dataclass
class StevedoreInspector:
    """
    FOXAI Stevedore-style plugin inspector.

    Note:
    Stevedore normally discovers installed Python package entry points.
    FOXAI currently uses portable folder plugins under Extensions/.
    This inspector uses Stevedore concepts while preserving FOXAI's portable layout:
    - discover
    - load
    - inspect hooks
    - run health
    - compare against Fleet Registry

    Later, true stevedore entry point support can be added for packaged .kmod modules.
    """

    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.context = ExtensionContext(self.foxai_root)
        self.extensions_root = self.context.extensions

    def discover_extension_dirs(self) -> list[dict[str, Any]]:
        rows = []
        dirs = sorted({p.parent for p in self.extensions_root.rglob("extension.json")} | {p.parent for p in self.extensions_root.rglob("plugin.py")})

        for d in dirs:
            manifest_path = d / "extension.json"
            plugin_path = d / "plugin.py"
            manifest = None
            error = ""

            if manifest_path.exists():
                try:
                    manifest = read_manifest(manifest_path)
                    manifest.setdefault("kind", "application")
                except Exception as exc:
                    error = str(exc)

            rows.append({
                "dir": str(d),
                "manifest_path": str(manifest_path) if manifest_path.exists() else "",
                "plugin_path": str(plugin_path) if plugin_path.exists() else "",
                "has_manifest": manifest_path.exists(),
                "has_plugin": plugin_path.exists(),
                "key": manifest.get("key") if manifest else "",
                "callsign": (manifest.get("callsign") or manifest.get("name")) if manifest else "",
                "kind": manifest.get("kind") if manifest else "",
                "manifest_error": error,
                "manifest": manifest,
            })

        return rows

    def _module_name(self, plugin_path: Path) -> str:
        try:
            rel = plugin_path.relative_to(self.extensions_root)
            base = "_".join(rel.parts[:-1])
        except Exception:
            base = plugin_path.stem
        return "foxai_stevedore_style_" + "".join(c if c.isalnum() or c == "_" else "_" for c in base)

    def load_plugin(self, plugin_path: Path) -> dict[str, Any]:
        result = {
            "plugin_path": str(plugin_path),
            "module_name": self._module_name(plugin_path),
            "loaded": False,
            "hooks": [],
            "callables": [],
            "error": "",
            "traceback": "",
        }

        try:
            spec = importlib.util.spec_from_file_location(result["module_name"], plugin_path)
            if not spec or not spec.loader:
                raise RuntimeError("Could not create import spec.")

            module = importlib.util.module_from_spec(spec)
            sys.modules[result["module_name"]] = module
            spec.loader.exec_module(module)
            result["loaded"] = True

            for hook in HOOK_NAMES:
                if callable(getattr(module, hook, None)):
                    result["hooks"].append(hook)

            for name, obj in inspect.getmembers(module):
                if callable(obj) and not name.startswith("_"):
                    result["callables"].append(name)

        except Exception as exc:
            result["error"] = str(exc)
            result["traceback"] = traceback.format_exc()

        return result

    def run_raw_health(self, row: dict[str, Any]) -> dict[str, Any]:
        key = row.get("key")
        manifest = row.get("manifest")
        plugin_path = row.get("plugin_path")

        if not manifest:
            return {"ok": False, "key": key, "message": "No readable manifest."}

        if not plugin_path:
            return {"ok": False, "key": key, "message": "No plugin.py found."}

        loaded = self.load_plugin(Path(plugin_path))
        if not loaded["loaded"]:
            return {
                "ok": False,
                "key": key,
                "message": "Plugin import failed.",
                "error": loaded["error"],
                "traceback": loaded["traceback"],
            }

        module = sys.modules.get(loaded["module_name"])
        health_func = getattr(module, "extension_health", None) if module else None
        if not callable(health_func):
            return {"ok": False, "key": key, "message": "No extension_health hook.", "hooks": loaded["hooks"]}

        try:
            health = health_func(context=self.context, manifest=manifest)
            return {
                "ok": isinstance(health, dict) and bool(health.get("ok")),
                "key": key,
                "message": "extension_health executed.",
                "health": health,
            }
        except Exception as exc:
            return {
                "ok": False,
                "key": key,
                "message": "extension_health raised exception.",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    def inspect_all(self) -> dict[str, Any]:
        rows = self.discover_extension_dirs()
        plugins = []
        health = []

        for row in rows:
            if row.get("plugin_path"):
                plugins.append({**row, "load": self.load_plugin(Path(row["plugin_path"]))})
                health.append({**row, "raw_health": self.run_raw_health(row)})
            else:
                plugins.append({**row, "load": None})
                health.append({**row, "raw_health": {"ok": False, "message": "No plugin.py"}})

        fleet = FleetRegistry(self.foxai_root)
        fleet_data = fleet.refresh()
        fleet_summary = fleet.summary(fleet_data)

        comparison = []
        for row in rows:
            key = row.get("key")
            fleet_item = (fleet_data.get("shuttles") or {}).get(key, {})
            raw = next((h.get("raw_health") for h in health if h.get("key") == key), {})
            comparison.append({
                "key": key,
                "callsign": row.get("callsign"),
                "kind": row.get("kind"),
                "raw_health_ok": raw.get("ok"),
                "raw_health_status": (raw.get("health") or {}).get("status") if isinstance(raw.get("health"), dict) else "",
                "fleet_state": fleet_item.get("service_state"),
                "fleet_health_status": fleet_item.get("health_status"),
                "fleet_health_message": fleet_item.get("health_message"),
                "matches": bool(raw.get("ok")) == (fleet_item.get("service_state") == "Operational"),
            })

        return {
            "ok": True,
            "stevedore_importable": stevedore is not None,
            "extensions_root": str(self.extensions_root),
            "extension_count": len(rows),
            "plugin_count": sum(1 for r in rows if r.get("plugin_path")),
            "loaded_count": sum(1 for p in plugins if p.get("load") and p["load"].get("loaded")),
            "failed_count": sum(1 for p in plugins if p.get("load") and not p["load"].get("loaded")),
            "rows": rows,
            "plugins": plugins,
            "health": health,
            "fleet_summary": fleet_summary,
            "comparison": comparison,
        }
