class EngineerIntent:
    """
    Engineer Intent Classifier RC2

    Classifies engineering questions before falling back to raw project search.
    """

    ARCHITECTURE_TERMS = [
        "review your code", "evaluate your code", "review the workshop",
        "evaluate the workshop", "architecture review", "design review",
        "code and design", "recommendations for upgrade",
        "recommendations for smoothness", "smoothness", "prominent detail",
        "prominate detail", "overall design"
    ]

    UI_INVESTIGATION_TERMS = [
        "right click", "right-click", "context menu", "menu comes up",
        "popup menu", "spell check menu", "ui menu", "mouse menu", "button-3"
    ]

    PERFORMANCE_TERMS = [
        "slow", "lag", "freeze", "frozen", "performance",
        "takes too long", "stutter", "startup time"
    ]

    SECURITY_TERMS = [
        "security", "safe", "unsafe", "risk", "permission",
        "admin", "sandbox", "password", "credentials"
    ]

    BUG_TERMS = [
        "bug", "broken", "error", "doesn't work", "does not work",
        "not working", "fails", "crash"
    ]

    SEARCH_TERMS = [
        "find", "where is", "where are", "search", "locate", "defined"
    ]

    FORGE_TERMS = [
        "forge sprint",
        "begin forge",
        "start forge",
        "build component",
        "create component",
        "create a new file",
        "new file",
        "generate implementation",
        "implement",
        "write the code",
        "build the skeleton",
        "kernel component",
        "create core/",
        "create core\\",
        "investigation_engine.py",
    ]

    def classify(self, query):
        lowered = (query or "").lower()

        if self.has_any(lowered, self.FORGE_TERMS):
            return {
                "intent": "forge_build",
                "label": "Forge Build",
                "reason": "Operator requested implementation of a new component or Forge Sprint.",
            }

        if self.has_any(lowered, self.UI_INVESTIGATION_TERMS):
            return {
                "intent": "ui_investigation",
                "label": "UI Investigation",
                "reason": "Question mentions context menu / right-click UI behavior.",
            }

        if self.has_any(lowered, self.ARCHITECTURE_TERMS):
            return {
                "intent": "architecture_review",
                "label": "Architecture Review",
                "reason": "Question asks for overall code/design evaluation.",
            }

        if self.has_any(lowered, self.PERFORMANCE_TERMS):
            return {
                "intent": "performance_review",
                "label": "Performance Review",
                "reason": "Question mentions speed, lag, freezing, or performance.",
            }

        if self.has_any(lowered, self.SECURITY_TERMS):
            return {
                "intent": "security_review",
                "label": "Security Review",
                "reason": "Question mentions safety, security, permissions, or credentials.",
            }

        if self.has_any(lowered, self.BUG_TERMS):
            return {
                "intent": "bug_investigation",
                "label": "Bug Investigation",
                "reason": "Question describes broken behavior or an error.",
            }

        if self.has_any(lowered, self.SEARCH_TERMS):
            return {
                "intent": "project_search",
                "label": "Project Search",
                "reason": "Question asks to find or locate something.",
            }

        return {
            "intent": "project_search",
            "label": "Project Search",
            "reason": "No specialized intent matched. Falling back to project search.",
        }

    def has_any(self, text, terms):
        return any(term in text for term in terms)

    def report(self, query):
        result = self.classify(query)
        return (
            "ENGINEER INTENT\n\n"
            f"Intent: {result['label']}\n"
            f"Reason: {result['reason']}"
        )
