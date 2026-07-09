from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import time
import traceback

from .fleet_command_bridge import FleetCommandBridge


@dataclass
class OPSBridge:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.commander = FleetCommandBridge(self.foxai_root)

    @property
    def outbox(self) -> Path:
        path = self.foxai_root / "OpsBridge" / "outbox"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def inbox(self) -> Path:
        path = self.foxai_root / "OpsBridge" / "inbox"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def execute_text(self, request: str, mode: str = "safe") -> dict[str, Any]:
        started = time.perf_counter()

        try:
            report = self.commander.command(request, mode=mode)
            text = self.commander.render_text(report)
            result = {
                "ok": bool(report.get("ok")),
                "bridge": "FOXAI OPS Bridge",
                "version": "CM v5.0",
                "request": request,
                "mode": mode,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "report": report,
                "text": text,
                "error": "",
            }
        except Exception as exc:
            result = {
                "ok": False,
                "bridge": "FOXAI OPS Bridge",
                "version": "CM v5.0",
                "request": request,
                "mode": mode,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "report": None,
                "text": f"FOXAI OPS Bridge error: {exc}",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

        self.write_latest(result)
        return result

    def write_latest(self, result: dict[str, Any]) -> None:
        latest_json = self.outbox / "latest_result.json"
        latest_txt = self.outbox / "latest_result.txt"

        latest_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        latest_txt.write_text(result.get("text", ""), encoding="utf-8")

        stamp = time.strftime("%Y%m%d_%H%M%S")
        archive_json = self.outbox / f"result_{stamp}.json"
        archive_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "bridge": "FOXAI OPS Bridge",
            "version": "CM v5.0",
            "inbox": str(self.inbox),
            "outbox": str(self.outbox),
            "latest_json": str(self.outbox / "latest_result.json"),
            "latest_txt": str(self.outbox / "latest_result.txt"),
        }
