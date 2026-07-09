from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import importlib
import json
import sys


@dataclass
class DepartmentRegistry:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.departments_root = self.foxai_root / "Departments"
        if str(self.foxai_root) not in sys.path:
            sys.path.insert(0, str(self.foxai_root))

    def discover(self) -> list[dict[str, Any]]:
        found = []
        if not self.departments_root.exists():
            return found

        for manifest_path in sorted(self.departments_root.glob("*/manifest.json")):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["_manifest_path"] = str(manifest_path)
                manifest["_department_path"] = str(manifest_path.parent)
                found.append(manifest)
            except Exception as exc:
                found.append({
                    "ok": False,
                    "id": manifest_path.parent.name,
                    "_manifest_path": str(manifest_path),
                    "error": str(exc),
                })
        return found

    def validate_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        required = ["api_version", "id", "name", "officer", "provides", "services", "tools", "health_check"]
        missing = [key for key in required if key not in manifest]
        return {
            "ok": not missing,
            "id": manifest.get("id"),
            "missing": missing,
        }

    def run_health(self, manifest: dict[str, Any]) -> dict[str, Any]:
        health_ref = manifest.get("health_check", "")
        if ":" not in health_ref:
            return {"ok": False, "message": "Invalid health_check reference.", "health_check": health_ref}

        module_name, func_name = health_ref.split(":", 1)
        try:
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            return func(self.foxai_root)
        except Exception as exc:
            return {
                "ok": False,
                "message": str(exc),
                "health_check": health_ref,
            }

    def status(self) -> dict[str, Any]:
        departments = []
        for manifest in self.discover():
            validation = self.validate_manifest(manifest)
            health = self.run_health(manifest) if validation["ok"] else {"ok": False, "message": "Manifest invalid."}
            departments.append({
                "id": manifest.get("id"),
                "name": manifest.get("name"),
                "officer": manifest.get("officer", {}),
                "validation": validation,
                "health": health,
                "manifest": manifest,
            })

        return {
            "ok": all(d["validation"]["ok"] and d["health"].get("ok") for d in departments),
            "department_count": len(departments),
            "departments": departments,
        }
