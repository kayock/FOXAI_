from core.mission_templates import MissionTemplates
from core.confidence_engine import ConfidenceEngine
from core.project_charter import ProjectCharterFactory


class ForgeMaster:
    """
    Forge Master RC1

    Generates safe advisory blueprints for future work.
    It does not execute, write files, or modify project state.
    """

    TEMPLATE_ALIASES = {
        "feature_development": [
            "new department", "new feature", "build", "add feature", "create department",
            "browser feature", "repair bay", "video", "comic"
        ],
        "refactor": [
            "refactor", "cleanup", "split", "simplify", "technical debt", "reorganize"
        ],
        "bug_fix": [
            "bug", "fix", "error", "crash", "broken", "not working", "fails"
        ],
        "creative_workflow": [
            "red canvas", "image", "prompt", "render", "creative", "visual"
        ],
        "identity_profile": [
            "identity", "profile", "theme", "kayock", "forge red", "soul forge",
            "rename", "branding", "first run"
        ],
        "research": [
            "research", "search", "library", "document", "sources", "evidence"
        ],
    }

    def __init__(self):
        self.templates = MissionTemplates()
        self.confidence = ConfidenceEngine()
        self.charter_factory = ProjectCharterFactory()

    def classify_template(self, mission):
        text = (mission or "").lower()
        scores = {key: 0 for key in self.templates.all().keys()}
        evidence = {key: [] for key in self.templates.all().keys()}

        for key, aliases in self.TEMPLATE_ALIASES.items():
            for alias in aliases:
                if alias in text:
                    scores[key] += 25
                    evidence[key].append(f"matched alias: {alias}")

        if max(scores.values()) == 0:
            scores["feature_development"] = 10
            evidence["feature_development"].append("fallback template")

        selected = max(scores, key=scores.get)

        return {
            "selected": selected,
            "scores": scores,
            "evidence": evidence[selected],
        }

    def estimate_complexity(self, mission, template_key):
        text = (mission or "").lower()

        if template_key in ["identity_profile", "research", "creative_workflow"]:
            return "Medium"

        if any(word in text for word in ["system", "architecture", "department", "engine", "automation", "multi"]):
            return "High"

        if template_key in ["feature_development", "refactor"]:
            return "High"

        return "Medium"

    def likely_artifacts(self, mission, template_key):
        text = (mission or "").lower()

        if template_key == "identity_profile":
            return [
                "core/identity.py",
                "Profiles/<profile_name>/identity.json",
                "ui/settings_panel.py",
            ]

        if "red canvas" in text:
            return [
                "core/promptsmith.py",
                "core/comfy_bridge.py",
                "ui/red_canvas_panel.py",
            ]

        if "browser" in text:
            return [
                "core/browser_bridge.py",
                "ui/browser_panel.py",
                "config/browser.json",
            ]

        if template_key == "refactor":
            return [
                "ui/main_window.py",
                "ui/<extracted_panel>.py",
                "core/<affected_module>.py",
            ]

        if template_key == "bug_fix":
            return [
                "mission log",
                "affected source file",
                "diagnostics report",
            ]

        return [
            "core/<new_module>.py",
            "ui/<optional_panel>.py",
            "config/<optional_config>.json",
        ]

    def risks(self, template_key):
        risk_map = {
            "feature_development": [
                "Scope creep",
                "Integration complexity",
                "UI growth pressure",
            ],
            "refactor": [
                "Behavior regression",
                "Import breakage",
                "Hidden runtime coupling",
            ],
            "bug_fix": [
                "Fixing symptom instead of root cause",
                "Regression in related feature",
            ],
            "creative_workflow": [
                "Prompt drift",
                "High CPU/RAM usage",
                "ComfyUI dependency",
            ],
            "identity_profile": [
                "Hardcoded branding remains",
                "Theme changes accidentally touching logic",
            ],
            "research": [
                "Unsupported claims",
                "Weak or stale evidence",
            ],
        }

        return risk_map.get(template_key, ["Unknown risk"])

    def blueprint(self, mission):
        classification = self.classify_template(mission)
        template_key = classification["selected"]
        template = self.templates.get(template_key)
        complexity = self.estimate_complexity(mission, template_key)
        artifacts = self.likely_artifacts(mission, template_key)
        risks = self.risks(template_key)

        evidence = [
            {"type": "inference", "detail": f"Forge template selected: {template['name']}"},
            {"type": "direct_file_match", "detail": "Template comes from MissionTemplates."},
        ]

        if classification["evidence"]:
            evidence.append({"type": "inference", "detail": "; ".join(classification["evidence"][:3])})

        uncertainty = 10 if classification["scores"][template_key] < 25 else 0

        lines = [
            "FORGE MASTER BLUEPRINT",
            "",
            f"Mission: {mission}",
            f"Template: {template['name']}",
            f"Complexity: {complexity}",
            "",
            "Purpose:",
            template["description"],
            "",
            "Forge Sequence:",
        ]

        for index, (stage, description) in enumerate(template["steps"], start=1):
            lines.append(f"{index}. {stage}")
            lines.append(f"   {description}")

        lines.extend([
            "",
            "Likely Artifacts:",
        ])

        for item in artifacts:
            lines.append(f"• {item}")

        lines.extend([
            "",
            "Risks:",
        ])

        for risk in risks:
            lines.append(f"• {risk}")

        lines.extend([
            "",
            "Quality Gates:",
            "• Blueprint reviewed",
            "• Operator approval received before writes",
            "• Imports compile",
            "• Diagnostics pass",
            "• Confidence report generated",
            "• Mission archived",
            "",
            self.confidence.card(
                evidence=evidence,
                base=65,
                uncertainty=uncertainty,
                reason="Forge Master selected a reusable mission template and produced an advisory blueprint."
            ),
            "",
            "Automation Status:",
            "Blueprint only. RC1 does not execute steps or modify files.",
            "",
            "Safety Status:",
            "Read-only. No files were modified.",
        ])

        return "\\n".join(lines)

    def charter(self, mission):
        charter = self.charter_factory.create(mission)

        lines = [
            charter.format(),
            "",
            self.confidence.card(
                evidence=[
                    {"type": "inference", "detail": "Project Charter Factory selected a charter type."},
                    {"type": "direct_file_match", "detail": "Charter fields are generated from a structured ProjectCharter object."},
                ],
                base=70,
                reason="This charter is an advisory project agreement. It defines scope before any implementation begins."
            ),
            "",
            "Automation Status:",
            "Charter only. No files were written or modified.",
            "",
            "Safety Status:",
            "Read-only. Operator approval required before forging.",
        ]

        return "\n".join(lines)

    def templates_report(self):
        return self.templates.report()
