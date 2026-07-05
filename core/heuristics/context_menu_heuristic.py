from __future__ import annotations

from typing import Any, List

from core.heuristics import Heuristic, HeuristicMatch


class ContextMenuHeuristic(Heuristic):
    """
    ContextMenuHeuristic RC1

    Interprets evidence related to right-click/context menu problems.
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
    )

    def match(self, mission: Any, ranked_evidence: List[Any]) -> HeuristicMatch | None:
        query = (getattr(mission, "query", "") or "").lower()

        if not any(k in query for k in (
            "right click",
            "right-click",
            "context menu",
            "button-3",
            "popup menu",
        )):
            return None

        hits = []

        for ranked in ranked_evidence:
            evidence = getattr(ranked, "evidence", ranked)
            text = (
                (getattr(evidence, "snippet", "") or "") + "\n" +
                (getattr(evidence, "path", "") or "")
            ).lower()

            if any(k.lower() in text for k in self.KEYWORDS):
                hits.append(getattr(evidence, "path", "unknown"))

        if not hits:
            return None

        return HeuristicMatch(
            name=self.name,
            finding="Context-menu implementation was located.",
            confidence=92,
            reasoning=[
                "Evidence contains common Tk/CustomTkinter context-menu patterns.",
                "Live project source ranked highest.",
                f"{len(hits)} relevant source file(s) matched."
            ],
            suggested_actions=[
                "Verify the widget binds <Button-3> (or platform equivalent).",
                "Ensure the tk.Menu object is created before binding.",
                "Confirm the target widget receives focus before popup().",
                "Test Windows and Linux mouse-button mappings."
            ],
            alternatives=[
                "Centralize context-menu creation in one helper.",
                "Create a reusable ContextMenu service."
            ],
            risk="low",
            impact="ui reliability",
            metadata={"matched_paths": hits},
        )
