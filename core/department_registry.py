class DepartmentRegistry:
    """
    Central registry of FOXAI Workshop departments.

    RC1 is static and read-only. Future versions can load department manifests
    from files so new departments can be added without editing core code.
    """

    def __init__(self):
        self.departments = self.default_departments()

    def default_departments(self):
        return {
            "chat": {
                "name": "Agent Fox",
                "status": "Ready",
                "mission_types": ["conversation", "general", "reasoning", "writing"],
                "preferred_models": ["DeepSeek-R1", "Qwen3VL", "Qwen"],
                "capabilities": ["Conversation", "General reasoning", "Writing assistance"],
                "requires": ["Neural Engine"],
                "risk": "Low",
            },
            "engineer": {
                "name": "Engineer",
                "status": "Ready",
                "mission_types": ["engineering", "architecture", "code review", "debugging", "refactor planning"],
                "preferred_models": ["Qwen3-Coder", "DeepSeek-R1"],
                "capabilities": [
                    "Project Index",
                    "Dependency Graph",
                    "Runtime Graph",
                    "Mission Flow",
                    "Technical Debt",
                    "Confidence Reports",
                ],
                "requires": ["Project files", "Project Index", "Confidence Engine"],
                "risk": "Low in read-only mode",
            },
            "red_canvas": {
                "name": "Red Canvas",
                "status": "Ready if ComfyUI is online",
                "mission_types": ["creative", "image", "visual", "prompt", "render"],
                "preferred_models": ["Qwen3VL", "DeepSeek-R1"],
                "capabilities": ["Prompt enhancement", "Image generation", "ComfyUI bridge"],
                "requires": ["ComfyUI", "PromptSmith", "workflow_api.json"],
                "risk": "Medium resource usage",
            },
            "iron_library": {
                "name": "Iron Library",
                "status": "Ready",
                "mission_types": ["research", "library", "document search", "local knowledge"],
                "preferred_models": ["Qwen3-Coder", "DeepSeek-R1", "Qwen"],
                "capabilities": ["Local search", "Document snippets", "Project knowledge retrieval"],
                "requires": ["Library folder"],
                "risk": "Low",
            },
            "diagnostics": {
                "name": "Diagnostics",
                "status": "Ready",
                "mission_types": ["diagnostics", "health", "system status", "hardware", "advisor"],
                "preferred_models": ["None required", "Lightweight model optional"],
                "capabilities": ["Workshop health", "Hardware status", "Neural status", "Workshop Advisor"],
                "requires": ["psutil", "Brainstem"],
                "risk": "Low",
            },
            "settings": {
                "name": "Settings",
                "status": "Planned",
                "mission_types": ["settings", "configuration", "profile", "theme", "model selection"],
                "preferred_models": ["None required"],
                "capabilities": ["Configuration management", "Profile switching", "Model preferences"],
                "requires": ["Identity Engine"],
                "risk": "Planned",
            },
            "soul_forge": {
                "name": "Soul Forge",
                "status": "Planned",
                "mission_types": ["identity", "profile", "branding", "theme", "first run setup"],
                "preferred_models": ["None required", "Qwen3-Coder for setup logic"],
                "capabilities": ["Workshop identity", "Theme profile", "Assistant naming", "First-run wizard"],
                "requires": ["Profile storage"],
                "risk": "Planned",
            },
        }

    def all(self):
        return self.departments

    def get(self, key):
        return self.departments.get(key)

    def find_by_mission(self, mission_type):
        lowered = mission_type.lower()
        matches = []

        for key, info in self.departments.items():
            types = [t.lower() for t in info.get("mission_types", [])]
            if any(lowered in t or t in lowered for t in types):
                matches.append((key, info))

        return matches

    def report(self):
        lines = [
            "DEPARTMENT REGISTRY",
            "",
            "Registered departments:",
            "",
        ]

        for key, info in self.departments.items():
            lines.append(f"--- {info['name']} ({key}) ---")
            lines.append(f"Status: {info.get('status', 'Unknown')}")
            lines.append(f"Mission Types: {', '.join(info.get('mission_types', []))}")
            lines.append(f"Preferred Models: {', '.join(info.get('preferred_models', []))}")
            lines.append(f"Capabilities: {', '.join(info.get('capabilities', []))}")
            lines.append(f"Requires: {', '.join(info.get('requires', []))}")
            lines.append(f"Risk: {info.get('risk', 'Unknown')}")
            lines.append("")

        lines.append("Safety Status:")
        lines.append("Registry is read-only in RC1. No files were modified.")

        return "\n".join(lines)
