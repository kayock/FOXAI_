from datetime import datetime

from core.project_memory import ProjectMemory


class ForgeJournal:
    """
    Forge Journal RC1

    Human-readable project memory interface.

    Records:
    - forge entries
    - engineering decisions
    - lessons learned
    """

    def __init__(self, root=None):
        self.memory = ProjectMemory(root=root)

    def open_project(self, project_name, charter=None):
        path = self.memory.create_project(project_name, charter=charter)
        return (
            "FORGE JOURNAL\n\n"
            f"Project opened:\n{project_name}\n\n"
            f"Path:\n{path}\n\n"
            "Memory tablets created:\n"
            "• charter.json\n"
            "• status.json\n"
            "• decisions.json\n"
            "• lessons.json\n"
            "• forge_log.json"
        )

    def log_forge(self, project_name, summary, artifacts=None, lessons=None, next_hammer=""):
        entry = self.memory.add_forge_entry(project_name, {
            "project": project_name,
            "summary": summary,
            "phase": "Forge Logged",
            "artifacts": artifacts or [],
            "lessons": lessons or [],
            "next_hammer": next_hammer,
            "result": "Recorded",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })

        for lesson in lessons or []:
            self.memory.add_lesson(
                project_name,
                lesson=lesson,
                reason="Recorded during forge session.",
                source=entry["mission_id"],
            )

        lines = [
            "FORGE JOURNAL ENTRY RECORDED",
            "",
            f"Project: {project_name}",
            f"Mission ID: {entry['mission_id']}",
            f"Summary: {summary}",
            "",
            "Artifacts:",
        ]

        lines.extend([f"• {item}" for item in (artifacts or [])] or ["• None listed"])

        lines.extend([
            "",
            "Lessons:",
        ])

        lines.extend([f"• {item}" for item in (lessons or [])] or ["• None listed"])

        lines.extend([
            "",
            f"Next Hammer Strike: {next_hammer or 'Not specified'}",
        ])

        return "\n".join(lines)

    def log_decision(self, project_name, title, reason, applies_to=None):
        decision = self.memory.add_decision(
            project_name,
            title=title,
            reason=reason,
            applies_to=applies_to or [],
        )

        return (
            "DECISION TABLET CHISELED\n\n"
            f"Project: {project_name}\n"
            f"Decision ID: {decision['decision_id']}\n"
            f"Title: {title}\n\n"
            f"Reason:\n{reason}"
        )

    def log_lesson(self, project_name, lesson, reason="", applies_to=None):
        item = self.memory.add_lesson(
            project_name,
            lesson=lesson,
            reason=reason,
            applies_to=applies_to or [],
        )

        return (
            "LESSON TABLET CHISELED\n\n"
            f"Project: {project_name}\n"
            f"Lesson ID: {item['lesson_id']}\n"
            f"Lesson: {lesson}\n\n"
            f"Reason:\n{reason or 'Not specified'}"
        )

    def report(self):
        return self.memory.report()
