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
            manifest.setdefault("kind", "application")
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

    def _service_health(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """
        Run extension_health hooks and arbitrate all matching responses.

        Pluggy calls every registered hook implementation. Generic executable
        plugins may return a matching key with status=missing before a
        specialized service plugin returns status=ready. Therefore we must not
        accept the first matching response blindly.

        Selection priority:
        1. ok=True / ready / installed / online
        2. degraded
        3. offline
        4. error
        5. missing
        """
        results = self.plugin_manager.hook.extension_health(context=self.context, manifest=manifest)
        key = manifest.get("key")
        matches: list[dict[str, Any]] = []

        for result in results:
            if not isinstance(result, dict):
                continue
            if result.get("key") != key:
                continue
            matches.append(result)

        if not matches:
            return {
                "key": key,
                "ok": False,
                "status": "missing",
                "message": "Service has no health handler.",
                "path": f"internal://{key}",
                "health_candidates": [],
                "selected_by": "none",
            }

        def score(item: dict[str, Any]) -> int:
            status = str(item.get("status", "")).lower()
            if item.get("ok") is True:
                return 100
            if status in ("ready", "installed", "online"):
                return 90
            if status == "degraded":
                return 70
            if status == "offline":
                return 50
            if status == "error":
                return 20
            if status == "missing":
                return 10
            return 0

        chosen = sorted(matches, key=score, reverse=True)[0]
        chosen = dict(chosen)
        chosen["health_candidates"] = [
            {
                "ok": m.get("ok"),
                "status": m.get("status"),
                "message": m.get("message"),
                "path": m.get("path"),
            }
            for m in matches
        ]
        chosen["selected_by"] = "extension_health_arbiter"
        return chosen

    def _runtime_metadata(self, manifest: dict[str, Any]) -> dict[str, Any]:
        out = dict(manifest)
        kind = out.get("kind", "application")

        if kind == "service":
            h = self._service_health(manifest)
            installed = bool(h.get("ok"))
            out["installed"] = installed
            out["path"] = h.get("path") or f"internal://{out.get('key')}"
            out["_service_health"] = h
        else:
            exe = self.context.find_manifest_executable(manifest)
            out["installed"] = bool(exe) if not manifest.get("reserved") else False
            out["path"] = str(exe) if exe else manifest.get("path")
            out["_service_health"] = None

        out["shuttle_record"] = {
            "callsign": out.get("callsign") or out.get("name"),
            "department": out.get("department"),
            "health": "reserved" if out.get("reserved") else ("installed" if out.get("installed") else "missing"),
            "capabilities": out.get("capabilities", []),
            "kind": kind,
        }
        return out

    def list_extensions(self) -> list[dict[str, Any]]:
        self.discover_plugins()
        items = [self._runtime_metadata(m) for m in self.manifests.values()]
        return sorted(items, key=lambda x: (x.get("department", ""), int(x.get("priority", 50)), x.get("name", "")))

    def executable_inventory(self) -> list[dict[str, Any]]:
        return self.context.executable_inventory()

    def passive_health(self, key: str | None = None) -> dict[str, Any]:
        self.discover_plugins()
        extensions = self.list_extensions()
        target = [x for x in extensions if (not key or x.get("key") == key)]

        if key and not target:
            return {"ok": False, "message": f"Unknown extension: {key}"}

        def one(ext: dict[str, Any]) -> dict[str, Any]:
            if ext.get("reserved"):
                return {
                    "key": ext.get("key"),
                    "ok": False,
                    "status": "reserved",
                    "message": f"{ext.get('name')} is reserved.",
                    "path": ext.get("path"),
                }

            if ext.get("kind") == "service":
                h = ext.get("_service_health") or {}
                return {
                    "key": ext.get("key"),
                    "ok": bool(h.get("ok")),
                    "status": h.get("status", "ready" if h.get("ok") else "missing"),
                    "message": h.get("message", f"{ext.get('name')} service checked."),
                    "path": h.get("path") or ext.get("path"),
                }

            if ext.get("installed"):
                return {
                    "key": ext.get("key"),
                    "ok": True,
                    "status": "ready",
                    "message": f"{ext.get('name')} found.",
                    "path": ext.get("path"),
                }

            return {
                "key": ext.get("key"),
                "ok": False,
                "status": "missing",
                "message": f"No matching executable found for {ext.get('executables', [])}.",
                "path": ext.get("path"),
            }

        if key:
            return one(target[0])

        return {
            "ok": True,
            "mode": "passive",
            "total": len(extensions),
            "items": [{**ext, "health": one(ext)} for ext in extensions],
        }

    def diagnostic_health(self, key: str | None = None) -> dict[str, Any]:
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
                chosen = self.passive_health(manifest.get("key"))
            health_by_key[manifest["key"]] = chosen

        if key:
            return health_by_key[key]

        return {
            "ok": True,
            "mode": "diagnostic",
            "total": len(extensions),
            "items": [{**ext, "health": health_by_key.get(ext["key"])} for ext in extensions],
        }

    def health(self, key: str | None = None) -> dict[str, Any]:
        return self.passive_health(key)

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

        results = self.plugin_manager.hook.extension_invoke(
            context=self.context,
            manifest=manifest,
            key=key,
            action=action,
            payload=payload or {},
        )

        matches: list[dict[str, Any]] = []
        for result in results:
            if not isinstance(result, dict):
                continue
            if result.get("key") != key:
                continue
            matches.append(result)

        if not matches:
            return {
                "ok": False,
                "key": key,
                "message": f"No invoke handler responded for extension: {key}.{action}",
                "invoke_candidates": [],
                "selected_by": "none",
            }

        def score(item: dict[str, Any]) -> int:
            if item.get("ok") is True:
                return 100
            msg = str(item.get("message", "")).lower()
            status = str(item.get("status", "")).lower()
            if status in ("complete", "ready", "success"):
                return 90
            if "unsupported" in msg or "does not support" in msg or "not implemented" in msg:
                return 5
            return 10

        chosen = sorted(matches, key=score, reverse=True)[0]
        chosen = dict(chosen)
        chosen["invoke_candidates"] = [
            {
                "ok": m.get("ok"),
                "status": m.get("status"),
                "message": m.get("message"),
                "provider": m.get("provider"),
                "model": m.get("model"),
            }
            for m in matches
        ]
        chosen["selected_by"] = "extension_invoke_arbiter"
        return chosen
