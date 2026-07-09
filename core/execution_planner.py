from core.capability_graph import CapabilityGraph


class ExecutionPlanner:
    """
    Execution Planner RC1

    Converts a mission into a multi-step departmental plan.
    This is the first step toward orchestration in Decision Layer 3.0.
    """

    def __init__(self):
        self.graph = CapabilityGraph()

    def classify_steps(self, query):
        q = query.lower()

        steps = []

        # Engineering-heavy
        if any(x in q for x in ["engineer", "code", "architecture", "refactor", "system"]):
            steps.append(("engineer", "architecture_review"))

        # Prompt / creative enhancement
        if any(x in q for x in ["prompt", "improve", "optimize text"]):
            steps.append(("promptsmith", "prompt_optimization"))

        # Visual generation
        if any(x in q for x in ["image", "draw", "render", "visual"]):
            steps.append(("red_canvas", "image_generation"))

        # Knowledge retrieval
        if any(x in q for x in ["search", "find", "library", "docs"]):
            steps.append(("iron_library", "knowledge_retrieval"))

        # Diagnostics
        if any(x in q for x in ["status", "health", "cpu", "diagnostic"]):
            steps.append(("diagnostics", "system_health"))

        # Default fallback
        if not steps:
            steps.append(("chat", "conversation"))

        return steps

    def build_plan(self, query):
        steps = self.classify_steps(query)

        plan = {
            "mission": query,
            "steps": [],
            "automation": False,
            "confidence": 0.85,
        }

        for i, (dept, capability) in enumerate(steps, 1):
            plan["steps"].append({
                "step": i,
                "department": dept,
                "capability": capability,
                "model_hint": self._model_hint(dept),
            })

        return plan

    def _model_hint(self, department):
        mapping = {
            "engineer": "Qwen3-Coder",
            "red_canvas": "Qwen3-VL / DeepSeek",
            "promptsmith": "DeepSeek",
            "iron_library": "DeepSeek / Qwen",
            "diagnostics": "Lightweight model or none",
            "chat": "General model",
            "soul_forge": "Qwen / DeepSeek",
        }
        return mapping.get(department, "General model")

    def format_plan(self, plan):
        lines = [
            "EXECUTION PLAN (RC1)",
            "",
            f"Mission: {plan['mission']}",
            "",
            "Steps:",
        ]

        for step in plan["steps"]:
            lines.append(
                f"{step['step']}. {step['department']} "
                f"-> {step['capability']} "
                f"(Model Hint: {step['model_hint']})"
            )

        lines.extend([
            "",
            f"Automation: {'ON' if plan['automation'] else 'OFF'}",
            f"Base Confidence: {int(plan['confidence'] * 100)}%",
            "",
            "Status: Advisory only (RC1)",
        ])

        return "\n".join(lines)
