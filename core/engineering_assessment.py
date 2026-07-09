from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class EngineeringAssessment:
    """
    Engineering Assessment RC1

    A structured judgment produced from evidence, ranking, and heuristics.

    This object is intentionally department-neutral so Engineer, Repair Bay,
    Comic Forge, Dungeon Master, and future departments can all use it.
    """
    finding: str
    confidence: int
    reasoning: List[str] = field(default_factory=list)
    evidence_summary: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    risk: str = "unknown"
    impact: str = "unknown"
    operator_summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def report(self) -> str:
        lines = [
            "ENGINEERING ASSESSMENT",
            "",
            "Finding:",
            self.finding,
            "",
            "Confidence:",
            f"{self.confidence}%",
            "",
            "Reasoning:",
        ]

        lines.extend(self._bullets(self.reasoning, empty="No reasoning recorded."))

        lines.extend(["", "Evidence Summary:"])
        lines.extend(self._bullets(self.evidence_summary, empty="No evidence summarized."))

        lines.extend(["", "Contradictions:"])
        lines.extend(self._bullets(self.contradictions, empty="None found."))

        lines.extend(["", "Missing Evidence:"])
        lines.extend(self._bullets(self.missing_evidence, empty="None identified."))

        lines.extend(["", "Suggested Actions:"])
        lines.extend(self._bullets(self.suggested_actions, empty="No actions suggested."))

        lines.extend(["", "Alternatives:"])
        lines.extend(self._bullets(self.alternatives, empty="No alternatives recorded."))

        lines.extend([
            "",
            "Risk:",
            self.risk,
            "",
            "Impact:",
            self.impact,
            "",
            "Operator Summary:",
            self.operator_summary or "No operator summary provided.",
        ])

        return "\n".join(lines)

    def _bullets(self, items: List[str], empty: str) -> List[str]:
        if not items:
            return [f"• {empty}"]
        return [f"• {item}" for item in items]
