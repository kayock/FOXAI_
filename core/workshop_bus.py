from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Any
import traceback


@dataclass
class WorkshopEvent:
    """
    A single Workshop Bus event.
    """
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class WorkshopBus:
    """
    Workshop Bus RC1

    The Workshop's nervous system.

    Departments should publish events instead of calling each other directly.

    Example:
        bus.publish("MISSION_STARTED", {"mission": "Engineer"}, source="Engineer")

    Subscribers receive WorkshopEvent objects.
    """

    MISSION_STARTED = "MISSION_STARTED"
    MISSION_PROGRESS = "MISSION_PROGRESS"
    MISSION_HEARTBEAT = "MISSION_HEARTBEAT"
    MISSION_COMPLETED = "MISSION_COMPLETED"
    MISSION_FAILED = "MISSION_FAILED"
    MISSION_CANCELLED = "MISSION_CANCELLED"

    INVESTIGATION_STARTED = "INVESTIGATION_STARTED"
    INVESTIGATION_STEP = "INVESTIGATION_STEP"
    INVESTIGATION_COMPLETED = "INVESTIGATION_COMPLETED"

    PROJECT_OPENED = "PROJECT_OPENED"
    DECISION_CHISELED = "DECISION_CHISELED"
    LESSON_RECORDED = "LESSON_RECORDED"
    FORGE_ENTRY_RECORDED = "FORGE_ENTRY_RECORDED"

    DEPARTMENT_LOADED = "DEPARTMENT_LOADED"
    DEPARTMENT_UNLOADED = "DEPARTMENT_UNLOADED"

    def __init__(self, keep_history=True, max_history=500):
        self.keep_history = keep_history
        self.max_history = max_history
        self.subscribers: Dict[str, List[Callable[[WorkshopEvent], None]]] = {}
        self.history: List[WorkshopEvent] = []
        self.errors: List[Dict[str, str]] = []

    def subscribe(self, event_type: str, handler: Callable[[WorkshopEvent], None]):
        """
        Subscribe a handler to an event type.

        Use "*" to receive all events.
        """
        self.subscribers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[WorkshopEvent], None]):
        handlers = self.subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event_type: str, payload=None, source="unknown"):
        """
        Publish an event to subscribers.

        Subscriber failures are isolated and recorded.
        One bad subscriber must not crash the Workshop Bus.
        """
        event = WorkshopEvent(
            event_type=event_type,
            payload=payload or {},
            source=source,
        )

        if self.keep_history:
            self.history.append(event)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

        handlers = []
        handlers.extend(self.subscribers.get(event_type, []))
        handlers.extend(self.subscribers.get("*", []))

        for handler in handlers:
            try:
                handler(event)
            except Exception as error:
                self.errors.append({
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "event_type": event_type,
                    "handler": getattr(handler, "__name__", str(handler)),
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                })

        return event

    def recent_events(self, limit=25):
        return self.history[-limit:]

    def recent_errors(self, limit=10):
        return self.errors[-limit:]

    def report(self):
        lines = [
            "WORKSHOP BUS REPORT",
            "",
            f"Subscribers: {sum(len(v) for v in self.subscribers.values())}",
            f"Event Types Subscribed: {len(self.subscribers)}",
            f"Events Stored: {len(self.history)}",
            f"Subscriber Errors: {len(self.errors)}",
            "",
            "Recent Events:",
        ]

        for event in self.recent_events(10):
            lines.append(
                f"• {event.timestamp} | {event.event_type} | source={event.source}"
            )

        if not self.history:
            lines.append("• No events recorded yet.")

        if self.errors:
            lines.extend([
                "",
                "Recent Subscriber Errors:",
            ])
            for error in self.recent_errors(5):
                lines.append(
                    f"• {error['timestamp']} | {error['event_type']} | {error['error']}"
                )

        lines.extend([
            "",
            "Safety Status:",
            "Workshop Bus dispatches events only. It does not execute mission logic by itself.",
        ])

        return "\n".join(lines)


_bus = None


def get_bus():
    """
    Shared Workshop Bus singleton.
    """
    global _bus
    if _bus is None:
        _bus = WorkshopBus()
    return _bus
