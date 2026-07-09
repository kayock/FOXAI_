from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .provider_base import ChatRequest, ChatResponse, BrainProvider
from .mock_provider import MockBrainProvider


@dataclass
class BrainRouter:
    foxai_root: Path
    providers: dict[str, BrainProvider] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.register(MockBrainProvider())

    def register(self, provider: BrainProvider) -> None:
        self.providers[provider.key] = provider

    def list_providers(self) -> list[dict[str, Any]]:
        out = []
        for key, provider in self.providers.items():
            h = provider.health()
            out.append({
                "key": key,
                "name": getattr(provider, "name", key),
                "health": h,
                "models": provider.list_models(),
            })
        return out

    def health(self) -> dict[str, Any]:
        providers = self.list_providers()
        return {
            "ok": any(p["health"].get("ok") for p in providers),
            "providers": providers,
            "default_provider": "mock",
        }

    def choose_provider(self, request: ChatRequest) -> BrainProvider:
        # v3.4 foundation: always use mock provider.
        # Later: choose by department, model availability, mission type, privacy, and offline mode.
        return self.providers["mock"]

    def chat(self, request: ChatRequest) -> ChatResponse:
        provider = self.choose_provider(request)
        return provider.chat(request)
