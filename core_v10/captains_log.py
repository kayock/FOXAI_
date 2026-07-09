from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


@dataclass
class CaptainsLog:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.outbox = self.foxai_root / "OpsBridge" / "outbox"
        self.outbox.mkdir(parents=True, exist_ok=True)
        self.events_path = self.outbox / "events.jsonl"
        self.log_json = self.outbox / "captains_log.json"
        self.log_txt = self.outbox / "captains_log.txt"

    def event_to_entry(self, event: dict[str, Any]) -> dict[str, Any]:
        return {
            "timestamp": event.get("timestamp"),
            "source": event.get("source"),
            "severity": event.get("severity", "info"),
            "type": event.get("type"),
            "message": event.get("message"),
            "payload": event.get("payload", {}),
        }

    def build(self, limit: int = 25) -> dict[str, Any]:
        events = []
        if self.events_path.exists():
            for line in self.events_path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue

        entries = [self.event_to_entry(e) for e in events[-limit:]]
        report = {
            "ok": True,
            "service": "Captain's Log",
            "entry_count": len(entries),
            "entries": entries,
        }

        self.log_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log_txt.write_text(self.render_text(report), encoding="utf-8")
        return report

    def render_text(self, report: dict[str, Any]) -> str:
        lines = []
        lines.append("Captain's Log")
        lines.append("=============")
        lines.append("")
        if not report.get("entries"):
            lines.append("No entries yet.")
            return "\n".join(lines)

        for entry in report.get("entries", []):
            lines.append(f"{entry.get('timestamp')} — {entry.get('source')}")
            lines.append(f"[{entry.get('severity')}] {entry.get('message')}")
            lines.append("")
        return "\n".join(lines)
