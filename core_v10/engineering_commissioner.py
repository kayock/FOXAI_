from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from datetime import datetime
import json

from .department_registry import DepartmentRegistry


@dataclass
class EngineeringCommissioner:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.registry = DepartmentRegistry(self.foxai_root)
        self.outbox = self.foxai_root / "OpsBridge" / "outbox"
        self.outbox.mkdir(parents=True, exist_ok=True)

    def commission(self) -> dict[str, Any]:
        status = self.registry.status()
        engineering = None
        for dept in status.get("departments", []):
            if dept.get("id") == "engineering":
                engineering = dept
                break

        ok = bool(engineering and engineering["validation"]["ok"] and engineering["health"].get("ok"))
        certificate = {
            "ok": ok,
            "certificate": "FOXAI Department Commissioning Certificate",
            "department": "Engineering Department",
            "officer": "Chief Engineer Ada",
            "commission_date": datetime.now().isoformat(timespec="seconds"),
            "status": "ACTIVE" if ok else "NEEDS_ATTENTION",
            "registry_status": status,
        }

        (self.outbox / "engineering_commissioning_certificate.json").write_text(
            json.dumps(certificate, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.outbox / "engineering_commissioning_certificate.txt").write_text(
            self.render_certificate(certificate),
            encoding="utf-8",
        )
        return certificate

    def render_certificate(self, cert: dict[str, Any]) -> str:
        lines = []
        lines.append("=" * 58)
        lines.append("FOXAI COMMAND OS")
        lines.append("Department Commissioning Certificate")
        lines.append("=" * 58)
        lines.append("")
        lines.append(f"Department: {cert.get('department')}")
        lines.append(f"Officer: {cert.get('officer')}")
        lines.append(f"Status: {cert.get('status')}")
        lines.append(f"Commission Date: {cert.get('commission_date')}")
        lines.append("")

        dept = None
        for item in cert.get("registry_status", {}).get("departments", []):
            if item.get("id") == "engineering":
                dept = item
                break

        if dept:
            health = dept.get("health", {})
            lines.append("Services:")
            for svc in health.get("services", []):
                lines.append(f"- {svc}")
            lines.append("")
            lines.append("Tools:")
            for name, item in health.get("tools", {}).items():
                lines.append(f"- {name}: {item.get('status')}")
        else:
            lines.append("Engineering Department was not discovered.")

        lines.append("")
        lines.append("=" * 58)
        return "\n".join(lines)
