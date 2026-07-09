class MissionTemplates:
    """
    Forge Master mission templates.

    Templates describe reusable engineering workflows.
    They do not execute anything. They produce blueprints.
    """

    def __init__(self):
        self.templates = self._build()

    def _build(self):
        return {
            "feature_development": {
                "name": "Feature Development",
                "description": "Build a new feature or department safely.",
                "steps": [
                    ("Requirements", "Define what the feature must do."),
                    ("Architecture", "Identify modules, dependencies, and boundaries."),
                    ("Blueprint", "List artifacts, files, risks, and integration points."),
                    ("Forge", "Create or modify code only after approval."),
                    ("Integration", "Wire the feature into the Workshop."),
                    ("Diagnostics", "Run health and import checks."),
                    ("Confidence Review", "Summarize evidence, risk, and confidence."),
                    ("Operator Approval", "Wait for the operator before finalizing."),
                    ("Archive", "Save the mission record and lessons learned."),
                ],
            },
            "refactor": {
                "name": "Refactor",
                "description": "Improve structure without changing behavior.",
                "steps": [
                    ("Technical Debt Review", "Identify size, complexity, and responsibility issues."),
                    ("Impact Analysis", "Find affected modules and runtime relationships."),
                    ("Blueprint", "Define safe extraction or cleanup boundaries."),
                    ("Forge", "Apply focused changes only after approval."),
                    ("Regression Check", "Verify behavior remains unchanged."),
                    ("Diagnostics", "Run Workshop health checks."),
                    ("Confidence Review", "Report evidence and remaining risk."),
                    ("Archive", "Save refactor notes and lessons learned."),
                ],
            },
            "bug_fix": {
                "name": "Bug Fix",
                "description": "Investigate and repair an observed issue.",
                "steps": [
                    ("Symptom Capture", "Record what happened and how to reproduce it."),
                    ("Evidence Review", "Inspect logs, diagnostics, and related code."),
                    ("Root Cause Hypothesis", "List likely causes with confidence."),
                    ("Patch Blueprint", "Propose minimal safe fix."),
                    ("Forge", "Apply patch only after approval."),
                    ("Verification", "Run the original failing case."),
                    ("Regression Check", "Confirm related systems still work."),
                    ("Archive", "Save the bug record and fix notes."),
                ],
            },
            "creative_workflow": {
                "name": "Creative Workflow",
                "description": "Plan a creative or Red Canvas mission.",
                "steps": [
                    ("Intent Review", "Clarify desired visual or creative output."),
                    ("PromptSmith", "Optimize prompt structure and style."),
                    ("Red Canvas", "Render or prepare the visual workflow."),
                    ("Review", "Inspect output against intent."),
                    ("Refinement", "Adjust prompt, model, or workflow if needed."),
                    ("Archive", "Save prompt, result path, and lessons learned."),
                ],
            },
            "identity_profile": {
                "name": "Identity Profile",
                "description": "Create or modify a Workshop identity such as Kayock's Forge.",
                "steps": [
                    ("Identity Requirements", "Define name, assistant, theme, and purpose."),
                    ("Profile Blueprint", "Map identity settings to configuration fields."),
                    ("Theme Safety", "Ensure branding changes do not alter core logic."),
                    ("Forge Profile", "Create profile files only after approval."),
                    ("Apply Preview", "Preview labels, colors, and startup text."),
                    ("Diagnostics", "Confirm the Workshop still loads correctly."),
                    ("Archive", "Save profile creation record."),
                ],
            },
            "research": {
                "name": "Research",
                "description": "Search and organize local or external reference material.",
                "steps": [
                    ("Question Definition", "Define the research target."),
                    ("Source Search", "Use Iron Library or browser-supported research."),
                    ("Evidence Sorting", "Separate facts, assumptions, and speculation."),
                    ("Summary", "Create a concise grounded report."),
                    ("Archive", "Save citations, notes, and follow-up questions."),
                ],
            },
        }

    def get(self, key):
        return self.templates.get(key)

    def all(self):
        return self.templates

    def report(self):
        lines = [
            "FORGE TEMPLATES",
            "",
            "Available templates:",
            "",
        ]

        for key, item in self.templates.items():
            lines.append(f"--- {item['name']} ({key}) ---")
            lines.append(item["description"])
            lines.append("Steps:")
            for index, (stage, description) in enumerate(item["steps"], start=1):
                lines.append(f"{index}. {stage} - {description}")
            lines.append("")

        lines.append("Safety Status:")
        lines.append("Templates are advisory. No files were modified.")

        return "\\n".join(lines)
