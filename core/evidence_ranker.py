from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePath
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class RankingProfile:
    """
    Evidence ranking profile.

    Profiles allow future departments to tune ranking without rewriting
    the Investigation Engine.
    """
    name: str = "default"
    location_weights: Dict[str, int] = field(default_factory=lambda: {
        "core": 100,
        "ui": 95,
        "departments": 90,
        "config": 85,
        "root": 70,
        "Projects": 65,
        "Memory": 55,
        "Library": 50,
        "Mission Archive": 30,
        "Backups": 20,
        "ComfyUI": 5,
        "vendor": 5,
    })
    category_weights: Dict[str, int] = field(default_factory=lambda: {
        "source": 90,
        "config": 80,
        "project_memory": 65,
        "history": 35,
        "vendor": 15,
        "unknown": 25,
    })
    exact_match_bonus: int = 25
    filename_match_bonus: int = 20
    current_source_bonus: int = 15
    backup_penalty: int = -40
    vendor_penalty: int = -60
    history_penalty: int = -25


@dataclass(frozen=True)
class RankedEvidence:
    """
    Evidence plus ranking metadata.

    The original evidence object is intentionally stored as Any so this ranker
    can work with InvestigationEngine.Evidence and future evidence types.
    """
    evidence: Any
    score: int
    reasons: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class EvidenceRanker:
    """
    Evidence Ranker RC1

    Scores and sorts evidence by engineering usefulness.

    This module does not search, read files, call AI, or modify anything.
    It only ranks evidence that was already collected.
    """

    VENDOR_MARKERS = {"ComfyUI", "venv", ".venv", "site-packages", "node_modules"}
    BACKUP_MARKERS = {"Backups", "Backup", "backup", "old", "archive"}
    HISTORY_MARKERS = {"Mission Archive", "MissionArchive", "Archive"}

    def __init__(self, profile: RankingProfile | None = None):
        self.profile = profile or RankingProfile()

    def rank(self, evidence: List[Any], query: str = "", department: str = "") -> List[RankedEvidence]:
        ranked = [self.score(item, query=query, department=department) for item in evidence]
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked

    def score(self, evidence: Any, query: str = "", department: str = "") -> RankedEvidence:
        path = self._get(evidence, "path", "") or ""
        category = self._get(evidence, "category", "unknown") or "unknown"
        confidence = int(self._get(evidence, "confidence", 0) or 0)
        weight = int(self._get(evidence, "weight", 0) or 0)
        snippet = self._get(evidence, "snippet", "") or ""

        score = 0
        reasons: List[str] = []

        location_score, location_reason = self._location_score(path)
        score += location_score
        reasons.append(location_reason)

        category_score = self.profile.category_weights.get(category, self.profile.category_weights["unknown"])
        score += category_score
        reasons.append(f"category '{category}' score {category_score}")

        score += confidence
        reasons.append(f"evidence confidence {confidence}")

        score += weight
        reasons.append(f"evidence weight {weight}")

        exact_bonus = self._exact_match_bonus(query, path, snippet)
        if exact_bonus:
            score += exact_bonus
            reasons.append(f"exact/path match bonus {exact_bonus}")

        if self._is_current_source(path):
            score += self.profile.current_source_bonus
            reasons.append(f"current source bonus {self.profile.current_source_bonus}")

        if self._is_backup(path):
            score += self.profile.backup_penalty
            reasons.append(f"backup penalty {self.profile.backup_penalty}")

        if self._is_vendor(path):
            score += self.profile.vendor_penalty
            reasons.append(f"vendor penalty {self.profile.vendor_penalty}")

        if self._is_history(path):
            score += self.profile.history_penalty
            reasons.append(f"history penalty {self.profile.history_penalty}")

        department_bonus = self._department_bonus(path, department)
        if department_bonus:
            score += department_bonus
            reasons.append(f"department bonus {department_bonus}")

        return RankedEvidence(
            evidence=evidence,
            score=score,
            reasons=reasons,
            metadata={
                "path": path,
                "category": category,
                "department": department,
                "profile": self.profile.name,
            },
        )

    def explain(self, ranked: List[RankedEvidence], limit: int = 8) -> str:
        lines = [
            "EVIDENCE RANKING REPORT",
            "",
            f"Profile: {self.profile.name}",
            f"Evidence Items: {len(ranked)}",
            "",
        ]

        if not ranked:
            lines.append("No evidence to rank.")
            return "\n".join(lines)

        for index, item in enumerate(ranked[:limit], start=1):
            path = item.metadata.get("path", "")
            category = item.metadata.get("category", "unknown")

            lines.append(f"{index}. {path or '[No path]'}")
            lines.append(f"   Score: {item.score}")
            lines.append(f"   Category: {category}")
            lines.append("   Reasons:")
            for reason in item.reasons:
                lines.append(f"   • {reason}")
            lines.append("")

        return "\n".join(lines)

    def _location_score(self, path: str) -> Tuple[int, str]:
        top = self._top_dir(path)

        if not top:
            score = self.profile.location_weights.get("root", 70)
            return score, f"root/unknown location score {score}"

        score = self.profile.location_weights.get(top)

        if score is None:
            if self._is_vendor(path):
                score = self.profile.location_weights.get("vendor", 5)
                return score, f"vendor location score {score}"

            score = 40
            return score, f"unclassified location '{top}' score {score}"

        return score, f"location '{top}' score {score}"

    def _exact_match_bonus(self, query: str, path: str, snippet: str) -> int:
        lowered = (query or "").lower().strip()
        if not lowered:
            return 0

        bonus = 0

        # Use meaningful tokens rather than requiring the whole query.
        tokens = [
            token for token in lowered.replace(",", " ").replace(".", " ").split()
            if len(token) > 3 and token not in {"engineer", "investigate", "where", "what", "that", "this"}
        ]

        path_lower = path.lower()
        snippet_lower = snippet.lower()

        for token in tokens:
            if token in path_lower:
                bonus += self.profile.filename_match_bonus
            elif token in snippet_lower:
                bonus += self.profile.exact_match_bonus // 2

        return min(60, bonus)

    def _department_bonus(self, path: str, department: str) -> int:
        lowered = (department or "").lower()
        path_lower = (path or "").lower()

        if not lowered:
            return 0

        if "engineer" in lowered and (path_lower.startswith("core/") or path_lower.startswith("ui/")):
            return 20

        if "repair" in lowered and any(term in path_lower for term in ["repair", "windows", "diagnostic", "driver"]):
            return 20

        if "comic" in lowered and any(term in path_lower for term in ["comic", "canvas", "story", "character"]):
            return 20

        return 0

    def _top_dir(self, path: str) -> str:
        if not path:
            return ""

        normalized = path.replace("\\", "/")
        parts = [part for part in normalized.split("/") if part]

        if not parts:
            return ""

        return parts[0]

    def _is_vendor(self, path: str) -> bool:
        parts = set(PurePath(path.replace("\\", "/")).parts)
        return bool(parts & self.VENDOR_MARKERS)

    def _is_backup(self, path: str) -> bool:
        parts = set(PurePath(path.replace("\\", "/")).parts)
        return bool(parts & self.BACKUP_MARKERS)

    def _is_history(self, path: str) -> bool:
        normalized = path.replace("\\", "/")
        return any(marker in normalized for marker in self.HISTORY_MARKERS)

    def _is_current_source(self, path: str) -> bool:
        normalized = path.replace("\\", "/")
        if self._is_backup(normalized) or self._is_vendor(normalized) or self._is_history(normalized):
            return False

        return normalized.endswith(".py") and (
            normalized.startswith("core/")
            or normalized.startswith("ui/")
            or normalized.startswith("departments/")
            or "/" not in normalized
        )

    def _get(self, item: Any, name: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(name, default)

        return getattr(item, name, default)
