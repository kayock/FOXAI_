from __future__ import annotations

from core.evidence_drivers.base import SmartSearchEvidenceDriver
from core.investigation_engine import Mission


class TimeoutDriver(SmartSearchEvidenceDriver):
    name = "TimeoutDriver"
    domain = "timeout"

    search_terms = [
        "timeout=300",
        "timeout = 300",
        "requests.post",
        "read timeout",
        "HTTPConnectionPool",
        "ChatTimeoutError",
        "request_timeout_seconds",
    ]

    preferred_markers = [
        "core/",
        "ui/",
        "Memory/ui/",
        "FoxAI_Desktop.py",
        "main_window.py",
        "chat",
        "kernel",
    ]

    def can_handle(self, mission: Mission) -> bool:
        lowered = mission.query.lower()
        return any(term in lowered for term in ["timeout", "read timed out", "httpconnectionpool", "slow response"])
