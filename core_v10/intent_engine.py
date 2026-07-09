from __future__ import annotations

from dataclasses import dataclass
from typing import Any


INTENT_RULES = [
    {
        "objective": "Understand or investigate code",
        "mission_type": "Engineering Investigation",
        "department": "Engineering",
        "lead_professor": "Professor Ada",
        "required_capabilities": ["code_search", "repo_search", "mission_history"],
        "strong": ["find every place", "where is", "where are", "used", "references", "missionbus", "function", "class", "method"],
        "weak": ["find", "search", "code", "repo", "repository"],
    },
    {
        "objective": "Understand code structure",
        "mission_type": "Engineering Structure Analysis",
        "department": "Engineering",
        "lead_professor": "Professor Ada",
        "required_capabilities": ["code_search", "ast_parse", "symbol_analysis", "mission_history"],
        "strong": ["parse", "ast", "syntax", "structure", "symbol", "classes", "methods"],
        "weak": ["analyze code", "explain code", "how does this work"],
    },
    {
        "objective": "Compare files or folders",
        "mission_type": "Engineering Comparison",
        "department": "Engineering",
        "lead_professor": "Professor Ada",
        "required_capabilities": ["file_compare", "folder_compare", "mission_history"],
        "strong": ["compare", "diff", "difference", "changed", "backup"],
        "weak": ["version", "old", "new", "yesterday", "today"],
    },
    {
        "objective": "Locate files or assets",
        "mission_type": "File Location",
        "department": "Engineering",
        "lead_professor": "Professor Ada",
        "required_capabilities": ["file_search", "mission_history"],
        "strong": ["where did i put", "locate", "find file", "find folder", "gguf", "pdf", "model"],
        "weak": ["file", "folder", "where", "saved"],
    },
    {
        "objective": "Create or develop a story, scene, character, or campaign",
        "mission_type": "Creative Writing",
        "department": "Creative Studio",
        "lead_professor": "Professor Tolkien",
        "required_capabilities": ["creative_writing", "story_memory", "mission_history"],
        "strong": ["novel", "story", "chapter", "character", "scene", "dialogue", "campaign", "dnd", "dm"],
        "weak": ["write", "creative", "plot", "worldbuild"],
    },
    {
        "objective": "Create or design visual media",
        "mission_type": "Creative Design",
        "department": "Creative Studio",
        "lead_professor": "Professor Tolkien",
        "required_capabilities": ["image_generation", "creative_studio", "mission_history"],
        "strong": ["draw", "image", "picture", "logo", "render", "art", "comfyui", "flux"],
        "weak": ["visual", "design", "make me"],
    },
    {
        "objective": "Research or explain knowledge",
        "mission_type": "Knowledge Research",
        "department": "Iron Library",
        "lead_professor": "Professor Sagan",
        "required_capabilities": ["documents", "reference", "mission_history"],
        "strong": ["research", "documentation", "manual", "docs", "source", "reference"],
        "weak": ["explain", "learn", "teach"],
    },
    {
        "objective": "Diagnose or repair a system",
        "mission_type": "System Repair",
        "department": "Repair Bay",
        "lead_professor": "Professor Kayock",
        "required_capabilities": ["diagnostics", "repair", "mission_history"],
        "strong": ["repair", "diagnose", "crash", "broken", "error", "audit", "scan", "fix windows"],
        "weak": ["slow", "issue", "problem"],
    },
    {
        "objective": "Create a reminder, watcher, or repeated task",
        "mission_type": "Automation",
        "department": "Automation",
        "lead_professor": "Operations Director",
        "required_capabilities": ["automation", "watch", "mission_history"],
        "strong": ["remind", "schedule", "monitor", "watch", "every day", "when"],
        "weak": ["later", "repeat", "automatic"],
    },
    {
        "objective": "Conversation, humor, brainstorming, or teaching",
        "mission_type": "General Conversation",
        "department": "Academy",
        "lead_professor": "Professor Kayock",
        "required_capabilities": ["general_reasoning", "mission_history"],
        "strong": ["joke", "funny", "brainstorm", "chat", "talk", "idea"],
        "weak": ["tell me", "what do you think"],
    },
]


@dataclass
class IntentEngine:
    confidence_floor: float = 0.60

    def classify(self, request: str) -> dict[str, Any]:
        text = request.lower().strip()
        scored: list[dict[str, Any]] = []

        for rule in INTENT_RULES:
            strong_hits = [k for k in rule["strong"] if k in text]
            weak_hits = [k for k in rule["weak"] if k in text]

            if not strong_hits and not weak_hits:
                continue

            score = min(0.99, (0.28 * len(strong_hits)) + (0.10 * len(weak_hits)) + 0.45)
            scored.append({
                **{k: rule[k] for k in [
                    "objective", "mission_type", "department", "lead_professor", "required_capabilities"
                ]},
                "confidence": round(score, 2),
                "matched": {
                    "strong": strong_hits,
                    "weak": weak_hits,
                },
            })

        if not scored:
            return {
                "objective": "Conversation or unclear request",
                "mission_type": "General Conversation",
                "department": "Academy",
                "lead_professor": "Professor Kayock",
                "required_capabilities": ["general_reasoning", "mission_history"],
                "confidence": 0.40,
                "matched": {"strong": [], "weak": []},
                "needs_clarification": True,
                "clarification": "I am not fully sure what kind of mission this is.",
            }

        scored.sort(key=lambda x: x["confidence"], reverse=True)
        best = scored[0]
        best["needs_clarification"] = best["confidence"] < self.confidence_floor
        best["alternatives"] = scored[1:4]
        return best
