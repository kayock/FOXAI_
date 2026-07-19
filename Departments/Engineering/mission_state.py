from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import MissionState


class MissionStateStore:
    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir).expanduser().resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.active_pointer = self.state_dir / "active_mission.json"

    def _path(self, mission_id: str) -> Path:
        safe = "".join(ch for ch in mission_id if ch.isalnum() or ch in "-_")
        if not safe:
            raise ValueError("mission_id must contain at least one safe character")
        return self.state_dir / f"{safe}.json"

    def save(self, state: MissionState) -> Path:
        path = self._path(state.mission_id)
        payload = state.to_dict()
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self.active_pointer.write_text(
            json.dumps({"mission_id": state.mission_id}, indent=2), encoding="utf-8"
        )
        return path

    def load(self, mission_id: str) -> MissionState | None:
        path = self._path(mission_id)
        if not path.exists():
            return None
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return MissionState(**data)

    def load_active(self) -> MissionState | None:
        if not self.active_pointer.exists():
            return None
        data = json.loads(self.active_pointer.read_text(encoding="utf-8"))
        mission_id = data.get("mission_id")
        return self.load(str(mission_id)) if mission_id else None

    def clear_active(self) -> None:
        self.active_pointer.unlink(missing_ok=True)
