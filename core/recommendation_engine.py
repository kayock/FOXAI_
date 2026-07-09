from __future__ import annotations

from typing import Any, List

from core.engineering_assessment import EngineeringAssessment
from core.heuristics import DEFAULT_HEURISTICS, Heuristic, HeuristicMatch


class RecommendationEngine:
    """
    Recommendation Engine RC1

    Converts ranked evidence into a structured EngineeringAssessment.

    This engine does not search, rank, write files, or call AI. It applies
    explicit heuristics so recommendations remain explainable.
    """

    def __init__(self, heuristics: List[Heuristic] | None = None):
        self.heuristics = heuristics or DEFAULT_HEURISTICS

    def assess(
        self,
        mission: Any,
        ranked_evidence: List[Any],
        confidence_report: Any = None,
        gaps: List[Any] | None = None,
    ) -> EngineeringAssessment:
        gaps = gaps or []

        match = self._first_match(mission, ranked_evidence)

        evidence_summary = self._summarize_evidence(ranked_evidence)
        missing_evidence = self._summarize_gaps(gaps)

        confidence = self._combine_confidence(match, confidence_report, ranked_evidence, gaps)

        return EngineeringAssessment(
            finding=match.finding,
            confidence=confidence,
            reasoning=match.reasoning,
            evidence_summary=evidence_summary,
            contradictions=[],
            missing_evidence=missing_evidence,
            suggested_actions=match.suggested_actions,
            alternatives=match.alternatives,
            risk=match.risk,
            impact=match.impact,
            operator_summary=self._operator_summary(match, confidence),
            metadata={
                "heuristic": match.name,
                "heuristic_confidence": match.confidence,
                "evidence_count": len(ranked_evidence),
                "gap_count": len(gaps),
                "heuristic_metadata": match.metadata,
            },
        )

    def _first_match(self, mission: Any, ranked_evidence: List[Any]) -> HeuristicMatch:
        for heuristic in self.heuristics:
            match = heuristic.match(mission, ranked_evidence)
            if match:
                return match

        # DEFAULT_HEURISTICS includes GenericEvidenceHeuristic, so this should rarely happen.
        return HeuristicMatch(
            name="No Heuristic",
            finding="No recommendation heuristic matched.",
            confidence=10,
            reasoning=["No heuristic produced a match."],
            suggested_actions=["Review the evidence manually."],
            risk="unknown",
            impact="unknown",
        )

    def _combine_confidence(
        self,
        match: HeuristicMatch,
        confidence_report: Any,
        ranked_evidence: List[Any],
        gaps: List[Any],
    ) -> int:
        score = match.confidence

        if confidence_report:
            overall = int(getattr(confidence_report, "overall", 0) or 0)
            if overall:
                score = int((score * 0.65) + (overall * 0.35))

        if ranked_evidence:
            top_score = int(getattr(ranked_evidence[0], "score", 0) or 0)
            if top_score >= 350:
                score += 5
            elif top_score < 150:
                score -= 10

        if gaps:
            score -= min(25, len(gaps) * 5)

        return max(0, min(100, score))

    def _summarize_evidence(self, ranked_evidence: List[Any], limit: int = 5) -> List[str]:
        summary = []

        for ranked in ranked_evidence[:limit]:
            evidence = getattr(ranked, "evidence", ranked)
            path = getattr(evidence, "path", "") or getattr(evidence, "source", "unknown source")
            category = getattr(evidence, "category", "unknown")
            score = getattr(ranked, "score", None)

            if score is None:
                summary.append(f"{path} ({category})")
            else:
                summary.append(f"{path} ({category}, rank {score})")

        return summary

    def _summarize_gaps(self, gaps: List[Any]) -> List[str]:
        summary = []

        for gap in gaps:
            expected = getattr(gap, "expected", "")
            reason = getattr(gap, "reason", "")
            if expected and reason:
                summary.append(f"{expected}: {reason}")
            elif expected:
                summary.append(expected)

        return summary

    def _operator_summary(self, match: HeuristicMatch, confidence: int) -> str:
        if confidence >= 80:
            return f"{match.finding} The evidence is strong enough to recommend action."
        if confidence >= 55:
            return f"{match.finding} The evidence is useful but should be reviewed before action."
        return f"{match.finding} Evidence is weak or incomplete; investigate further before acting."
