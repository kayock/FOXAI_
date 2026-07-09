from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any


@dataclass
class ServiceRecord:
    """
    A registered FOXAI kernel service.
    """
    name: str
    service_type: str
    version: str = "RC1"
    status: str = "READY"
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    detail: str = ""
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self):
        return {
            "name": self.name,
            "service_type": self.service_type,
            "version": self.version,
            "status": self.status,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "detail": self.detail,
            "registered_at": self.registered_at,
        }


class ServiceRegistry:
    """
    Service Registry RC1

    The kernel roster.

    Records what services exist, what they do, and whether they appear ready.
    This is not a department registry; this is for kernel services.
    """

    def __init__(self):
        self.services: Dict[str, ServiceRecord] = {}

    def register(
        self,
        name,
        service_type,
        version="RC1",
        status="READY",
        capabilities=None,
        dependencies=None,
        detail="",
    ):
        record = ServiceRecord(
            name=name,
            service_type=service_type,
            version=version,
            status=status,
            capabilities=capabilities or [],
            dependencies=dependencies or [],
            detail=detail,
        )
        self.services[name] = record
        return record

    def unregister(self, name):
        return self.services.pop(name, None)

    def get(self, name):
        return self.services.get(name)

    def all(self):
        return list(self.services.values())

    def ready_services(self):
        return [service for service in self.all() if service.status.upper() == "READY"]

    def missing_dependencies(self):
        missing = []

        for service in self.all():
            for dependency in service.dependencies:
                if dependency not in self.services:
                    missing.append({
                        "service": service.name,
                        "missing_dependency": dependency,
                    })

        return missing

    def health(self):
        services = self.all()
        missing = self.missing_dependencies()
        ready = self.ready_services()

        return {
            "total_services": len(services),
            "ready_services": len(ready),
            "missing_dependencies": missing,
            "healthy": len(missing) == 0 and len(ready) == len(services),
        }

    def report(self):
        health = self.health()

        lines = [
            "SERVICE REGISTRY REPORT",
            "",
            f"Services Registered: {health['total_services']}",
            f"Services Ready: {health['ready_services']}",
            f"Healthy: {'YES' if health['healthy'] else 'NO'}",
            "",
            "Registered Services:",
        ]

        if not self.services:
            lines.append("• No services registered yet.")
        else:
            for service in self.all():
                lines.append(f"--- {service.name} ---")
                lines.append(f"Type: {service.service_type}")
                lines.append(f"Version: {service.version}")
                lines.append(f"Status: {service.status}")
                if service.capabilities:
                    lines.append("Capabilities:")
                    for capability in service.capabilities:
                        lines.append(f"• {capability}")
                if service.dependencies:
                    lines.append("Dependencies:")
                    for dependency in service.dependencies:
                        lines.append(f"• {dependency}")
                if service.detail:
                    lines.append(f"Detail: {service.detail}")
                lines.append("")

        if health["missing_dependencies"]:
            lines.append("Missing Dependencies:")
            for item in health["missing_dependencies"]:
                lines.append(f"• {item['service']} requires {item['missing_dependency']}")

        lines.extend([
            "",
            "Safety Status:",
            "Service Registry records kernel service metadata only.",
        ])

        return "\n".join(lines)


_registry = None


def get_service_registry():
    global _registry

    if _registry is None:
        _registry = ServiceRegistry()

    return _registry
