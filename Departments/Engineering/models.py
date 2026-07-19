from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

MissionType = Literal["search", "diagnose", "plan", "implement", "repair", "unknown"]
MissionStage = Literal[
    "received",
    "located",
    "inspected",
    "previewed",
    "snapshotted",
    "applied",
    "validated",
    "completed",
    "blocked",
    "rolled_back",
]


@dataclass(slots=True)
class MissionState:
    mission_id: str
    title: str
    mission_type: MissionType
    authorized: bool
    stage: MissionStage = "received"
    project_root: str | None = None
    plan_path: str | None = None
    plan_sha256: str | None = None
    snapshot_path: str | None = None
    receipt_path: str | None = None
    discovered_files: list[str] = field(default_factory=list)
    completed_actions: list[str] = field(default_factory=list)
    outstanding_validations: list[str] = field(default_factory=list)
    blocker: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CommandEvidence:
    name: str
    argv: list[str]
    cwd: str
    started_at: str
    finished_at: str
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FileChangeEvidence:
    action: str
    relative_path: str
    before_sha256: str | None
    after_sha256: str
    before_size: int | None
    after_size: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlanPreview:
    plan_sha256: str
    mission_id: str
    project_root: Path
    changed_paths: list[str]
    diff_text: str
    warnings: list[str] = field(default_factory=list)
