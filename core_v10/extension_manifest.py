from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = {
    "schema": 1,
    "key": "",
    "name": "",
    "callsign": "",
    "department": "General",
    "category": "Utility",
    "priority": 50,
    "portable": True,
    "reserved": False,
    "executables": [],
    "capabilities": [],
    "version": "auto",
    "status": "auto",
    "description": "",
}


def read_manifest(path: Path) -> dict[str, Any]:
    data = dict(DEFAULT_MANIFEST)
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data.update(raw)
        except Exception as exc:
            data["manifest_error"] = str(exc)

    if not data.get("key"):
        data["key"] = path.parent.name.lower().replace(" ", "_")
    if not data.get("name"):
        data["name"] = data["key"]
    if not data.get("callsign"):
        data["callsign"] = data["name"]

    return data


def write_manifest(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT_MANIFEST)
    merged.update(data)
    path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
