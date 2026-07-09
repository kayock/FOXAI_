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


HOOK_NAMES = ["extension_health", "extension_launch", "extension_invoke"]


@dataclass
class PluginDiagnostics:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.context = ExtensionContext(self.foxai_root)
        self.extensions_root = self.context.extensions

    def discover(self) -> dict[str, Any]:
        manifests = []
        plugins = []
        by_dir: dict[str, dict[str, Any]] = {}

        for manifest_path in sorted(self.extensions_root.rglob("extension.json")):
            try:
                manifest = read_manifest(manifest_path)
                manifest.setdefault("kind", "application")
                item = {
                    "path": str(manifest_path),
                    "dir": str(manifest_path.parent),
                    "key": manifest.get("key"),
                    "callsign": manifest.get("callsign") or manifest.get("name"),
                    "kind": manifest.get("kind", "application"),
                    "capabilities": manifest.get("capabilities", []),
                    "ok": True,
                    "error": "",
                }
            except Exception as exc:
                item = {
                    "path": str(manifest_path),
                    "dir": str(manifest_path.parent),
                    "key": "",
                    "callsign": "",
                    "kind": "",
                    "capabilities": [],
                    "ok": False,
                    "error": str(exc),
                }
            manifests.append(item)
            by_dir.setdefault(item["dir"], {})["manifest"] = item

        for plugin_path in sorted(self.extensions_root.rglob("plugin.py")):
            item = {
                "path": str(plugin_path),
                "dir": str(plugin_path.parent),
                "loaded": False,
                "module_name": self._module_name(plugin_path),
                "hooks": [],
                "error": "",
                "traceback": "",
            }
            plugins.append(item)
            by_dir.setdefault(item["dir"], {})["plugin"] = item

        pairs = []
        for d, items in sorted(by_dir.items()):
            pairs.append({
                "dir": d,
                "has_manifest": "manifest" in items,
                "has_plugin": "plugin" in items,
                "manifest": items.get("manifest"),
                "plugin": items.get("plugin"),
            })

        return {
            "ok": True,
            "extensions_root": str(self.extensions_root),
            "manifest_count": len(manifests),
            "plugin_count": len(plugins),
            "manifests": manifests,
            "plugins": plugins,
            "pairs": pairs,
        }

    def _module_name(self, plugin_path: Path) -> str:
        try:
            rel_parts = plugin_path.relative_to(self.extensions_root).parts[:-1]
        except Exception:
            rel_parts = plugin_path.parts[-3:-1]
        name = "foxai_diag_" + "_".join(rel_parts)
        return "".join(c if c.isalnum() or c == "_" else "_" for c in name)

    def load_plugin_file(self, plugin_path: Path) -> dict[str, Any]:
        item = {
            "path": str(plugin_path),
            "module_name": self._module_name(plugin_path),
            "loaded": False,
            "hooks": [],
            "error": "",
            "traceback": "",
            "callables": [],
        }

        try:
            spec = importlib.util.spec_from_file_location(item["module_name"], plugin_path)
            if not spec or not spec.loader:
                raise RuntimeError("Could not create import spec.")

            module = importlib.util.module_from_spec(spec)
            sys.modules[item["module_name"]] = module
            spec.loader.exec_module(module)

            item["loaded"] = True
            for name in HOOK_NAMES:
                obj = getattr(module, name, None)
                if callable(obj):
                    item["hooks"].append(name)

            for name, obj in inspect.getmembers(module):
                if callable(obj) and not name.startswith("_"):
                    item["callables"].append(name)

        except Exception as exc:
            item["error"] = str(exc)
            item["traceback"] = traceback.format_exc()

        return item

    def load_all_plugins(self) -> dict[str, Any]:
        discovery = self.discover()
        loaded = []
        for plugin in discovery["plugins"]:
            loaded.append(self.load_plugin_file(Path(plugin["path"])))

        return {
            "ok": all(p["loaded"] for p in loaded),
            "total": len(loaded),
            "loaded_count": sum(1 for p in loaded if p["loaded"]),
            "failed_count": sum(1 for p in loaded if not p["loaded"]),
            "plugins": loaded,
        }

    def raw_service_health(self, key: str = "conversation") -> dict[str, Any]:
        discovery = self.discover()

        target_pair = None
        for pair in discovery["pairs"]:
            manifest = pair.get("manifest") or {}
            if manifest.get("key") == key:
                target_pair = pair
                break

        if not target_pair:
            return {"ok": False, "key": key, "message": "No manifest found for key."}

        manifest_path = Path(target_pair["manifest"]["path"])
        manifest = read_manifest(manifest_path)
        manifest.setdefault("kind", "application")

        plugin = target_pair.get("plugin")
        if not plugin:
            return {
                "ok": False,
                "key": key,
                "manifest": str(manifest_path),
                "message": "Manifest found but no plugin.py found beside it.",
            }

        loaded = self.load_plugin_file(Path(plugin["path"]))
        if not loaded["loaded"]:
            return {
                "ok": False,
                "key": key,
                "manifest": str(manifest_path),
                "plugin": plugin["path"],
                "message": "Plugin import failed.",
                "error": loaded["error"],
                "traceback": loaded["traceback"],
            }

        module = sys.modules.get(loaded["module_name"])
        func = getattr(module, "extension_health", None) if module else None
        if not callable(func):
            return {
                "ok": False,
                "key": key,
                "manifest": str(manifest_path),
                "plugin": plugin["path"],
                "message": "Plugin loaded but extension_health hook is missing.",
                "hooks": loaded["hooks"],
            }

        try:
            result = func(context=self.context, manifest=manifest)
            return {
                "ok": isinstance(result, dict) and bool(result.get("ok")),
                "key": key,
                "manifest": str(manifest_path),
                "plugin": plugin["path"],
                "message": "Raw extension_health executed.",
                "result": result,
            }
        except Exception as exc:
            return {
                "ok": False,
                "key": key,
                "manifest": str(manifest_path),
                "plugin": plugin["path"],
                "message": "extension_health raised exception.",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    def report(self, service_key: str = "conversation") -> dict[str, Any]:
        discovery = self.discover()
        loading = self.load_all_plugins()
        raw = self.raw_service_health(service_key)

        return {
            "ok": loading.get("ok", False) and raw.get("ok", False),
            "service_key": service_key,
            "discovery": discovery,
            "loading": loading,
            "raw_service_health": raw,
        }
