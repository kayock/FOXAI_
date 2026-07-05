from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class HeuristicMatch:
    """
    A matched engineering heuristic.
    """
    name: str
    finding: str
    confidence: int
    reasoning: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    risk: str = "low"
    impact: str = "maintainability"
    metadata: Dict[str, Any] = field(default_factory=dict)


class Heuristic:
    """
    Base heuristic contract.
    """

    name = "Base Heuristic"

    def match(self, mission: Any, ranked_evidence: List[Any]) -> HeuristicMatch | None:
        raise NotImplementedError


class HardcodedTimeoutHeuristic(Heuristic):
    """
    Detects hardcoded timeout values in evidence snippets.
    """

    name = "Hardcoded Timeout"

    def match(self, mission: Any, ranked_evidence: List[Any]) -> HeuristicMatch | None:
        hits = []

        for ranked in ranked_evidence:
            evidence = getattr(ranked, "evidence", ranked)
            snippet = getattr(evidence, "snippet", "") or ""
            path = getattr(evidence, "path", "") or ""

            if "timeout=300" in snippet.replace(" ", "") or "timeout = 300" in snippet:
                hits.append(path or "unknown source")

        if not hits:
            return None

        unique_hits = list(dict.fromkeys(hits))

        return HeuristicMatch(
            name=self.name,
            finding="HTTP timeout appears to be hardcoded.",
            confidence=90,
            reasoning=[
                "A literal timeout value was found in source evidence.",
                "Hardcoded operational values are harder to tune across machines and models.",
                f"Detected in {len(unique_hits)} evidence source(s).",
            ],
            suggested_actions=[
                "Move the timeout value into configuration.",
                "Add a named setting such as request_timeout_seconds.",
                "Allow a safe default while permitting machine-specific overrides.",
            ],
            alternatives=[
                "Use an environment variable for quick overrides.",
                "Use a command-line argument for developer testing.",
            ],
            risk="low",
            impact="maintainability and portability",
            metadata={"hits": unique_hits},
        )


class KernelComponentHeuristic(Heuristic):
    """
    Recognizes investigation/kernel component evidence.
    """

    name = "Kernel Component Evidence"

    def match(self, mission: Any, ranked_evidence: List[Any]) -> HeuristicMatch | None:
        query = (getattr(mission, "query", "") or "").lower()

        if "investigation engine" not in query and "investigation_engine" not in query:
            return None

        paths = []
        for ranked in ranked_evidence:
            evidence = getattr(ranked, "evidence", ranked)
            path = getattr(evidence, "path", "") or ""
            if "investigation" in path.lower() or "engineer_agent" in path.lower() or "engineer_intent" in path.lower():
                paths.append(path)

        if not paths:
            return None

        return HeuristicMatch(
            name=self.name,
            finding="Investigation Engine integration evidence was found.",
            confidence=82,
            reasoning=[
                "Evidence references Investigation Engine related code paths.",
                "The feature appears to be connected through Engineer-facing integration points.",
            ],
            suggested_actions=[
                "Expose Investigation Engine through the Kernel facade.",
                "Move SourceCodeDriver out of Engineer once the interface stabilizes.",
                "Add a small command or test that verifies mission-to-result flow.",
            ],
            alternatives=[
                "Keep SourceCodeDriver inside Engineer temporarily during RC testing.",
            ],
            risk="medium",
            impact="kernel architecture",
            metadata={"paths": list(dict.fromkeys(paths))},
        )


class ContextMenuHeuristic(Heuristic):
    """
    Interprets evidence related to right-click/context-menu behavior.
    """

    name = "Context Menu"

    KEYWORDS = (
        "<Button-3>",
        "<ButtonRelease-3>",
        "tk.Menu",
        "context menu",
        "right click",
        "right-click",
        "event_generate",
        "CTkTextbox",
        "input_box",
        "chat_box",
        "popup menu",
    )

    def match(self, mission: Any, ranked_evidence: List[Any]) -> HeuristicMatch | None:
        query = (getattr(mission, "query", "") or "").lower()

        if not any(term in query for term in (
            "right click",
            "right-click",
            "context menu",
            "button-3",
            "popup menu",
            "menu not appearing",
        )):
            return None

        hits = []

        for ranked in ranked_evidence:
            evidence = getattr(ranked, "evidence", ranked)
            text = (
                (getattr(evidence, "snippet", "") or "") + "\n" +
                (getattr(evidence, "path", "") or "")
            ).lower()

            if any(keyword.lower() in text for keyword in self.KEYWORDS):
                hits.append(getattr(evidence, "path", "unknown source"))

        if not hits:
            return HeuristicMatch(
                name=self.name,
                finding="Context-menu evidence was not found in live source.",
                confidence=45,
                reasoning=[
                    "The mission asks about right-click/context-menu behavior.",
                    "The selected driver ran, but no strong implementation evidence matched.",
                    "This usually means the feature is missing, not wired, or named differently.",
                ],
                suggested_actions=[
                    "Search active UI files for text widget creation.",
                    "Add a reusable context-menu helper if no implementation exists.",
                    "Bind the helper to input/chat text widgets.",
                ],
                alternatives=[
                    "Run a broader UI investigation.",
                    "Inspect main_window.py manually for textbox widgets.",
                ],
                risk="medium",
                impact="ui usability",
                metadata={"matched_paths": []},
            )

        unique_hits = list(dict.fromkeys(hits))

        return HeuristicMatch(
            name=self.name,
            finding="Context-menu implementation evidence was located.",
            confidence=88,
            reasoning=[
                "Evidence contains Tk/CustomTkinter context-menu patterns.",
                "The query matches right-click/context-menu behavior.",
                f"{len(unique_hits)} relevant source file(s) matched.",
            ],
            suggested_actions=[
                "Verify the target widget binds <Button-3> or the platform equivalent.",
                "Ensure the tk.Menu object is created before binding.",
                "Confirm the widget receives focus before showing the popup menu.",
                "Test Windows and Linux mouse-button mappings.",
            ],
            alternatives=[
                "Centralize context-menu creation in one reusable helper.",
                "Create a ContextMenu service shared by chat, input, and editor widgets.",
            ],
            risk="low",
            impact="ui reliability",
            metadata={"matched_paths": unique_hits},
        )


class GenericEvidenceHeuristic(Heuristic):
    """
    Fallback when evidence exists but no specific heuristic matches.
    """

    name = "Generic Evidence Review"

    def match(self, mission: Any, ranked_evidence: List[Any]) -> HeuristicMatch | None:
        if not ranked_evidence:
            return HeuristicMatch(
                name=self.name,
                finding="No evidence was collected.",
                confidence=20,
                reasoning=[
                    "The investigation pipeline ran, but no evidence items were available.",
                ],
                suggested_actions=[
                    "Add or enable an evidence driver.",
                    "Try a more specific investigation query.",
                ],
                alternatives=[
                    "Run SmartSearch manually as a fallback.",
                ],
                risk="unknown",
                impact="insufficient evidence",
            )

        return HeuristicMatch(
            name=self.name,
            finding="Evidence was collected, but no specific engineering heuristic matched.",
            confidence=55,
            reasoning=[
                "Ranked evidence exists.",
                "No specialized recommendation rule matched this investigation yet.",
            ],
            suggested_actions=[
                "Review the top-ranked evidence.",
                "Add a domain-specific heuristic if this investigation type is common.",
            ],
            alternatives=[
                "Ask Engineer for a deeper architecture review.",
            ],
            risk="medium",
            impact="requires human review",
        )


DEFAULT_HEURISTICS = [
    HardcodedTimeoutHeuristic(),
    KernelComponentHeuristic(),
    ContextMenuHeuristic(),
    GenericEvidenceHeuristic(),
]
