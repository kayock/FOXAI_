from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CapabilityAdapter:
    root: Path
    adapter_path: Path
    data: dict[str, Any]

    @classmethod
    def load(cls, root: Path, adapter_path: Path) -> "CapabilityAdapter":
        data = json.loads(adapter_path.read_text(encoding="utf-8"))
        return cls(root=root, adapter_path=adapter_path, data=data)

    @property
    def key(self) -> str:
        return self.data.get("key", self.adapter_path.parent.name)

    @property
    def name(self) -> str:
        return self.data.get("name", self.key)

    @property
    def reserved(self) -> bool:
        return bool(self.data.get("reserved", False))

    @property
    def category(self) -> str:
        return self.data.get("category", "General")

    @property
    def capabilities(self) -> list[str]:
        return list(self.data.get("capabilities", []))

    def executable_path(self) -> Path | None:
        raw = self.data.get("path")
        if not raw:
            return None
        raw = str(raw).replace("%FOXAI_ROOT%", str(self.root))
        return Path(raw)

    @property
    def installed(self) -> bool:
        if self.reserved:
            return False
        path = self.executable_path()
        return path.exists() if path else bool(self.data.get("installed", False))

    def health(self) -> dict[str, Any]:
        if self.reserved:
            return {"ok": False, "status": "reserved", "message": f"{self.name} is reserved but not installed yet."}
        path = self.executable_path()
        if path and not path.exists():
            return {"ok": False, "status": "missing", "message": f"Executable/path not found: {path}"}
        url = self.data.get("health_url")
        if url:
            try:
                urllib.request.urlopen(url, timeout=1.5).read(64)
                return {"ok": True, "status": "online", "message": f"{self.name} is online."}
            except Exception:
                return {"ok": False, "status": "offline", "message": f"{self.name} is installed but not responding."}
        if path and path.exists():
            return {"ok": True, "status": "installed", "message": f"{self.name} is installed."}
        return {"ok": False, "status": "unknown", "message": "No health check configured."}

    def launch(self) -> dict[str, Any]:
        if self.reserved:
            return {"ok": False, "message": f"{self.name} is reserved but not installed yet."}
        path = self.executable_path()
        if not path or not path.exists():
            return {"ok": False, "message": f"Cannot launch. Executable/path not found: {path}"}
        if path.is_dir():
            return {"ok": False, "message": f"{self.name} is a folder capability, not a launchable app."}
        args = self.data.get("args", [])
        cwd_raw = self.data.get("cwd")
        cwd = Path(str(cwd_raw).replace("%FOXAI_ROOT%", str(self.root))) if cwd_raw else path.parent
        try:
            subprocess.Popen([str(path), *args], cwd=str(cwd))
            return {"ok": True, "message": f"Launched {self.name}."}
        except Exception as exc:
            return {"ok": False, "message": f"Launch failed for {self.name}: {exc}"}

    def summary(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "installed": self.installed,
            "reserved": self.reserved,
            "capabilities": self.capabilities,
            "health": self.health(),
            "path": str(self.executable_path()) if self.executable_path() else None,
        }
