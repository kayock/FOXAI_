from core.workshop_bus import get_bus, WorkshopBus
from core.confidence_engine import ConfidenceEngine
from core.forge_journal import ForgeJournal
from core.project_memory import ProjectMemory
from core.decision_layer import DecisionLayer
from core.service_registry import get_service_registry

try:
    from core.smart_search import SmartSearch
except Exception:
    SmartSearch = None


class FoxAIKernel:
    """
    FOXAI Kernel RC1

    Unified facade for core Workshop services.

    Departments should eventually use this instead of importing every
    subsystem directly.

    Kernel services:
    - Workshop Bus
    - Confidence Engine
    - Forge Journal
    - Project Memory
    - Decision Layer
    - SmartSearch / Evidence Search
    """

    def __init__(self, root=None):
        self.root = root
        self.bus = get_bus()
        self.confidence_engine = ConfidenceEngine()
        self.forge_journal = ForgeJournal(root=root)
        self.project_memory = ProjectMemory(root=root)
        self.decision_layer = DecisionLayer()
        self.smart_search = SmartSearch(root) if (SmartSearch and root) else None
        self.service_registry = get_service_registry()
        self.register_core_services()

    # -------------------------
    # Service Registry
    # -------------------------

    def register_core_services(self):
        self.service_registry.register(
            "Workshop Bus",
            "kernel_service",
            version="RC1",
            capabilities=["publish events", "subscribe handlers", "event history"],
            detail="Kernel event communication backbone.",
        )

        self.service_registry.register(
            "Confidence Engine",
            "kernel_service",
            version="RC1",
            capabilities=["confidence cards", "evidence scoring"],
            detail="Builds explainable confidence reports.",
        )

        self.service_registry.register(
            "Forge Journal",
            "kernel_service",
            version="RC1",
            capabilities=["forge entries", "decisions", "lessons"],
            dependencies=["Project Memory"],
            detail="Persistent engineering journal interface.",
        )

        self.service_registry.register(
            "Project Memory",
            "kernel_service",
            version="RC1",
            capabilities=["project records", "status", "decisions", "lessons", "forge logs"],
            detail="Structured project memory store.",
        )

        self.service_registry.register(
            "Decision Layer",
            "kernel_service",
            version="RC3",
            capabilities=["mission classification", "department recommendation", "execution planning"],
            detail="Strategic mission planning layer.",
        )

        self.service_registry.register(
            "SmartSearch",
            "kernel_service",
            version="RC2" if self.smart_search else "Unavailable",
            status="READY" if self.smart_search else "WARNING",
            capabilities=["evidence-weighted search", "source-first ranking"],
            detail="Available with project root." if self.smart_search else "No project root supplied.",
        )

        self.service_registry.register(
            "Kernel",
            "kernel_core",
            version="RC2",
            capabilities=["service facade", "shared kernel API", "service registry"],
            dependencies=[
                "Workshop Bus",
                "Confidence Engine",
                "Forge Journal",
                "Project Memory",
                "Decision Layer",
            ],
            detail="Unified front door to shared Workshop services.",
        )

    def service_report(self):
        return self.service_registry.report()

    # -------------------------
    # Workshop Bus
    # -------------------------

    def publish(self, event_type, payload=None, source="kernel"):
        return self.bus.publish(event_type, payload or {}, source=source)

    def subscribe(self, event_type, handler):
        return self.bus.subscribe(event_type, handler)

    def bus_report(self):
        return self.bus.report()

    # -------------------------
    # Planning
    # -------------------------

    def plan(self, query, available_models=None, hardware=None):
        self.publish(
            WorkshopBus.INVESTIGATION_STARTED,
            {"query": query, "stage": "decision_layer"},
            source="Kernel",
        )

        report = self.decision_layer.report(
            query,
            available_models=available_models,
            hardware=hardware,
        )

        self.publish(
            WorkshopBus.INVESTIGATION_COMPLETED,
            {"query": query, "stage": "decision_layer"},
            source="Kernel",
        )

        return report

    # -------------------------
    # Evidence / Investigation
    # -------------------------

    def search(self, query, limit=8):
        if not self.smart_search:
            return (
                "KERNEL SEARCH\n\n"
                "SmartSearch is not available because no project root was provided."
            )

        self.publish(
            WorkshopBus.INVESTIGATION_STARTED,
            {"query": query, "stage": "smart_search"},
            source="Kernel",
        )

        report = self.smart_search.format_report(query, limit=limit)

        self.publish(
            WorkshopBus.INVESTIGATION_COMPLETED,
            {"query": query, "stage": "smart_search"},
            source="Kernel",
        )

        return report

    # -------------------------
    # Confidence
    # -------------------------

    def confidence(self, evidence=None, base=50, uncertainty=0, reason=""):
        return self.confidence_engine.card(
            evidence=evidence or [],
            base=base,
            uncertainty=uncertainty,
            reason=reason,
        )

    # -------------------------
    # Memory / Journal
    # -------------------------

    def open_project(self, project_name, charter=None):
        result = self.forge_journal.open_project(project_name, charter=charter)

        self.publish(
            WorkshopBus.PROJECT_OPENED,
            {"project": project_name},
            source="Kernel",
        )

        return result

    def chisel_decision(self, project_name, title, reason, applies_to=None):
        result = self.forge_journal.log_decision(
            project_name,
            title,
            reason,
            applies_to=applies_to or [],
        )

        self.publish(
            WorkshopBus.DECISION_CHISELED,
            {
                "project": project_name,
                "title": title,
                "reason": reason,
            },
            source="Kernel",
        )

        return result

    def record_lesson(self, project_name, lesson, reason="", applies_to=None):
        result = self.forge_journal.log_lesson(
            project_name,
            lesson,
            reason=reason,
            applies_to=applies_to or [],
        )

        self.publish(
            WorkshopBus.LESSON_RECORDED,
            {
                "project": project_name,
                "lesson": lesson,
                "reason": reason,
            },
            source="Kernel",
        )

        return result

    def forge_entry(self, project_name, summary, artifacts=None, lessons=None, next_hammer=""):
        result = self.forge_journal.log_forge(
            project_name,
            summary,
            artifacts=artifacts or [],
            lessons=lessons or [],
            next_hammer=next_hammer,
        )

        self.publish(
            WorkshopBus.FORGE_ENTRY_RECORDED,
            {
                "project": project_name,
                "summary": summary,
                "artifacts": artifacts or [],
                "lessons": lessons or [],
                "next_hammer": next_hammer,
            },
            source="Kernel",
        )

        return result

    def project_memory_report(self):
        return self.project_memory.report()

    # -------------------------
    # Kernel Status
    # -------------------------

    def report(self):
        lines = [
            "FOXAI KERNEL REPORT",
            "",
            "Kernel Services:",
            "✓ Workshop Bus",
            "✓ Confidence Engine",
            "✓ Forge Journal",
            "✓ Project Memory",
            "✓ Decision Layer",
            f"{'✓' if self.smart_search else '⚠'} SmartSearch",
            "✓ Service Registry",
            "",
            "Kernel Principle:",
            "Departments should inherit shared services through the Kernel instead of reimplementing them.",
            "",
            "Service Registry:",
            f"Services Registered: {self.service_registry.health()['total_services']}",
            f"Services Ready: {self.service_registry.health()['ready_services']}",
            "",
            "Workshop Bus:",
            f"Events Stored: {len(self.bus.history)}",
            f"Subscriber Errors: {len(self.bus.errors)}",
            "",
            "Safety Status:",
            "Kernel RC1 exposes shared services only. It does not execute department logic by itself.",
        ]

        return "\n".join(lines)


_kernel = None


def get_kernel(root=None):
    """
    Shared kernel singleton.

    If root is supplied on first call, it is used for project-aware services.
    """
    global _kernel

    if _kernel is None:
        _kernel = FoxAIKernel(root=root)

    return _kernel
