from __future__ import annotations

from time import perf_counter
from .provider_base import BrainProvider, ChatRequest, ChatResponse


class MockBrainProvider(BrainProvider):
    key = "mock"
    name = "USS Mock Brain"

    def list_models(self) -> list[str]:
        return ["mock-brain-v1"]

    def health(self) -> dict:
        return {
            "ok": True,
            "provider": self.key,
            "status": "ready",
            "message": "Mock Brain ready. No external model required.",
            "models": self.list_models(),
        }

    def chat(self, request: ChatRequest) -> ChatResponse:
        start = perf_counter()
        professor = request.professor or "Professor Kayock"

        if "joke" in request.prompt.lower() or "toaster" in request.prompt.lower():
            answer = (
                f"{professor}: A toaster joined Starfleet because it wanted to boldly go "
                "where no bread had gone before. It was assigned to the Enterprise's crumb drive."
            )
        elif "missionbus" in request.prompt.lower() or "mission bus" in request.prompt.lower():
            answer = (
                f"{professor}: MissionBus appears to be FOXAI's command-routing layer. "
                "Recommended next step: use USS Search Shuttle for references, USS Syntax Shuttle "
                "for structure, and USS Database Shuttle for mission history."
            )
        else:
            answer = (
                f"{professor}: Mock Brain received the mission. "
                "This confirms the Conversation Shuttle route is operational."
            )

        elapsed = int((perf_counter() - start) * 1000)
        return ChatResponse(
            ok=True,
            answer=answer,
            provider=self.key,
            model="mock-brain-v1",
            elapsed_ms=elapsed,
            tokens_prompt=len(request.prompt.split()),
            tokens_completion=len(answer.split()),
            metadata={"mock": True},
        )
