from __future__ import annotations

from core.evidence_drivers.base import SmartSearchEvidenceDriver
from core.investigation_engine import Mission


class ContextMenuDriver(SmartSearchEvidenceDriver):
    name = "ContextMenuDriver"
    domain = "context_menu"

    search_terms = [
        "bind(\"<Button-3>\"",
        "bind('<Button-3>'",
        "<Button-3>",
        "<ButtonRelease-3>",
        "tk.Menu",
        "context menu",
        "right-click",
        "right click",
        "CTkTextbox",
        "event_generate",
        "input_box",
        "chat_box",
        "popup menu",
    ]

    preferred_markers = [
        "ui/",
        "Memory/ui/",
        "main_window.py",
        "widgets",
        "textbox",
        "input",
        "chat",
        "core/",
    ]

    def can_handle(self, mission: Mission) -> bool:
        lowered = mission.query.lower()
        return any(term in lowered for term in [
            "right click",
            "right-click",
            "context menu",
            "mouse menu",
            "popup menu",
            "menu not appearing",
            "button-3",
        ])
