class ConfidenceEngine:
    """
    Standard confidence and evidence reporting for FOXAI.

    This module does not verify truth by itself. It turns available evidence
    signals into a consistent confidence card that every department can use.
    """

    EVIDENCE_WEIGHTS = {
        "direct_file_match": 30,
        "project_index": 20,
        "dependency_graph": 20,
        "runtime_graph": 25,
        "mission_flow": 15,
        "technical_debt": 15,
        "diagnostics": 25,
        "user_observed": 20,
        "inference": 10,
        "general_reasoning": 5,
        "speculation": -25,
        "no_evidence": -40,
    }

    LABELS = [
        (90, "VERY HIGH"),
        (75, "HIGH"),
        (55, "MODERATE"),
        (35, "LOW"),
        (0, "VERY LOW"),
    ]

    def score(self, evidence=None, base=50, uncertainty=0):
        evidence = evidence or []
        total = base

        for item in evidence:
            if isinstance(item, str):
                key = item
            else:
                key = item.get("type", "")

            total += self.EVIDENCE_WEIGHTS.get(key, 0)

        total -= uncertainty
        return max(0, min(100, int(total)))

    def label(self, score):
        for threshold, label in self.LABELS:
            if score >= threshold:
                return label
        return "VERY LOW"

    def recommendation(self, score):
        if score >= 90:
            return "Strong evidence. Safe to treat this as reliable."
        if score >= 75:
            return "Good evidence. Reasonable confidence, but review details before major changes."
        if score >= 55:
            return "Moderate confidence. Treat as likely, not certain."
        if score >= 35:
            return "Low confidence. Treat as a hypothesis and verify before acting."
        return "Very low confidence. Do not rely on this without more evidence."

    def evidence_label(self, item):
        labels = {
            "direct_file_match": "Direct File Match",
            "project_index": "Project Index",
            "dependency_graph": "Dependency Graph",
            "runtime_graph": "Runtime Graph",
            "mission_flow": "Mission Flow",
            "technical_debt": "Technical Debt Engine",
            "diagnostics": "Diagnostics",
            "user_observed": "User Observation",
            "inference": "Inference",
            "general_reasoning": "General Reasoning",
            "speculation": "Speculation",
            "no_evidence": "No Direct Evidence",
        }

        if isinstance(item, str):
            return labels.get(item, item)

        kind = item.get("type", "unknown")
        detail = item.get("detail", "")
        base = labels.get(kind, kind)

        return f"{base}: {detail}" if detail else base

    def card(self, evidence=None, base=50, uncertainty=0, reason=""):
        evidence = evidence or []
        score = self.score(evidence=evidence, base=base, uncertainty=uncertainty)
        label = self.label(score)

        lines = [
            "CONFIDENCE REPORT",
            "",
            f"Confidence: {score}% - {label}",
            "",
            "Evidence:",
        ]

        if evidence:
            for item in evidence:
                lines.append(f"✓ {self.evidence_label(item)}")
        else:
            lines.append("— No direct evidence listed")

        if reason:
            lines.extend([
                "",
                "Reason:",
                reason,
            ])

        lines.extend([
            "",
            "Recommendation:",
            self.recommendation(score),
        ])

        return "\n".join(lines)

    def compact(self, evidence=None, base=50, uncertainty=0):
        evidence = evidence or []
        score = self.score(evidence=evidence, base=base, uncertainty=uncertainty)
        return f"Confidence: {score}% - {self.label(score)}"

    def workshop_evidence_table(self, used=None):
        used = set(used or [])

        rows = [
            ("Project Index", "project_index"),
            ("Dependency Graph", "dependency_graph"),
            ("Runtime Graph", "runtime_graph"),
            ("Mission Flow", "mission_flow"),
            ("Technical Debt", "technical_debt"),
            ("Diagnostics", "diagnostics"),
            ("Direct File Match", "direct_file_match"),
        ]

        lines = [
            "WORKSHOP EVIDENCE",
            "",
        ]

        for label, key in rows:
            mark = "✓" if key in used else "—"
            lines.append(f"{label:<18} {mark}")

        return "\n".join(lines)
