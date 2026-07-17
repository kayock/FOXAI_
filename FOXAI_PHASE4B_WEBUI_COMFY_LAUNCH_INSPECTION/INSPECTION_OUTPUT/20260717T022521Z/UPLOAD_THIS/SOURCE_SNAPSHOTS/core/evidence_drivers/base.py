from __future__ import annotations

from typing import List

from core.investigation_engine import Evidence, EvidenceDriver, Mission


class SmartSearchEvidenceDriver(EvidenceDriver):
    """
    Base class for SmartSearch-backed evidence drivers.

    RC2 adds search waves:
    1. preferred live source
    2. broader current project source
    3. history/vendor fallback only if needed
    """

    name = "SmartSearchEvidenceDriver"
    domain = "generic"
    search_terms: List[str] = []

    preferred_markers: List[str] = []
    live_source_markers: List[str] = [
        "core/",
        "ui/",
        "Memory/ui/",
        "FoxAI_Desktop.py",
        "foxai.py",
    ]
    avoid_markers: List[str] = [
        "ComfyUI",
        "Mission Archive",
        "Backups",
        "site-packages",
        "node_modules",
        ".venv",
        "venv",
    ]

    def __init__(self, smart_search):
        self.smart_search = smart_search

    def can_handle(self, mission: Mission) -> bool:
        lowered = mission.query.lower()
        return self.domain.lower() in lowered

    def collect(self, mission: Mission) -> List[Evidence]:
        terms = self.terms_for(mission)

        for wave_name, mode in [
            ("preferred_live_source", "preferred"),
            ("live_project_source", "live"),
            ("fallback_history_vendor", "fallback"),
        ]:
            evidence = self._collect_wave(terms, wave_name, mode)
            if evidence:
                return self._sort_evidence(evidence)

        return []

    def terms_for(self, mission: Mission) -> List[str]:
        return self.search_terms or [mission.query]

    def _collect_wave(self, terms: List[str], wave_name: str, mode: str) -> List[Evidence]:
        evidence: List[Evidence] = []

        for term in terms:
            result = self.smart_search.layered_search(term, limit=12)

            if mode == "preferred":
                categories = ["primary"]
            elif mode == "live":
                categories = ["primary"]
            else:
                categories = ["history", "vendor"]

            for category in categories:
                for item in result.get(category, []):
                    path = item.get("file", "")

                    if mode == "preferred" and not self._is_preferred(path):
                        continue

                    if mode == "live":
                        if self._is_avoided(path):
                            continue
                        if not self._is_live_source(path):
                            continue

                    if mode == "fallback":
                        # Fallback is allowed, but still records weak confidence.
                        pass

                    evidence.append(self._from_item(term, item, category, wave_name))

            if evidence:
                break

        return evidence

    def _from_item(self, term: str, item: dict, category: str, wave_name: str) -> Evidence:
        path = item.get("file", "")

        confidence = {
            "primary": 82,
            "history": 42,
            "vendor": 18,
        }.get(category, 30)

        weight = {
            "primary": 88,
            "history": 30,
            "vendor": 8,
        }.get(category, 20)

        if wave_name == "preferred_live_source":
            confidence += 10
            weight += 10
        elif wave_name == "fallback_history_vendor":
            confidence -= 12
            weight -= 12

        if self._is_preferred(path):
            confidence += 8
            weight += 8

        if self._is_avoided(path):
            confidence -= 25
            weight -= 30

        return Evidence(
            source=self.name,
            category="source" if category == "primary" else category,
            path=path,
            snippet=item.get("snippet", ""),
            confidence=max(0, min(100, confidence)),
            weight=max(0, min(100, weight)),
            metadata={
                "driver": self.name,
                "domain": self.domain,
                "search_term": term,
                "search_wave": wave_name,
                "raw_category": category,
                "evidence_class": item.get("evidence_class", ""),
                "evidence_label": item.get("evidence_label", ""),
                "score": item.get("score", 0),
                "preferred": self._is_preferred(path),
                "live_source": self._is_live_source(path),
                "avoided": self._is_avoided(path),
            },
        )

    def _sort_evidence(self, evidence: List[Evidence]) -> List[Evidence]:
        return sorted(
            evidence,
            key=lambda item: (
                item.metadata.get("preferred", False),
                item.metadata.get("live_source", False),
                not item.metadata.get("avoided", False),
                item.confidence,
                item.weight,
            ),
            reverse=True,
        )

    def _is_preferred(self, path: str) -> bool:
        normalized = path.replace("\\", "/").lower()
        return any(marker.lower() in normalized for marker in self.preferred_markers)

    def _is_live_source(self, path: str) -> bool:
        normalized = path.replace("\\", "/")
        lowered = normalized.lower()

        if self._is_avoided(normalized):
            return False

        if any(marker.lower() in lowered for marker in self.live_source_markers):
            return True

        # Root-level active Python files are considered live source.
        return "/" not in normalized and normalized.endswith(".py")

    def _is_avoided(self, path: str) -> bool:
        normalized = path.replace("\\", "/").lower()
        return any(marker.lower() in normalized for marker in self.avoid_markers)
