from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .academy import get_professor
from .llm_engine import LLMEngine
from .memory_engine import MemoryEngine
from .project_manager import ProjectManager


@dataclass
class MissionEngine:
    foxai_root: Path
    project_name: str
    professor_key: str = "fox"
    model_name: str | None = None

    def __post_init__(self) -> None:
        self.projects = ProjectManager(self.foxai_root)
        self.project_path = self.projects.ensure_project(self.project_name)
        self.professor = get_professor(self.professor_key)
        self.memory = MemoryEngine(self.project_path)
        self.memory.ensure()
        self.llm = LLMEngine()

    def build_messages(self, user_text: str) -> list[dict]:
        memory_context = self.memory.build_context(
            professor_name=self.professor.name,
            model_name=self.model_name,
        )

        system_prompt = (
            self.professor.prompt
            + "\n\n"
            + "FOXAI is a portable Star Trek Engineering Console for Makers, Builders, and Explorers. "
            + "Always use supplied Mission Intelligence as authoritative project memory."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": memory_context + "\n\nUSER REQUEST:\n" + user_text},
        ]

    def ask(self, user_text: str) -> dict:
        self.memory.chat("ERIC", user_text)
        self.memory.event("Mission request received")
        if not self.llm.online():
            return {"ok": False, "message": "Local chat engine is offline. Start llama-server first."}

        answer = self.llm.chat(self.build_messages(user_text))
        self.memory.chat(self.professor.name, answer)
        self.memory.event("Professor response recorded")
        return {"ok": True, "answer": answer, "professor": self.professor.name}
