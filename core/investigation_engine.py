from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass(frozen=True)
class Mission:
    """
    A structured investigation request.

    Departments create Missions instead of passing raw strings into the
    Investigation Engine.
    """
    id: str
    department: str
    intent: str
    query: str
    priority: str = "normal"
    requested_drivers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @classmethod
    def create(
        cls,
        department: str,
        intent: str,
        query: str,
        priority: str = "normal",
        requested_drivers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Mission":
        return cls(
            id=f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:8]}",
            department=department,
            intent=intent,
            query=query,
            priority=priority,
            requested_drivers=requested_drivers or [],
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class Evidence:
    """
    A single piece of structured evidence.
    """
    source: str
    category: str
    path: str = ""
    snippet: str = ""
    confidence: int = 0
    weight: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceGap:
    """
    Expected evidence that was not found or not checked.
    """
    expected: str
    reason: str
    impact: str = "unknown"
    suggested_driver: str = ""


@dataclass(frozen=True)
class ConfidenceReport:
    """
    Explainable confidence summary for an investigation.
    """
    evidence_quality: int = 0
    coverage: int = 0
    agreement: int = 0
    overall: int = 0
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class InvestigationResult:
    """
    Final structured result returned by the Investigation Engine.
    """
    mission: Mission
    evidence: List[Evidence]
    gaps: List[EvidenceGap]
    confidence: ConfidenceReport
    recommendation: str
    risk: str
    alternatives: List[str]
    next_step: str
    timeline: List[str]
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class EvidenceDriver(ABC):
    """
    Abstract evidence driver contract.

    Future drivers may inspect source code, configuration, project memory,
    mission history, Windows logs, images, video, or other evidence sources.
    """

    name = "EvidenceDriver"

    @abstractmethod
    def collect(self, mission: Mission) -> List[Evidence]:
        """Collect evidence for a Mission."""
        raise NotImplementedError


class InvestigationEngine:
    """
    FOXAI Investigation Engine RC1

    Kernel-grade reasoning pipeline skeleton.

    RC1 intentionally contains no SmartSearch integration, filesystem scanning,
    AI calls, web access, Windows APIs, threading, async, or caching.
    """

    def __init__(self, kernel=None, drivers: Optional[List[EvidenceDriver]] = None):
        self.kernel = kernel
        self.drivers = drivers or []

    def investigate(self, mission: Mission) -> InvestigationResult:
        """
        Run the investigation pipeline and return an InvestigationResult.
        """
        started = perf_counter()
        timeline: List[str] = []

        self._publish("MISSION_STARTED", {
            "mission_id": mission.id,
            "department": mission.department,
            "intent": mission.intent,
        })

        timeline.append(self._stamp("Mission received"))

        plan = self._plan(mission, timeline)
        evidence = self._collect(mission, plan, timeline)
        gaps = self._analyze_gaps(mission, plan, evidence, timeline)
        confidence = self._build_confidence(mission, evidence, gaps, timeline)
        recommendation, risk, alternatives, next_step = self._build_recommendation(
            mission,
            evidence,
            gaps,
            confidence,
            timeline,
        )

        result = self._build_result(
            mission=mission,
            evidence=evidence,
            gaps=gaps,
            confidence=confidence,
            recommendation=recommendation,
            risk=risk,
            alternatives=alternatives,
            next_step=next_step,
            timeline=timeline,
            duration=perf_counter() - started,
            metadata={"plan": plan},
        )

        self._publish("MISSION_COMPLETED", {
            "mission_id": mission.id,
            "department": mission.department,
            "intent": mission.intent,
            "duration": result.duration,
        })

        return result

    def _plan(self, mission: Mission, timeline: List[str]) -> Dict[str, Any]:
        timeline.append(self._stamp("Plan created"))

        return {
            "requested_drivers": mission.requested_drivers,
            "driver_count": len(self.drivers),
            "rc1_scope": "skeleton_only",
        }

    def _collect(
        self,
        mission: Mission,
        plan: Dict[str, Any],
        timeline: List[str],
    ) -> List[Evidence]:
        timeline.append(self._stamp("Evidence collection started"))

        evidence: List[Evidence] = []

        for driver in self.drivers:
            collected = driver.collect(mission)
            evidence.extend(collected)

        timeline.append(self._stamp(f"Evidence collection completed: {len(evidence)} items"))
        return evidence

    def _analyze_gaps(
        self,
        mission: Mission,
        plan: Dict[str, Any],
        evidence: List[Evidence],
        timeline: List[str],
    ) -> List[EvidenceGap]:
        timeline.append(self._stamp("Gap analysis completed"))

        # RC1 skeleton: no required gaps until real drivers define expectations.
        return []

    def _build_confidence(
        self,
        mission: Mission,
        evidence: List[Evidence],
        gaps: List[EvidenceGap],
        timeline: List[str],
    ) -> ConfidenceReport:
        timeline.append(self._stamp("Confidence report built"))

        if not evidence:
            return ConfidenceReport(
                evidence_quality=0,
                coverage=0,
                agreement=0,
                overall=0,
                notes=["RC1 skeleton: no evidence drivers produced evidence."],
            )

        average_quality = int(sum(item.confidence for item in evidence) / len(evidence))
        average_weight = int(sum(item.weight for item in evidence) / len(evidence))

        return ConfidenceReport(
            evidence_quality=average_quality,
            coverage=min(100, len(evidence) * 10),
            agreement=average_weight,
            overall=int((average_quality + min(100, len(evidence) * 10) + average_weight) / 3),
            notes=["Confidence is provisional until RC2 evidence drivers are integrated."],
        )

    def _build_recommendation(
        self,
        mission: Mission,
        evidence: List[Evidence],
        gaps: List[EvidenceGap],
        confidence: ConfidenceReport,
        timeline: List[str],
    ) -> tuple[str, str, List[str], str]:
        timeline.append(self._stamp("Recommendation built"))

        if not evidence:
            return (
                "Investigation Engine RC1 completed the pipeline. No evidence was collected because no evidence drivers are active yet.",
                "low",
                ["Add SourceCodeDriver in RC2.", "Integrate SmartSearch as an evidence driver."],
                "Implement the first EvidenceDriver and rerun this mission.",
            )

        return (
            "Evidence was collected. Review the structured evidence list before taking action.",
            "medium",
            ["Collect additional evidence with more drivers."],
            "Review evidence and proceed with a department-specific recommendation.",
        )

    def _build_result(
        self,
        mission: Mission,
        evidence: List[Evidence],
        gaps: List[EvidenceGap],
        confidence: ConfidenceReport,
        recommendation: str,
        risk: str,
        alternatives: List[str],
        next_step: str,
        timeline: List[str],
        duration: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> InvestigationResult:
        timeline.append(self._stamp("Investigation result assembled"))

        return InvestigationResult(
            mission=mission,
            evidence=evidence,
            gaps=gaps,
            confidence=confidence,
            recommendation=recommendation,
            risk=risk,
            alternatives=alternatives,
            next_step=next_step,
            timeline=timeline,
            duration=duration,
            metadata=metadata or {},
        )

    def _publish(self, event_type: str, payload: Dict[str, Any]):
        if not self.kernel:
            return

        try:
            self.kernel.publish(event_type, payload, source="InvestigationEngine")
        except Exception:
            # RC1 must not let event publishing break investigations.
            pass

    def _stamp(self, message: str) -> str:
        return f"{datetime.now().isoformat(timespec='seconds')} | {message}"
