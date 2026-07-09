import json
import re
from datetime import datetime
from pathlib import Path


class ProjectMemory:
    """
    Project Memory RC1

    Persistent engineering memory for FOXAI projects.

    Stores structured project records under:

        Projects/<ProjectName>/
            charter.json
            status.json
            decisions.json
            lessons.json
            forge_log.json

    This module writes only to the Projects folder.
    """

    def __init__(self, root=None):
        self.root = Path(root) if root else Path(__file__).resolve().parents[1]
        self.projects_dir = self.root / "Projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def slug(self, name):
        name = name or "UntitledProject"
        cleaned = re.sub(r"[^A-Za-z0-9]+", "", name)
        return cleaned or "UntitledProject"

    def project_dir(self, project_name):
        path = self.projects_dir / self.slug(project_name)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def read_json(self, path, default):
        if not path.exists():
            return default

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def create_project(self, project_name, charter=None):
        project_path = self.project_dir(project_name)
        now = datetime.now().isoformat(timespec="seconds")

        if charter is None:
            charter = {
                "project_name": project_name,
                "created_at": now,
                "approval_status": "Pending",
            }

        status = {
            "project_name": project_name,
            "created_at": now,
            "last_activity": now,
            "current_phase": "Charter",
            "current_milestone": "Project created",
            "completion_percent": 0,
            "status": "Active",
        }

        self.write_json(project_path / "charter.json", charter)
        self.write_json(project_path / "status.json", status)
        self.write_json(project_path / "decisions.json", [])
        self.write_json(project_path / "lessons.json", [])
        self.write_json(project_path / "forge_log.json", [])

        return project_path

    def ensure_project(self, project_name):
        project_path = self.project_dir(project_name)
        if not (project_path / "status.json").exists():
            self.create_project(project_name)
        return project_path

    def list_projects(self):
        projects = []

        for path in sorted(self.projects_dir.iterdir()):
            if not path.is_dir():
                continue

            status = self.read_json(path / "status.json", {})
            projects.append({
                "name": status.get("project_name", path.name),
                "slug": path.name,
                "status": status.get("status", "Unknown"),
                "phase": status.get("current_phase", "Unknown"),
                "milestone": status.get("current_milestone", "Unknown"),
                "completion_percent": status.get("completion_percent", 0),
                "last_activity": status.get("last_activity", "Unknown"),
            })

        return projects

    def add_decision(self, project_name, title, reason, applies_to=None, status="Active"):
        project_path = self.ensure_project(project_name)
        decisions_path = project_path / "decisions.json"
        decisions = self.read_json(decisions_path, [])

        decision = {
            "decision_id": f"DEC-{len(decisions) + 1:05d}",
            "date": datetime.now().isoformat(timespec="seconds"),
            "title": title,
            "reason": reason,
            "applies_to": applies_to or [],
            "status": status,
            "superseded": False,
        }

        decisions.append(decision)
        self.write_json(decisions_path, decisions)
        self.touch(project_name, phase="Decision Logged", milestone=title)
        return decision

    def add_lesson(self, project_name, lesson, reason="", applies_to=None, source="Forge Journal"):
        project_path = self.ensure_project(project_name)
        lessons_path = project_path / "lessons.json"
        lessons = self.read_json(lessons_path, [])

        item = {
            "lesson_id": f"LESSON-{len(lessons) + 1:05d}",
            "date": datetime.now().isoformat(timespec="seconds"),
            "lesson": lesson,
            "reason": reason,
            "applies_to": applies_to or [],
            "source": source,
        }

        lessons.append(item)
        self.write_json(lessons_path, lessons)
        self.touch(project_name, phase="Lesson Logged", milestone=lesson)
        return item

    def add_forge_entry(self, project_name, entry):
        project_path = self.ensure_project(project_name)
        log_path = project_path / "forge_log.json"
        log = self.read_json(log_path, [])

        entry = dict(entry)
        entry.setdefault("mission_id", f"FM-{datetime.now().strftime('%Y%m%d')}-{len(log) + 1:05d}")
        entry.setdefault("date", datetime.now().isoformat(timespec="seconds"))

        log.append(entry)
        self.write_json(log_path, log)

        self.touch(
            project_name,
            phase=entry.get("phase", "Forge Journal"),
            milestone=entry.get("summary", "Forge entry recorded"),
        )

        return entry

    def touch(self, project_name, phase=None, milestone=None, completion_percent=None):
        project_path = self.ensure_project(project_name)
        status_path = project_path / "status.json"
        status = self.read_json(status_path, {})

        status["last_activity"] = datetime.now().isoformat(timespec="seconds")

        if phase is not None:
            status["current_phase"] = phase

        if milestone is not None:
            status["current_milestone"] = milestone

        if completion_percent is not None:
            status["completion_percent"] = completion_percent

        self.write_json(status_path, status)
        return status

    def report(self):
        projects = self.list_projects()

        lines = [
            "PROJECT MEMORY",
            "",
            f"Projects Folder: {self.projects_dir}",
            f"Projects Tracked: {len(projects)}",
            "",
        ]

        if not projects:
            lines.append("No projects tracked yet.")
        else:
            for project in projects:
                lines.append(f"--- {project['name']} ---")
                lines.append(f"Status: {project['status']}")
                lines.append(f"Phase: {project['phase']}")
                lines.append(f"Milestone: {project['milestone']}")
                lines.append(f"Completion: {project['completion_percent']}%")
                lines.append(f"Last Activity: {project['last_activity']}")
                lines.append("")

        lines.append("Safety Status:")
        lines.append("Project Memory writes only to the Projects folder.")

        return "\n".join(lines)
