from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExtensionContext:
    foxai_root: Path

    @property
    def drive_root(self) -> Path:
        return Path(self.foxai_root.anchor)

    @property
    def hangar_bay(self) -> Path:
        return self.drive_root / "Hanger Bay"

    @property
    def extensions(self) -> Path:
        return self.foxai_root / "Extensions"

    @property
    def library(self) -> Path:
        return self.foxai_root / "Library"

    @property
    def models(self) -> Path:
        return self.foxai_root / "Models"

    @property
    def logs(self) -> Path:
        return self.foxai_root / "Logs"

    @property
    def config(self) -> Path:
        return self.foxai_root / "Config"

    def ensure_roots(self) -> None:
        for p in [self.extensions, self.library, self.models, self.logs, self.config]:
            p.mkdir(parents=True, exist_ok=True)

    def executable_inventory(self) -> list[dict[str, Any]]:
        roots = [self.hangar_bay, self.foxai_root / "Engine", self.foxai_root / "ComfyUI"]
        items: list[dict[str, Any]] = []
        seen = set()

        for root in roots:
            if not root.exists():
                continue
            for exe in root.rglob("*.exe"):
                try:
                    real = str(exe.resolve()).lower()
                    if real in seen:
                        continue
                    seen.add(real)
                    st = exe.stat()
                    rel_priority = 100
                    try:
                        exe.relative_to(self.hangar_bay)
                        rel_priority = 10
                    except Exception:
                        pass
                    items.append({
                        "name": exe.name,
                        "stem": exe.stem,
                        "path": str(exe),
                        "folder": str(exe.parent),
                        "size": st.st_size,
                        "priority": rel_priority,
                    })
                except Exception:
                    pass

        return sorted(items, key=lambda x: (x["priority"], x["name"].lower(), x["path"].lower()))

    def find_executable(self, *names: str) -> Path | None:
        wanted = {n.lower() for n in names}
        for item in self.executable_inventory():
            if item["name"].lower() in wanted:
                return Path(item["path"])
        return None

    def find_manifest_executable(self, manifest: dict[str, Any]) -> Path | None:
        names = [str(x) for x in manifest.get("executables", []) if str(x).strip()]
        if not names:
            return None
        return self.find_executable(*names)
