from datetime import datetime


class BootManager:
    """
    Boot Manager RC1

    Performs a safe startup readiness inspection for FOXAI Kernel services.

    RC1 is read-only:
    - checks that expected services exist
    - checks basic object construction
    - reports department presence
    - does not start or stop services
    """

    def __init__(self, app=None, kernel=None):
        self.app = app
        self.kernel = kernel

    def check(self, name, ok, detail="", action=""):
        return {
            "name": name,
            "ok": bool(ok),
            "detail": detail,
            "action": action,
        }

    def inspect(self):
        checks = []

        checks.append(self.check(
            "Brainstem",
            hasattr(self.app, "brainstem") if self.app else False,
            "Workshop lifecycle manager detected." if self.app and hasattr(self.app, "brainstem") else "Brainstem not attached to app.",
            "Attach Brainstem during app startup."
        ))

        checks.append(self.check(
            "Workshop Bus",
            hasattr(self.kernel, "bus") if self.kernel else False,
            "Workshop Bus available through Kernel." if self.kernel and hasattr(self.kernel, "bus") else "Workshop Bus not available.",
            "Initialize Kernel with Workshop Bus."
        ))

        checks.append(self.check(
            "Decision Layer",
            hasattr(self.kernel, "decision_layer") if self.kernel else False,
            "Decision Layer available through Kernel." if self.kernel and hasattr(self.kernel, "decision_layer") else "Decision Layer not available.",
            "Install/initialize decision_layer.py."
        ))

        checks.append(self.check(
            "Confidence Engine",
            hasattr(self.kernel, "confidence_engine") if self.kernel else False,
            "Confidence Engine available through Kernel." if self.kernel and hasattr(self.kernel, "confidence_engine") else "Confidence Engine not available.",
            "Install/initialize confidence_engine.py."
        ))

        checks.append(self.check(
            "Forge Journal",
            hasattr(self.kernel, "forge_journal") if self.kernel else False,
            "Forge Journal available through Kernel." if self.kernel and hasattr(self.kernel, "forge_journal") else "Forge Journal not available.",
            "Install/initialize forge_journal.py."
        ))

        checks.append(self.check(
            "Project Memory",
            hasattr(self.kernel, "project_memory") if self.kernel else False,
            "Project Memory available through Kernel." if self.kernel and hasattr(self.kernel, "project_memory") else "Project Memory not available.",
            "Install/initialize project_memory.py."
        ))

        checks.append(self.check(
            "SmartSearch",
            bool(getattr(self.kernel, "smart_search", None)) if self.kernel else False,
            "SmartSearch available with project root." if self.kernel and getattr(self.kernel, "smart_search", None) else "SmartSearch missing or no project root supplied.",
            "Initialize Kernel with project root."
        ))

        departments = getattr(self.app, "specialists", {}) if self.app else {}
        checks.append(self.check(
            "Departments",
            bool(departments),
            f"Departments loaded: {', '.join(departments.keys())}" if departments else "No departments loaded.",
            "Load specialists during app startup."
        ))

        passed = sum(1 for item in checks if item["ok"])
        total = len(checks)

        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "passed": passed,
            "total": total,
            "ready": passed == total,
            "checks": checks,
        }

    def report(self):
        data = self.inspect()

        lines = [
            "FOXAI BOOT MANAGER REPORT",
            "",
            f"Timestamp: {data['timestamp']}",
            f"Readiness: {data['passed']}/{data['total']} checks passed",
            f"Kernel Ready: {'YES' if data['ready'] else 'NO'}",
            "",
            "Boot Checks:",
        ]

        for item in data["checks"]:
            symbol = "✓" if item["ok"] else "⚠"
            lines.append(f"{symbol} {item['name']}")
            if item["detail"]:
                lines.append(f"  {item['detail']}")
            if not item["ok"] and item["action"]:
                lines.append(f"  Action: {item['action']}")
            lines.append("")

        lines.extend([
            "Safety Status:",
            "Boot Manager RC1 is read-only. It performs inspection only.",
        ])

        return "\n".join(lines)
