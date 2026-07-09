from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from .academy.professor_loader import ProfessorLoader
from .brain.brain_router import BrainRouter
from .brain.provider_base import ChatRequest
from .vault import Vault


@dataclass
class ConversationShuttle:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.router = BrainRouter(self.foxai_root)
        self.professors = ProfessorLoader(self.foxai_root)
        self.vault = Vault(self.foxai_root)

    def health(self) -> dict[str, Any]:
        router_health = self.router.health()
        return {
            "ok": router_health.get("ok", False),
            "key": "conversation",
            "callsign": "USS Conversation Shuttle",
            "status": "ready" if router_health.get("ok") else "offline",
            "message": "Conversation Shuttle ready." if router_health.get("ok") else "No brain providers available.",
            "providers": router_health.get("providers", []),
        }

    def chat(self, prompt: str, professor: str = "Professor Kayock", mission_id: int | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        system = self.professors.system_prompt(professor)
        request = ChatRequest(
            prompt=prompt,
            system=system,
            professor=professor,
            mission_id=mission_id,
            metadata=metadata or {},
        )
        response = self.router.chat(request)

        # Vault logging through controlled Vault service.
        self.vault.initialize()
        if mission_id is None:
            mission = self.vault.log_mission(
                title=prompt[:80] or "Conversation mission",
                request=prompt,
                professor=professor,
                mission_type="conversation",
                department=self.professors.load(professor).get("department", "Academy"),
                status="complete" if response.ok else "failed",
            )
            mission_id = mission["mission_id"]

        self.vault.log_event(
            mission_id=mission_id,
            level="INFO" if response.ok else "ERROR",
            source="USS Conversation Shuttle",
            message="Conversation response generated." if response.ok else "Conversation response failed.",
            data=json.dumps({
                "provider": response.provider,
                "model": response.model,
                "elapsed_ms": response.elapsed_ms,
                "tokens_prompt": response.tokens_prompt,
                "tokens_completion": response.tokens_completion,
                "error": response.error,
            }),
        )

        return {
            "ok": response.ok,
            "mission_id": mission_id,
            "answer": response.answer,
            "provider": response.provider,
            "model": response.model,
            "elapsed_ms": response.elapsed_ms,
            "tokens_prompt": response.tokens_prompt,
            "tokens_completion": response.tokens_completion,
            "error": response.error,
        }
