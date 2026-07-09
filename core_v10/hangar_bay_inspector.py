from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import email.parser
import json
import re


@dataclass
class HangarBayInspector:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()

    @property
    def candidates(self) -> list[Path]:
        return [
            self.foxai_root.parent / "Hanger Bay",
            self.foxai_root.parent / "Hangar Bay",
            Path("Z:/Hanger Bay"),
            Path("Z:/Hangar Bay"),
        ]

    def existing_roots(self) -> list[Path]:
        seen = set()
        roots = []
        for p in self.candidates:
            try:
                rp = p.resolve()
            except Exception:
                rp = p
            key = str(rp).lower()
            if p.exists() and key not in seen:
                roots.append(p)
                seen.add(key)
        return roots

    def _normalize(self, name: str) -> str:
        return re.sub(r"[-_.]+", "_", name).lower().strip("_")

    def _read_metadata(self, dist: Path) -> dict[str, str]:
        meta = dist / "METADATA"
        if not meta.exists():
            meta = dist / "PKG-INFO"
        if not meta.exists():
            return {}

        try:
            msg = email.parser.Parser().parsestr(meta.read_text(encoding="utf-8", errors="replace"))
            return {
                "name": msg.get("Name", ""),
                "version": msg.get("Version", ""),
                "summary": msg.get("Summary", ""),
            }
        except Exception:
            return {}

    def _read_top_level(self, dist: Path) -> list[str]:
        top = dist / "top_level.txt"
        if not top.exists():
            return []
        try:
            return [
                line.strip()
                for line in top.read_text(encoding="utf-8", errors="replace").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
        except Exception:
            return []

    def _package_from_dist_name(self, dist: Path) -> str:
        name = dist.name
        for suffix in [".dist-info", ".egg-info"]:
            if name.endswith(suffix):
                name = name[: -len(suffix)]
        # Trim common version suffix if metadata not available.
        # Example: pydantic-2.13.4 -> pydantic
        parts = name.split("-")
        if len(parts) > 1 and any(ch.isdigit() for ch in parts[-1]):
            return "-".join(parts[:-1])
        return name

    def scan(self) -> dict[str, Any]:
        roots = self.existing_roots()
        packages: dict[str, dict[str, Any]] = {}
        import_names: dict[str, dict[str, Any]] = {}
        raw_items = []

        for hb in roots:
            for dist in sorted(list(hb.glob("*.dist-info")) + list(hb.glob("*.egg-info"))):
                meta = self._read_metadata(dist)
                package_name = meta.get("name") or self._package_from_dist_name(dist)
                version = meta.get("version", "")
                summary = meta.get("summary", "")
                top_levels = self._read_top_level(dist)
                if not top_levels:
                    top_levels = [package_name.replace("-", "_")]

                norm = self._normalize(package_name)
                item = {
                    "package": package_name,
                    "normalized": norm,
                    "version": version,
                    "summary": summary,
                    "source": "dist_info",
                    "path": str(dist),
                    "hangar_bay": str(hb),
                    "top_level": top_levels,
                    "import_names": [t.replace("-", "_") for t in top_levels],
                }
                packages[norm] = item
                raw_items.append(item)

                for imp in item["import_names"]:
                    import_names[self._normalize(imp)] = item

            # Also include direct package folders even if dist-info is missing.
            for child in sorted(hb.iterdir()):
                if not child.is_dir():
                    continue
                if child.name.endswith((".dist-info", ".egg-info", "__pycache__")):
                    continue
                init = child / "__init__.py"
                py_files = list(child.glob("*.py"))
                if init.exists() or py_files:
                    norm = self._normalize(child.name)
                    if norm not in import_names:
                        item = {
                            "package": child.name,
                            "normalized": norm,
                            "version": "",
                            "summary": "",
                            "source": "package_folder",
                            "path": str(child),
                            "hangar_bay": str(hb),
                            "top_level": [child.name],
                            "import_names": [child.name],
                        }
                        packages.setdefault(norm, item)
                        import_names[norm] = item
                        raw_items.append(item)

        return {
            "ok": True,
            "roots": [str(r) for r in roots],
            "package_count": len(packages),
            "import_count": len(import_names),
            "packages": packages,
            "imports": import_names,
            "raw_items": raw_items,
        }

    def find(self, aliases: list[str]) -> dict[str, Any] | None:
        inventory = self.scan()
        packages = inventory["packages"]
        imports = inventory["imports"]

        for alias in aliases:
            keys = {
                self._normalize(alias),
                self._normalize(alias.replace("-", "_")),
                self._normalize(alias.replace("_", "-")),
            }
            for key in keys:
                if key in imports:
                    item = dict(imports[key])
                    item["matched_alias"] = alias
                    item["matched_by"] = "import_name"
                    return item
                if key in packages:
                    item = dict(packages[key])
                    item["matched_alias"] = alias
                    item["matched_by"] = "package_name"
                    return item
        return None

    def write_inventory(self) -> dict[str, Any]:
        inventory = self.scan()
        out = self.foxai_root / "OpsBridge" / "outbox"
        out.mkdir(parents=True, exist_ok=True)
        path = out / "hangar_bay_inventory.json"
        path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "path": str(path), "inventory": inventory}

    def render_text(self, inventory: dict[str, Any]) -> str:
        lines = []
        lines.append("FOXAI Hangar Bay Package Inventory")
        lines.append("==================================")
        lines.append("")
        lines.append("Roots:")
        for r in inventory.get("roots", []):
            lines.append(f"- {r}")
        lines.append("")
        lines.append(f"Packages: {inventory.get('package_count')}")
        lines.append(f"Import Names: {inventory.get('import_count')}")
        lines.append("")
        lines.append("Detected Packages:")
        for item in sorted(inventory.get("raw_items", []), key=lambda x: x.get("package", "").lower()):
            version = f" {item.get('version')}" if item.get("version") else ""
            lines.append(f"- {item.get('package')}{version}")
            lines.append(f"  Source: {item.get('source')}")
            lines.append(f"  Imports: {', '.join(item.get('import_names', []))}")
            lines.append(f"  Path: {item.get('path')}")
        return "\\n".join(lines)
