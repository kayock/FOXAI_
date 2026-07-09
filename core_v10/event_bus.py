from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from datetime import datetime
import json
import uuid


EventHandler = Callable[[dict[str, Any]], None]


@dataclass
class EventBus:
    foxai_root: Path
    subscribers: dict[str, list[EventHandler]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.outbox = self.foxai_root / "OpsBridge" / "outbox"
        self.outbox.mkdir(parents=True, exist_ok=True)
        self.events_path = self.outbox / "events.jsonl"

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self.subscribers.setdefault(event_type, []).append(handler)

    def publish(
        self,
        event_type: str,
        source: str,
        message: str,
        payload: dict[str, Any] | None = None,
        severity: str = "info",
        channel: str = "system",
    ) -> dict[str, Any]:
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": event_type,
            "channel": channel,
            "severity": severity,
            "source": source,
            "message": message,
            "payload": payload or {},
        }

        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        self._write_latest(event)

        for handler in self.subscribers.get(event_type, []):
            handler(event)
        for handler in self.subscribers.get("*", []):
            handler(event)

        return event

    def _write_latest(self, event: dict[str, Any]) -> None:
        (self.outbox / "latest_event.json").write_text(
            json.dumps(event, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def read_events(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []

        lines = self.events_path.read_text(encoding="utf-8", errors="replace").splitlines()
        events = []
        for line in lines[-limit:]:
            try:
                events.append(json.loads(line))
            except Exception:
                continue
        return events
