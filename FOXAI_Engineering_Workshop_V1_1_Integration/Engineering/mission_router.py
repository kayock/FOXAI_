from __future__ import annotations

import re
from dataclasses import dataclass

from .models import MissionState, MissionType


@dataclass(slots=True)
class RouteDecision:
    mission_type: MissionType
    authorized: bool
    confidence: int
    reasons: list[str]


_SEARCH = re.compile(r"\b(find|locate|search|where is|show references?|grep)\b", re.I)
_DIAGNOSE = re.compile(r"\b(inspect|diagnose|analy[sz]e|why|determine|review)\b", re.I)
_PLAN = re.compile(r"\b(plan|preview|propose|what would change|do not modify|read[- ]only)\b", re.I)
_IMPLEMENT = re.compile(r"\b(build|implement|create|add|integrate|patch|update|deploy|install feature)\b", re.I)
_REPAIR = re.compile(r"\b(fix|repair|apply|proceed with the approved|execute the approved)\b", re.I)
_AUTH = re.compile(
    r"\b(authoriz(?:e|ed|ation)|approved|proceed|apply|implement|targeted source changes|do not stop at planning)\b",
    re.I,
)
_CONTINUE = re.compile(r"^\s*(continue|proceed|go on|finish it|resume)\s*[.!]?\s*$", re.I)


def classify_mission(text: str, active: MissionState | None = None) -> RouteDecision:
    normalized = text.strip()
    if active is not None and _CONTINUE.match(normalized):
        return RouteDecision(
            mission_type=active.mission_type,
            authorized=active.authorized,
            confidence=100,
            reasons=[f"resuming active mission {active.mission_id} at stage {active.stage}"],
        )

    scores: dict[MissionType, int] = {
        "search": 0,
        "diagnose": 0,
        "plan": 0,
        "implement": 0,
        "repair": 0,
        "unknown": 0,
    }
    reasons: list[str] = []

    for kind, pattern, weight in (
        ("search", _SEARCH, 35),
        ("diagnose", _DIAGNOSE, 30),
        ("plan", _PLAN, 45),
        ("implement", _IMPLEMENT, 60),
        ("repair", _REPAIR, 55),
    ):
        if pattern.search(normalized):
            scores[kind] += weight
            reasons.append(f"{kind} language detected")

    # Explicit implementation authorization should outrank incidental words such as
    # “search” appearing in a long feature description.
    authorized = bool(_AUTH.search(normalized))
    if authorized and scores["implement"]:
        scores["implement"] += 25
        reasons.append("explicit implementation authorization detected")
    if authorized and scores["repair"]:
        scores["repair"] += 20
        reasons.append("explicit repair/application authorization detected")

    if not any(scores[k] for k in ("search", "diagnose", "plan", "implement", "repair")):
        return RouteDecision("unknown", authorized, 20, ["no decisive mission verbs detected"])

    mission_type = max(
        ("search", "diagnose", "plan", "implement", "repair"),
        key=lambda key: scores[key],
    )
    confidence = min(100, max(35, scores[mission_type]))
    return RouteDecision(mission_type, authorized, confidence, reasons)
