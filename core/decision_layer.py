from core.department_registry import DepartmentRegistry
from core.confidence_engine import ConfidenceEngine
from core.execution_planner import ExecutionPlanner


class DecisionLayer:
    """
    Advisory decision layer for FOXAI.

    v3 connects:
    - Department Registry
    - Confidence Engine
    - Capability Graph
    - Execution Planner

    Still advisory only. It does not switch models, launch departments,
    or modify files.
    """

    DEPARTMENT_ALIASES = {
        "engineer": ["engineer", "engineering", "code", "debug", "architecture", "refactor"],
        "red_canvas": ["red canvas", "canvas", "image", "visual", "render", "picture", "draw", "promptsmith", "comfyui", "comfy"],
        "iron_library": ["iron library", "library", "research", "document", "documents", "search files", "local knowledge"],
        "diagnostics": ["diagnostics", "diagnostic", "health", "status", "hardware", "cpu", "ram", "workshop health"],
        "settings": ["settings", "configuration", "config", "profile", "theme", "model selection"],
        "soul_forge": ["soul forge", "identity", "branding", "first run", "forge", "kayock"],
        "chat": ["chat", "conversation", "general", "writing", "agent fox"],
    }

    MISSION_BY_DEPARTMENT = {
        "engineer": "engineering",
        "red_canvas": "creative",
        "iron_library": "research",
        "diagnostics": "diagnostics",
        "settings": "configuration",
        "soul_forge": "identity",
        "chat": "conversation",
    }

    def __init__(self):
        self.registry = DepartmentRegistry()
        self.confidence = ConfidenceEngine()
        self.planner = ExecutionPlanner()

    def normalize_query(self, query):
        return " ".join((query or "").strip().split())

    def strip_command_prefix(self, query):
        text = self.normalize_query(query)
        lowered = text.lower()

        prefixes = [
            "engineer,",
            "engineer ",
            "agent fox,",
            "fox,",
            "please ",
        ]

        for prefix in prefixes:
            if lowered.startswith(prefix):
                return text[len(prefix):].strip()

        return text

    def extract_subject_text(self, query):
        text = self.strip_command_prefix(query)
        lowered = text.lower()

        markers = [
            "decision report for ",
            "decision report about ",
            "model recommendation for ",
            "recommend model for ",
            "department recommendation for ",
            "execution plan for ",
            "plan for ",
            "report for ",
            "for ",
            "about ",
        ]

        for marker in markers:
            idx = lowered.find(marker)
            if idx >= 0:
                return text[idx + len(marker):].strip()

        return text

    def score_departments(self, query):
        subject = self.extract_subject_text(query)
        lowered = subject.lower()

        scores = {key: 0 for key in self.registry.all().keys()}
        evidence = {key: [] for key in self.registry.all().keys()}

        for key, aliases in self.DEPARTMENT_ALIASES.items():
            for alias in aliases:
                if alias in lowered:
                    points = 50 if alias == lowered or alias in lowered else 30
                    scores[key] += points
                    evidence[key].append(f"subject contains alias: {alias}")

        for key, info in self.registry.all().items():
            for mission_type in info.get("mission_types", []):
                if mission_type.lower() in lowered:
                    scores[key] += 20
                    evidence[key].append(f"matches mission type: {mission_type}")

        if max(scores.values()) == 0:
            fallback = self.classify_mission(subject)
            department = self.recommend_department(fallback)
            scores[department] += 15
            evidence[department].append(f"fallback mission classification: {fallback}")

        selected = max(scores, key=scores.get)

        return {
            "subject": subject,
            "scores": scores,
            "evidence": evidence,
            "selected_department": selected,
        }

    def classify_mission(self, query):
        lowered = self.extract_subject_text(query).lower()

        if any(term in lowered for term in ["code", "architecture", "debug", "refactor", "technical debt"]):
            return "engineering"

        if any(term in lowered for term in ["draw", "image", "render", "red canvas", "promptsmith", "visual", "picture", "canvas"]):
            return "creative"

        if any(term in lowered for term in ["library", "search documents", "research", "find in files", "iron library"]):
            return "research"

        if any(term in lowered for term in ["diagnostics", "health", "status", "hardware", "cpu", "ram"]):
            return "diagnostics"

        if any(term in lowered for term in ["settings", "theme", "profile", "identity", "name", "color", "soul forge", "forge"]):
            return "configuration"

        return "conversation"

    def complexity(self, query, mission_type, plan=None):
        length = len(query)
        step_count = len(plan.get("steps", [])) if isinstance(plan, dict) else 1

        if step_count >= 3:
            return "High"

        if mission_type in ["engineering", "creative"] and length > 120:
            return "High"

        if mission_type in ["engineering", "diagnostics", "configuration", "identity"]:
            return "Medium"

        if length > 200:
            return "Medium"

        return "Low"

    def recommend_department(self, mission_type):
        mapping = {
            "engineering": "engineer",
            "creative": "red_canvas",
            "research": "iron_library",
            "diagnostics": "diagnostics",
            "configuration": "settings",
            "identity": "soul_forge",
            "conversation": "chat",
        }

        return mapping.get(mission_type, "chat")

    def recommend_model(self, mission_type, department_key=None, available_models=None):
        available_models = available_models or []
        names = [getattr(model, "name", str(model)) for model in available_models]
        lowered = [name.lower() for name in names]

        def find_contains(*needles):
            for i, name in enumerate(lowered):
                if all(needle.lower() in name for needle in needles):
                    return names[i]
            return None

        if department_key == "engineer" or mission_type == "engineering":
            return find_contains("coder") or find_contains("qwen") or find_contains("deepseek") or (names[0] if names else "Qwen3-Coder recommended")

        if department_key == "red_canvas" or mission_type == "creative":
            return find_contains("vl") or find_contains("deepseek") or find_contains("qwen") or (names[0] if names else "Qwen3VL or DeepSeek recommended")

        if department_key == "iron_library" or mission_type == "research":
            return find_contains("coder") or find_contains("deepseek") or find_contains("qwen") or (names[0] if names else "Qwen or DeepSeek recommended")

        if department_key == "diagnostics" or mission_type == "diagnostics":
            return "No model required unless explanation is requested"

        if department_key in ["settings", "soul_forge"] or mission_type in ["configuration", "identity"]:
            return find_contains("coder") or find_contains("qwen") or (names[0] if names else "Qwen3-Coder recommended")

        return find_contains("deepseek") or find_contains("qwen") or (names[0] if names else "General model recommended")

    def recommend_settings(self, mission_type, department_key=None, hardware=None):
        hardware = hardware or {}

        settings = {
            "temperature": 0.7,
            "context": 8192,
            "reply_tokens": 2048,
            "threads": hardware.get("recommended_threads", 10),
        }

        if department_key == "engineer" or mission_type == "engineering":
            settings.update({
                "temperature": 0.2,
                "context": 8192,
                "reply_tokens": 2048,
            })

        elif department_key == "red_canvas" or mission_type == "creative":
            settings.update({
                "temperature": 0.8,
                "context": 8192,
                "reply_tokens": 2048,
            })

        elif department_key == "diagnostics" or mission_type == "diagnostics":
            settings.update({
                "temperature": 0.1,
                "context": 4096,
                "reply_tokens": 1024,
            })

        elif department_key in ["settings", "soul_forge"] or mission_type in ["configuration", "identity"]:
            settings.update({
                "temperature": 0.3,
                "context": 8192,
                "reply_tokens": 2048,
            })

        return settings

    def build_execution_plan(self, subject):
        return self.planner.build_plan(subject)

    def format_execution_plan_block(self, plan):
        lines = [
            "Execution Plan:",
        ]

        steps = plan.get("steps", [])

        if not steps:
            lines.append("• No execution steps generated.")
            return lines

        for step in steps:
            lines.append(
                f"{step.get('step')}. "
                f"{step.get('department')} → {step.get('capability')} "
                f"(Model Hint: {step.get('model_hint')})"
            )

        lines.extend([
            "",
            f"Plan Automation: {'ON' if plan.get('automation') else 'OFF'}",
            f"Plan Confidence: {int(plan.get('confidence', 0) * 100)}%",
        ])

        return lines

    def report(self, query, available_models=None, hardware=None):
        query = self.normalize_query(query)
        subject_analysis = self.score_departments(query)

        department_key = subject_analysis["selected_department"]
        department = self.registry.get(department_key)
        mission_type = self.MISSION_BY_DEPARTMENT.get(department_key, self.classify_mission(query))

        subject = subject_analysis["subject"]
        plan = self.build_execution_plan(subject)

        complexity = self.complexity(query, mission_type, plan)
        model = self.recommend_model(mission_type, department_key, available_models)
        settings = self.recommend_settings(mission_type, department_key, hardware)

        score = subject_analysis["scores"].get(department_key, 0)
        trace = subject_analysis["evidence"].get(department_key, [])

        evidence = [
            {"type": "inference", "detail": f"Subject interpreted as: {subject}"},
            {"type": "direct_file_match", "detail": "Department recommendation comes from the Department Registry."},
            {"type": "inference", "detail": "Execution Planner generated an advisory multi-step plan."},
        ]

        if available_models:
            evidence.append({"type": "diagnostics", "detail": "Available model list was considered."})

        if trace:
            evidence.append({"type": "inference", "detail": "; ".join(trace[:3])})

        reason = (
            f"The command shell was separated from the requested subject. "
            f"The subject appears to target {department['name'] if department else department_key}, "
            f"which maps to a {mission_type} mission. "
            f"The Execution Planner then decomposed the subject into advisory capability steps."
        )

        lines = [
            "DECISION LAYER REPORT",
            "",
            "Request:",
            query,
            "",
            f"Interpreted Subject: {subject}",
            f"Mission Type: {mission_type.title()}",
            f"Complexity: {complexity}",
            f"Recommended Department: {department['name'] if department else department_key}",
            f"Recommended Model: {model}",
            "",
            "Decision Trace:",
        ]

        if trace:
            for item in trace:
                lines.append(f"• {item}")
        else:
            lines.append("• fallback classification used")

        lines.extend([
            "",
            "Department Scores:",
        ])

        for key, value in sorted(subject_analysis["scores"].items(), key=lambda item: item[1], reverse=True):
            if value > 0:
                name = self.registry.get(key)["name"] if self.registry.get(key) else key
                lines.append(f"• {name}: {value}")

        lines.extend([
            "",
        ])

        lines.extend(self.format_execution_plan_block(plan))

        lines.extend([
            "",
            "Recommended Settings:",
            f"• Temperature: {settings['temperature']}",
            f"• Context: {settings['context']}",
            f"• Reply Tokens: {settings['reply_tokens']}",
            f"• Threads: {settings['threads']}",
            "",
            "Department Capabilities:",
        ])

        if department:
            for capability in department.get("capabilities", []):
                lines.append(f"• {capability}")

            lines.extend([
                "",
                "Department Requirements:",
            ])

            for requirement in department.get("requires", []):
                lines.append(f"• {requirement}")

        uncertainty = 0
        if score < 40:
            uncertainty += 15
        if complexity == "High":
            uncertainty += 5

        lines.extend([
            "",
            self.confidence.card(
                evidence=evidence,
                base=65,
                uncertainty=uncertainty,
                reason=reason,
            ),
            "",
            "Automation Status:",
            "Advisory only. Decision Layer v3 does not switch models or launch departments automatically.",
            "",
            "Safety Status:",
            "Read-only. No files were modified.",
        ])

        return "\n".join(lines)

    def execution_plan_report(self, query):
        subject = self.extract_subject_text(query)
        plan = self.build_execution_plan(subject)

        lines = [
            "EXECUTION PLANNER REPORT",
            "",
            f"Mission: {subject}",
            "",
        ]

        lines.extend(self.format_execution_plan_block(plan))

        lines.extend([
            "",
            self.confidence.card(
                evidence=[
                    {"type": "inference", "detail": "Execution Planner decomposed the mission into capability steps."},
                    {"type": "direct_file_match", "detail": "Capabilities come from the Capability Graph."},
                ],
                base=65,
                reason="This is an advisory workflow plan. It describes what should happen, not what has happened."
            ),
            "",
            "Automation Status:",
            "Advisory only. No steps were executed.",
            "",
            "Safety Status:",
            "Read-only. No files were modified.",
        ])

        return "\n".join(lines)

    def registry_report(self):
        return self.registry.report()
