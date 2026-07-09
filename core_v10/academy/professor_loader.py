from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALIASES = {
    "professor ada": "ada",
    "ada": "ada",
    "professor kayock": "kayock",
    "kayock": "kayock",
    "professor tolkien": "tolkien",
    "tolkien": "tolkien",
    "professor sagan": "sagan",
    "sagan": "sagan",
    "professor asimov": "asimov",
    "asimov": "asimov",
}


@dataclass
class ProfessorLoader:
    foxai_root: Path

    @property
    def prompts_root(self) -> Path:
        return Path(self.foxai_root) / "core_v10" / "academy" / "prompts"

    def resolve_key(self, name: str | None) -> str:
        if not name:
            return "kayock"
        return ALIASES.get(name.strip().lower(), "kayock")

    def load(self, name: str | None) -> dict[str, Any]:
        key = self.resolve_key(name)
        path = self.prompts_root / f"{key}.json"
        if not path.exists():
            return {
                "name": "Professor Kayock",
                "department": "Academy",
                "tone": "Practical",
                "goals": ["Clarity"],
                "system": "You are Professor Kayock."
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def system_prompt(self, name: str | None) -> str:
        profile = self.load(name)
        goals = ", ".join(profile.get("goals", []))
        return (
            f"{profile.get('system', '')}\n"
            f"Department: {profile.get('department', '')}\n"
            f"Tone: {profile.get('tone', '')}\n"
            f"Goals: {goals}\n"
        )
