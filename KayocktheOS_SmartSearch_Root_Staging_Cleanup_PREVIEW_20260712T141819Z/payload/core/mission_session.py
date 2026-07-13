from __future__ import annotations

"""Stable, receipt-verified mission transcript persistence.

This module is interface-independent. The WebUI is the first caller, while the
desktop Mission Console remains unchanged during this milestone.
"""

from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
from secrets import token_hex
from threading import RLock
from typing import Any

from core.security_containment import make_tool_receipt


class MissionSession:
    """Own one stable archive path for a multi-turn mission session."""

    def __init__(self, foxai_root: str | Path, interface_name: str = "Unknown") -> None:
        self.foxai_root = Path(foxai_root).resolve()
        self.interface_name = (interface_name or "Unknown").strip()
        self._lock = RLock()
        self._session_id: str | None = None
        self._archive_path: Path | None = None
        self._started_at: datetime | None = None
        self._context: dict[str, str] = {}
        self._lines: list[dict[str, str]] = []

    @property
    def active(self) -> bool:
        return self._session_id is not None and self._archive_path is not None

    @property
    def archive_path(self) -> Path | None:
        return self._archive_path

    @property
    def session_id(self) -> str | None:
        return self._session_id

    def _context_key(
        self,
        project: str | None,
        professor: str | None,
        model: str | None,
    ) -> tuple[str, str, str]:
        return (
            (project or "Default_Mission").strip() or "Default_Mission",
            (professor or "Agent Fox").strip() or "Agent Fox",
            (model or "None").strip() or "None",
        )

    def start(
        self,
        *,
        project: str | None = None,
        professor: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Begin a new in-memory session and reserve one stable archive path."""
        with self._lock:
            started = datetime.now()
            project_name, professor_name, model_name = self._context_key(
                project, professor, model
            )
            session_id = f"{started:%Y%m%dT%H%M%S%f}_{token_hex(3)}"
            folder = (
                self.foxai_root
                / "Mission Archive"
                / "Chats"
                / str(started.year)
                / f"{started.month:02d}"
                / f"{started.day:02d}"
            )
            filename = f"{started:%H-%M-%S-%f} WebUI Mission {session_id[-6:]}.md"

            self._session_id = session_id
            self._archive_path = folder / filename
            self._started_at = started
            self._context = {
                "project": project_name,
                "professor": professor_name,
                "model": model_name,
            }
            self._lines = []

            return make_tool_receipt(
                "mission_session.start",
                "verified",
                checks=[
                    {
                        "id": "session_initialized",
                        "ok": self.active,
                        "message": "A stable WebUI mission-session identity was created.",
                    },
                    {
                        "id": "archive_path_scoped",
                        "ok": self._path_is_scoped(self._archive_path),
                        "message": "Reserved path is inside Mission Archive/Chats.",
                    },
                ],
                details={
                    "session_id": self._session_id,
                    "archive_path": str(self._archive_path),
                    "project": project_name,
                    "professor": professor_name,
                    "model": model_name,
                    "file_created": False,
                },
                actor="mission_console",
            )

    def ensure_started(
        self,
        *,
        project: str | None = None,
        professor: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Reuse the current session only while its mission context is unchanged."""
        with self._lock:
            requested = self._context_key(project, professor, model)
            current = (
                self._context.get("project", ""),
                self._context.get("professor", ""),
                self._context.get("model", ""),
            )
            if not self.active or requested != current:
                return self.start(
                    project=project,
                    professor=professor,
                    model=model,
                )
            return make_tool_receipt(
                "mission_session.reuse",
                "verified",
                checks=[
                    {
                        "id": "session_active",
                        "ok": self.active,
                        "message": "Existing mission session remains active.",
                    },
                    {
                        "id": "context_unchanged",
                        "ok": requested == current,
                        "message": "Project, professor, and model context are unchanged.",
                    },
                ],
                details={
                    "session_id": self._session_id,
                    "archive_path": str(self._archive_path),
                },
                actor="mission_console",
            )

    def add(self, speaker: str, text: str) -> None:
        with self._lock:
            if not self.active:
                self.start()
            self._lines.append(
                {
                    "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "speaker": (speaker or "UNKNOWN").strip() or "UNKNOWN",
                    "text": str(text or ""),
                }
            )

    def _path_is_scoped(self, path: Path | None) -> bool:
        if path is None:
            return False
        expected = (self.foxai_root / "Mission Archive" / "Chats").resolve()
        try:
            path.resolve().relative_to(expected)
            return True
        except Exception:
            return False

    def _render(self) -> str:
        started = self._started_at or datetime.now()
        lines = [
            "# FOXAI Mission Archive",
            "",
            f"- Session ID: `{self._session_id or 'unknown'}`",
            f"- Interface: {self.interface_name}",
            f"- Project: {self._context.get('project', 'Default_Mission')}",
            f"- Professor: {self._context.get('professor', 'Agent Fox')}",
            f"- Model: {self._context.get('model', 'None')}",
            f"- Started: {started.isoformat(timespec='seconds')}",
            "",
            "## Transcript",
            "",
        ]
        for item in self._lines:
            lines.extend(
                [
                    f"### {item['speaker']} — {item['time']}",
                    "",
                    item["text"],
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

    def save(self) -> dict[str, Any]:
        """Atomically write, reopen, and hash-verify the complete transcript."""
        with self._lock:
            if not self.active or self._archive_path is None:
                return make_tool_receipt(
                    "mission_archive.write",
                    "failed",
                    checks=[
                        {
                            "id": "session_active",
                            "ok": False,
                            "message": "No mission session is active.",
                        }
                    ],
                    actor="mission_console",
                )
            if not self._lines:
                return make_tool_receipt(
                    "mission_archive.write",
                    "failed",
                    checks=[
                        {
                            "id": "transcript_not_empty",
                            "ok": False,
                            "message": "No transcript lines are available to archive.",
                        }
                    ],
                    details={
                        "session_id": self._session_id,
                        "archive_path": str(self._archive_path),
                    },
                    actor="mission_console",
                )

            path = self._archive_path
            temporary = path.with_name(path.name + ".tmp")
            rendered = self._render()
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary.write_text(rendered, encoding="utf-8")
                os.replace(temporary, path)

                reopened = path.read_text(encoding="utf-8")
                expected_hash = sha256(rendered.encode("utf-8")).hexdigest()
                actual_hash = sha256(reopened.encode("utf-8")).hexdigest()
                path_ok = self._path_is_scoped(path)
                content_ok = reopened == rendered
                hash_ok = expected_hash == actual_hash

                return make_tool_receipt(
                    "mission_archive.write",
                    "verified",
                    checks=[
                        {
                            "id": "archive_path_scoped",
                            "ok": path_ok,
                            "message": "Archive is inside Mission Archive/Chats.",
                        },
                        {
                            "id": "archive_file_readable",
                            "ok": path.is_file(),
                            "message": "Archive file exists and reopened successfully.",
                        },
                        {
                            "id": "archive_content_verified",
                            "ok": content_ok,
                            "message": "Reopened transcript exactly matches the rendered session.",
                        },
                        {
                            "id": "archive_sha256_verified",
                            "ok": hash_ok,
                            "message": "Expected and reopened transcript hashes match.",
                        },
                    ],
                    details={
                        "session_id": self._session_id,
                        "archive_path": str(path),
                        "sha256": actual_hash,
                        "line_count": len(self._lines),
                    },
                    actor="mission_console",
                )
            except Exception as error:
                try:
                    if temporary.exists():
                        temporary.unlink()
                except Exception:
                    pass
                return make_tool_receipt(
                    "mission_archive.write",
                    "failed",
                    checks=[
                        {
                            "id": "archive_write_completed",
                            "ok": False,
                            "message": f"{type(error).__name__}: {error}",
                        }
                    ],
                    details={
                        "session_id": self._session_id,
                        "archive_path": str(path),
                    },
                    actor="mission_console",
                )
