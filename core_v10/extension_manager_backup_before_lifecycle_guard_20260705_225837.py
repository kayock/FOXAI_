from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pluggy

from .extension_context import ExtensionContext
from .extension_hooks import FoxAIExtensionSpec
from .extension_manifest import read_manifest


@dataclass
class ExtensionManager:
    foxai_root: Path
    plugin_manager: pluggy.PluginManager = field(init=False)
    context: ExtensionContext = field(init=False)
    manifests: dict[str, dict[str, Any]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.context = ExtensionContext(self.foxai_root)
        self.context.ensure_roots()
        self.plugin_manager = pluggy.PluginManager("foxai")
        self.plugin_manager.add_hookspecs(FoxAIExtensionSpec)
        self.discover_plugins()

    @property
    def extensions_root(self) -> Path:
        return self.context.extensions

    def discover_plugins(self) -> None:
        self.manifests = {}

        for manifest_path in sorted(self.extensions_root.rglob("extension.json")):
            manifest = read_manifest(manifest_path)
            manifest["_manifest_path"] = str(manifest_path)
            manifest["_extension_dir"] = str(manifest_path.parent)
            self.manifests[manifest["key"]] = manifest

        for plugin_path in sorted(self.extensions_root.rglob("plugin.py")):
            name = "foxai_ext_" + "_".join(plugin_path.relative_to(self.extensions_root).parts[:-1])
            name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
            if self.plugin_manager.has_plugin(name):
                continue
            try:
                spec = importlib.util.spec_from_file_location(name, plugin_path)
                if not spec or not spec.loader:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
                self.plugin_manager.register(module, name=name)
            except Exception as exc:
                print(f"[ExtensionManager] Failed to load {plugin_path}: {exc}")

    def _runtime_metadata(self, manifest: dict[str, Any]) -> dict[str, Any]:
        exe = self.context.find_manifest_executable(manifest)
        out = dict(manifest)
        out["installed"] = bool(exe) if not manifest.get("reserved") else False
        out["path"] = str(exe) if exe else manifest.get("path")
        out["shuttle_record"] = {
            "callsign": out.get("callsign") or out.get("name"),
            "department": out.get("department"),
            "health": "reserved" if out.get("reserved") else ("installed" if exe else "missing"),
            "capabilities": out.get("capabilities", []),
        }
        return out

    def list_extensions(self) -> list[dict[str, Any]]:
        self.discover_plugins()
        items = [self._runtime_metadata(m) for m in self.manifests.values()]
        return sorted(items, key=lambda x: (x.get("department", ""), int(x.get("priority", 50)), x.get("name", "")))

    def executable_inventory(self) -> list[dict[str, Any]]:
        return self.context.executable_inventory()

    def health(self, key: str | None = None) -> dict[str, Any]:
        self.discover_plugins()
        extensions = self.list_extensions()
        target = [x for x in extensions if (not key or x.get("key") == key)]

        if key and not target:
            return {"ok": False, "message": f"Unknown extension: {key}"}

        health_by_key: dict[str, dict[str, Any]] = {}
        for manifest in target:
            results = self.plugin_manager.hook.extension_health(context=self.context, manifest=manifest)
            chosen = None
            for result in results:
                if isinstance(result, dict) and result.get("key") == manifest.get("key"):
                    chosen = result
                    break
            if not chosen:
                exe = self.context.find_manifest_executable(manifest)
                if manifest.get("reserved"):
                    chosen = {"key": manifest["key"], "ok": False, "status": "reserved", "message": f"{manifest.get('name')} is reserved."}
                elif exe:
                    chosen = {"key": manifest["key"], "ok": True, "status": "installed", "message": f"{manifest.get('name')} executable found.", "path": str(exe)}
                else:
                    chosen = {"key": manifest["key"], "ok": False, "status": "missing", "message": f"No matching executable found for {manifest.get('executables', [])}."}
            health_by_key[manifest["key"]] = chosen

        if key:
            return health_by_key[key]

        return {
            "ok": True,
            "total": len(extensions),
            "items": [{**ext, "health": health_by_key.get(ext["key"])} for ext in extensions],
        }

    def find_capability(self, capability: str) -> list[dict[str, Any]]:
        cap = capability.lower().strip()
        return [
            ext for ext in self.list_extensions()
            if cap in [str(c).lower() for c in ext.get("capabilities", [])]
        ]

    def launch(self, key: str) -> dict[str, Any]:
        manifest = self.manifests.get(key)
        if not manifest:
            self.discover_plugins()
            manifest = self.manifests.get(key)
        if not manifest:
            return {"ok": False, "key": key, "message": f"Unknown extension: {key}"}

        results = self.plugin_manager.hook.extension_launch(context=self.context, manifest=manifest, key=key)
        for result in results:
            if isinstance(result, dict) and result.get("key") == key:
                return result

        return {"ok": False, "key": key, "message": f"No launch handler responded for extension: {key}"}

    def invoke(self, key: str, action: str, payload: dict | None = None) -> dict[str, Any]:
        manifest = self.manifests.get(key)
        if not manifest:
            self.discover_plugins()
            manifest = self.manifests.get(key)
        if not manifest:
            return {"ok": False, "key": key, "message": f"Unknown extension: {key}"}

        results = self.plugin_manager.hook.extension_invoke(context=self.context, manifest=manifest, key=key, action=action, payload=payload or {})
        for result in results:
            if isinstance(result, dict) and result.get("key") == key:
                return result

        return {"ok": False, "key": key, "message": f"No invoke handler responded for extension: {key}.{action}"}
