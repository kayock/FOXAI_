from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass


@dataclass
class LLMEngine:
    api_url: str = "http://127.0.0.1:8080/v1/chat/completions"
    health_url: str = "http://127.0.0.1:8080/health"

    def online(self) -> bool:
        try:
            urllib.request.urlopen(self.health_url, timeout=1.5).read(64)
            return True
        except Exception:
            return False

    def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 768) -> str:
        payload = {
            "model": "local-model",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as res:
            data = json.loads(res.read().decode("utf-8", errors="replace"))
        return data["choices"][0]["message"]["content"].strip()
