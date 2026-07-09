from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from datetime import datetime
import importlib
import json
import subprocess
import sys
import traceback


@dataclass
class FOXAIBuilder:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.outbox = self.foxai_root / "OpsBridge" / "outbox"
        self.outbox.mkdir(parents=True, exist_ok=True)

    def run_python_script(self, script_name: str) -> dict[str, Any]:
        path = self.foxai_root / script_name
        if not path.exists():
            return {
                "ok": False,
                "step": script_name,
                "status": "missing",
                "message": f"{script_name} not found.",
            }

        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(self.foxai_root),
                text=True,
                capture_output=True,
                timeout=120,
            )
            return {
                "ok": result.returncode == 0,
                "step": script_name,
                "status": "complete" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout_tail": result.stdout[-4000:],
                "stderr_tail": result.stderr[-4000:],
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "step": script_name,
                "status": "timeout",
                "message": str(exc),
            }
        except Exception as exc:
            return {
                "ok": False,
                "step": script_name,
                "status": "error",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }

    def build_captains_log(self) -> dict[str, Any]:
        try:
            from .captains_log import CaptainsLog
            report = CaptainsLog(self.foxai_root).build(limit=50)
            return {"ok": True, "step": "captains_log", "status": "complete", "entry_count": report.get("entry_count")}
        except Exception as exc:
            return {"ok": False, "step": "captains_log", "status": "error", "message": str(exc)}

    def build_bridge_feed(self) -> dict[str, Any]:
        try:
            from .bridge_feed import BridgeFeed
            feed = BridgeFeed(self.foxai_root).build()
            return {
                "ok": True,
                "step": "bridge_feed",
                "status": "complete",
                "department_count": feed.get("summary", {}).get("department_count"),
                "departments_online": feed.get("summary", {}).get("departments_online"),
            }
        except Exception as exc:
            return {"ok": False, "step": "bridge_feed", "status": "error", "message": str(exc), "traceback": traceback.format_exc()}

    def publish_event(self, ok: bool, steps: list[dict[str, Any]]) -> None:
        try:
            from .event_bus import EventBus
            from .captains_log import CaptainsLog
            bus = EventBus(self.foxai_root)
            bus.publish(
                event_type="builder.completed" if ok else "builder.failed",
                source="FOXAI Builder",
                message=f"Builder completed with {'success' if ok else 'attention required'}: {sum(1 for s in steps if s.get('ok'))}/{len(steps)} steps passed.",
                payload={"steps": steps},
                severity="success" if ok else "warning",
                channel="bridge",
            )
            CaptainsLog(self.foxai_root).build(limit=50)
        except Exception:
            pass

    def build_all(self) -> dict[str, Any]:
        started = datetime.now().isoformat(timespec="seconds")

        steps: list[dict[str, Any]] = []

        # These scripts are allowed to be absent; the Builder reports that instead of crashing.
        for script in [
            "ENGINEERING_STATUS.py",
            "COMMISSION_ENGINEERING.py",
            "DEPENDENCY_ARBITER.py",
            "HANGAR_BAY_INVENTORY.py",
            "FOXKERNEL_STATUS.py",
        ]:
            steps.append(self.run_python_script(script))

        steps.append(self.build_captains_log())
        steps.append(self.build_bridge_feed())

        ok = all(step.get("ok") or step.get("status") == "missing" for step in steps)

        report = {
            "ok": ok,
            "service": "FOXAI Builder",
            "version": "Operation Bridge Alive v8.1",
            "started": started,
            "completed": datetime.now().isoformat(timespec="seconds"),
            "root": str(self.foxai_root),
            "steps": steps,
            "passed": sum(1 for s in steps if s.get("ok")),
            "attention": [s for s in steps if not s.get("ok") and s.get("status") != "missing"],
            "missing_optional": [s for s in steps if s.get("status") == "missing"],
        }

        self.write_report(report)
        self.publish_event(ok, steps)

        # Rebuild Captain's Log and Bridge Feed after the builder event.
        self.build_captains_log()
        self.build_bridge_feed()

        return report

    def write_report(self, report: dict[str, Any]) -> None:
        (self.outbox / "builder_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.outbox / "builder_report.txt").write_text(self.render_text(report), encoding="utf-8")

    def render_text(self, report: dict[str, Any]) -> str:
        lines = []
        lines.append("FOXAI Builder Report")
        lines.append("====================")
        lines.append("")
        lines.append(f"OK: {report.get('ok')}")
        lines.append(f"Version: {report.get('version')}")
        lines.append(f"Started: {report.get('started')}")
        lines.append(f"Completed: {report.get('completed')}")
        lines.append(f"Passed: {report.get('passed')}/{len(report.get('steps', []))}")
        lines.append("")
        lines.append("Steps:")
        for step in report.get("steps", []):
            status = step.get("status")
            ok = "PASS" if step.get("ok") else ("SKIP" if status == "missing" else "ATTENTION")
            lines.append(f"- {step.get('step')}: {ok} ({status})")
            if step.get("message"):
                lines.append(f"  {step.get('message')}")
            if step.get("stderr_tail"):
                lines.append("  stderr:")
                for line in step.get("stderr_tail", "").splitlines()[-5:]:
                    lines.append(f"    {line}")
        return "\n".join(lines)
