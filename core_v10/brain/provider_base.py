from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatRequest:
    prompt: str
    system: str = ""
    professor: str = "Professor Kayock"
    mission_id: int | None = None
    temperature: float = 0.7
    max_tokens: int = 1024
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    ok: bool
    answer: str
    provider: str
    model: str
    elapsed_ms: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BrainProvider:
    key = "base"
    name = "Base Provider"

    def initialize(self) -> dict[str, Any]:
        return {"ok": True, "provider": self.key, "message": "Initialized."}

    def health(self) -> dict[str, Any]:
        return {"ok": True, "provider": self.key, "status": "ready", "message": "Ready."}

    def list_models(self) -> list[str]:
        return []

    def chat(self, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError

    def shutdown(self) -> dict[str, Any]:
        return {"ok": True, "provider": self.key, "message": "Shutdown complete."}
