class CapabilityGraph:
    """
    Workshop Capability Graph (RC1)

    Maps departments to atomic capabilities.
    Used by Decision Layer 3.0 to reason about skill requirements.
    """

    def __init__(self):
        self.capabilities = self._build()

    def _build(self):
        return {
            "engineer": [
                "code_analysis",
                "architecture_review",
                "dependency_mapping",
                "runtime_tracing",
                "technical_debt_analysis",
                "refactor_planning",
            ],
            "red_canvas": [
                "image_generation",
                "prompt_enhancement",
                "visual_composition",
                "workflow_rendering",
            ],
            "promptsmith": [
                "prompt_optimization",
                "semantic_refinement",
                "style_shaping",
            ],
            "iron_library": [
                "document_search",
                "knowledge_retrieval",
                "local_index_query",
            ],
            "diagnostics": [
                "system_health",
                "hardware_monitoring",
                "performance_analysis",
            ],
            "soul_forge": [
                "identity_creation",
                "theme_configuration",
                "profile_building",
            ],
            "chat": [
                "conversation",
                "general_reasoning",
                "writing_assistance",
            ],
        }

    def get(self, department):
        return self.capabilities.get(department, [])

    def find_departments_for_capability(self, capability):
        matches = []
        for dept, caps in self.capabilities.items():
            if capability in caps:
                matches.append(dept)
        return matches

    def all(self):
        return self.capabilities
