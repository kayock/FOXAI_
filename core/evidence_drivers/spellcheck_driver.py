from __future__ import annotations

from core.evidence_drivers.base import SmartSearchEvidenceDriver
from core.investigation_engine import Mission


class SpellcheckDriver(SmartSearchEvidenceDriver):
    name = "SpellcheckDriver"
    domain = "spellcheck"

    search_terms = [
        "spellcheck",
        "spell check",
        "SpellChecker",
        "Hunspell",
        "en_US",
        "dictionary",
        "misspelled",
        "squiggle",
        "red underline",
        "right-click",
    ]

    preferred_markers = [
        "ui/",
        "Memory/ui/",
        "main_window.py",
        "editor",
        "textbox",
        "input",
        "core/",
    ]

    def can_handle(self, mission: Mission) -> bool:
        lowered = mission.query.lower()
        return any(term in lowered for term in [
            "spellcheck",
            "spell check",
            "spell checker",
            "misspelled",
            "dictionary",
            "squiggle",
        ])
