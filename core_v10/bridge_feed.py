from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from datetime import datetime
import json


@dataclass
class BridgeFeed:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.outbox = self.foxai_root / "OpsBridge" / "outbox"
        self.outbox.mkdir(parents=True, exist_ok=True)

    def read_json(self, name: str) -> dict[str, Any] | None:
        path = self.outbox / name
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return None

    def department_cards(self, department_status: dict[str, Any] | None) -> list[dict[str, Any]]:
        cards = []
        if not department_status:
            return cards

        for dept in department_status.get("departments", []):
            health = dept.get("health", {})
            officer = dept.get("officer", {})
            dept_id = dept.get("id", "unknown")
            cards.append({
                "id": dept_id,
                "title": dept.get("name", dept_id.title()),
                "officer": officer.get("name", "Unknown Officer"),
                "status": health.get("status") or ("ACTIVE" if health.get("ok") else "NEEDS_ATTENTION"),
                "ok": bool(health.get("ok")),
                "accent": {
                    "engineering": "orange",
                    "science": "blue",
                    "academy": "cyan",
                    "creative": "magenta",
                    "security": "red",
                    "communications": "gold",
                }.get(dept_id, "purple"),
                "services": health.get("services", []),
                "tools": health.get("tools", {}),
            })
        return cards

    def build(self) -> dict[str, Any]:
        kernel = self.read_json("kernel_status.json")
        departments = self.read_json("department_registry_status.json")
        engineering = self.read_json("engineering_commissioning_certificate.json")
        captains_log = self.read_json("captains_log.json")
        latest_event = self.read_json("latest_event.json")
        update = self.read_json("update_center_report.json")
        latest_result = self.read_json("latest_result.json")
        hangar = self.read_json("hangar_bay_inventory.json")

        cards = self.department_cards(departments)

        # Ensure Science appears as planned, so the Bridge looks like a living roadmap.
        if not any(card.get("id") == "science" for card in cards):
            cards.append({
                "id": "science",
                "title": "Science Department",
                "officer": "Professor Carl Sagan",
                "status": "PLANNED",
                "ok": False,
                "accent": "blue",
                "services": ["Research Engine", "Evidence Engine", "Knowledge Index", "Iron Library"],
                "tools": {
                    "llamaindex": {"status": "planned"},
                    "iron-library": {"status": "planned"},
                },
            })

        feed = {
            "ok": True,
            "service": "FOXAI Bridge Feed",
            "version": "Operation Bridge Alive v8.0",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "identity": {
                "name": "FOXAI Command OS",
                "subtitle": "Ultimate Edifier Platform",
                "primary_color": "purple",
                "theme": "graphite",
            },
            "kernel": {
                "ok": bool(kernel.get("ok")) if kernel else None,
                "status": "ONLINE" if kernel and kernel.get("ok") else "WAITING",
                "raw": kernel,
            },
            "summary": {
                "department_count": len(cards),
                "departments_online": sum(1 for c in cards if c.get("ok")),
                "captains_log_entries": len((captains_log or {}).get("entries", [])),
                "runtime_packages": (kernel or {}).get("runtime", {}).get("package_count") or (hangar or {}).get("package_count"),
                "latest_event": (latest_event or {}).get("message", ""),
                "latest_mission": (latest_result or {}).get("request", ""),
                "update_status": "READY" if update and update.get("ok") else "WAITING",
            },
            "department_cards": cards,
            "captains_log": captains_log or {"entries": []},
            "latest_event": latest_event,
            "latest_result": latest_result,
            "engineering_certificate": engineering,
            "update_center": update,
        }

        self.write(feed)
        return feed

    def write(self, feed: dict[str, Any]) -> None:
        (self.outbox / "bridge_feed.json").write_text(
            json.dumps(feed, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.outbox / "bridge_feed.txt").write_text(self.render_text(feed), encoding="utf-8")

    def render_text(self, feed: dict[str, Any]) -> str:
        lines = []
        lines.append("FOXAI Bridge Feed")
        lines.append("=================")
        lines.append("")
        lines.append(f"Generated: {feed.get('generated_at')}")
        lines.append(f"Kernel: {feed.get('kernel', {}).get('status')}")
        lines.append(f"Departments: {feed.get('summary', {}).get('department_count')}")
        lines.append(f"Online: {feed.get('summary', {}).get('departments_online')}")
        lines.append("")
        lines.append("Department Cards:")
        for card in feed.get("department_cards", []):
            lines.append(f"- {card.get('title')} [{card.get('status')}] — {card.get('officer')}")
        lines.append("")
        lines.append("Captain's Log:")
        for entry in feed.get("captains_log", {}).get("entries", [])[-5:]:
            lines.append(f"- {entry.get('timestamp')} {entry.get('source')}: {entry.get('message')}")
        return "\n".join(lines)
