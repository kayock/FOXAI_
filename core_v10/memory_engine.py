from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@dataclass
class MemoryEngine:
    project_path: Path

    @property
    def memory_root(self) -> Path:
        path = self.project_path / "Memory"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def ensure(self) -> None:
        for filename in ["facts.json", "decisions.json", "questions.json", "discoveries.json", "objectives.json", "tasks.json"]:
            path = self.memory_root / filename
            if not path.exists():
                write_json(path, [])

        mission = self.memory_root / "mission.md"
        if not mission.exists():
            mission.write_text(
                f"# Mission Intelligence: {self.project_path.name}\n\n"
                f"Created: {now()}\n\n"
                "## Mission Purpose\n\nDescribe what this project is trying to accomplish.\n\n",
                encoding="utf-8",
            )

        session_log = self.memory_root / "session_log.md"
        if not session_log.exists():
            session_log.write_text(f"# Session Log: {self.project_path.name}\n\n", encoding="utf-8")

        transcript = self.memory_root / "chat_transcript.md"
        if not transcript.exists():
            transcript.write_text(f"# Chat Transcript: {self.project_path.name}\n\n", encoding="utf-8")

    def append_md(self, filename: str, text: str) -> None:
        self.ensure()
        with (self.memory_root / filename).open("a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n\n")

    def event(self, event: str) -> None:
        self.append_md("session_log.md", f"## {now()}\n\n{event}")

    def chat(self, speaker: str, content: str) -> None:
        trimmed = content.strip()
        if len(trimmed) > 5000:
            trimmed = trimmed[:5000] + "\n...[trimmed]"
        self.append_md("chat_transcript.md", f"### {now()} — {speaker}\n\n{trimmed}")

    def add_item(self, kind: str, text: str) -> dict:
        allowed = {
            "fact": "facts.json",
            "decision": "decisions.json",
            "question": "questions.json",
            "discovery": "discoveries.json",
            "objective": "objectives.json",
            "task": "tasks.json",
        }
        filename = allowed.get(kind)
        if not filename:
            return {"ok": False, "message": f"Unknown memory type: {kind}"}
        value = text.strip()
        if not value:
            return {"ok": False, "message": "Empty memory item."}
        items = read_json(self.memory_root / filename, [])
        items.append({"time": now(), "text": value, "done": False if kind == "task" else None})
        write_json(self.memory_root / filename, items[-500:])
        self.event(f"Memory added ({kind}): {value}")
        return {"ok": True, "message": f"Saved {kind}."}

    def build_context(self, professor_name: str, model_name: str | None) -> str:
        self.ensure()

        def tail_file(filename: str, limit: int = 3000) -> str:
            path = self.memory_root / filename
            if path.exists():
                return path.read_text(encoding="utf-8", errors="replace")[-limit:]
            return ""

        facts = read_json(self.memory_root / "facts.json", [])
        decisions = read_json(self.memory_root / "decisions.json", [])
        questions = read_json(self.memory_root / "questions.json", [])
        discoveries = read_json(self.memory_root / "discoveries.json", [])
        objectives = read_json(self.memory_root / "objectives.json", [])
        tasks = read_json(self.memory_root / "tasks.json", [])

        notes_path = self.project_path / "FOXAI_PROJECT_NOTES.md"
        notes = notes_path.read_text(encoding="utf-8", errors="replace")[-3000:] if notes_path.exists() else ""

        parts: list[str] = []
        parts.append("MISSION INTELLIGENCE v10")
        parts.append(f"Project: {self.project_path.name}")
        parts.append(f"Professor: {professor_name}")
        parts.append(f"Model: {model_name or 'None'}")

        for title, items in [
            ("Objectives", objectives),
            ("Open Tasks", [t for t in tasks if not t.get("done")]),
            ("Known Facts", facts),
            ("Decisions", decisions),
            ("Discoveries", discoveries),
            ("Open Questions", questions),
        ]:
            if items:
                parts.append(f"\n{title}:")
                for item in items[-10:]:
                    parts.append(f"- {item.get('text', item) if isinstance(item, dict) else item}")

        mission = tail_file("mission.md")
        log = tail_file("session_log.md")
        transcript = tail_file("chat_transcript.md", 2500)

        if notes:
            parts.append("\nProject Notes:")
            parts.append(notes)
        if mission:
            parts.append("\nMission Brief:")
            parts.append(mission)
        if log:
            parts.append("\nRecent Session Log:")
            parts.append(log)
        if transcript:
            parts.append("\nRecent Chat Transcript:")
            parts.append(transcript)

        parts.append(
            "\nInstruction: This is real disk-backed memory supplied by FOXAI. Use it directly. "
            "Do not claim you lack memory if the answer is present here."
        )
        return "\n".join(parts)
