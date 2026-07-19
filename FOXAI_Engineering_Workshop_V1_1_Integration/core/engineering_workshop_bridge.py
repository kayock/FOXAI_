from __future__ import annotations

import json
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from Departments.Engineering.evidence import sha256_json, utc_now, write_json
from Departments.Engineering.workshop import EngineeringWorkshop, WorkshopError
from core.security_containment import (
    authorize_department_route,
    authorize_repair_action,
)


class EngineeringWorkshopBridge:
    """Expose the controlled Engineering Workshop through explicit /engineer commands.

    Ordinary Engineer analysis remains read-only. Project writes are possible only
    through an exact JSON plan that has already been previewed and whose SHA-256 is
    repeated in the operator's exact APPLY confirmation.
    """

    _PREFIX = re.compile(r"^(?:/engineer\s+)?workshop\b", re.IGNORECASE)
    _OPERATORS = {"operator", "human_operator", "eric", "ui_operator"}

    def __init__(self, engineer_agent: Any):
        self.engineer_agent = engineer_agent
        self.project_root = Path(__file__).resolve().parents[1]
        self.data_root = self.project_root / "System" / "EngineeringWorkshop"
        self.workshop = EngineeringWorkshop(self.data_root)
        self.plan_root = self.data_root / "plans"
        self.plan_root.mkdir(parents=True, exist_ok=True)

    def handle(
        self,
        query: str,
        *,
        caller: str = "operator",
        operator_approved: bool = False,
    ) -> str | None:
        text = (query or "").strip()
        match = self._PREFIX.match(text)
        if not match:
            return None
        remainder = text[match.end() :].strip()
        if not remainder or remainder.lower() in {"help", "?"}:
            return self.help_report()

        command, _, payload = remainder.partition(" ")
        command = command.strip().lower()
        payload = payload.strip()

        try:
            if command in {"status", "continue", "resume"}:
                return self.status_report(payload or None)
            if command in {"begin", "stage"}:
                return self.begin_report(payload, caller=caller)
            if command == "locate":
                return self.locate_report(payload, caller=caller)
            if command in {"save-plan", "saveplan"}:
                return self.save_plan_report(payload, caller=caller)
            if command == "preview":
                return self.preview_report(payload, caller=caller)
            if command == "apply":
                return self.apply_report(payload, caller=caller)
            if command == "rollback":
                return self.rollback_report(payload, caller=caller)
            if command == "capabilities":
                return self.capabilities_report()
            return (
                "ENGINEERING WORKSHOP\n\n"
                f"Unknown Workshop command: {command}\n\n"
                + self.help_report()
            )
        except (WorkshopError, ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
            return (
                "ENGINEERING WORKSHOP\n\n"
                "Result: BLOCKED — NOTHING CHANGED\n\n"
                f"{type(exc).__name__}: {exc}"
            )

    def help_report(self) -> str:
        return (
            "ENGINEERING WORKSHOP V1.1\n\n"
            "Ordinary Engineer analysis remains read-only. Controlled project changes "
            "use an exact plan, preview hash, targeted snapshot, explicit approval, "
            "validation, receipt, and rollback on failure.\n\n"
            "Commands:\n"
            "/engineer workshop status\n"
            "/engineer workshop begin TITLE :: IMPLEMENTATION MISSION\n"
            "/engineer workshop locate MISSION-ID :: term one | term two\n"
            "/engineer workshop save-plan MISSION-ID :: {JSON PLAN}\n"
            "/engineer workshop preview \"ABSOLUTE PLAN PATH\"\n"
            "/engineer workshop apply \"ABSOLUTE PLAN PATH\" :: APPLY PLAN-SHA256\n"
            "/engineer workshop rollback MISSION-ID :: ROLLBACK MISSION-ID\n"
            "/engineer workshop capabilities\n\n"
            "No natural-language request is allowed to write files by itself."
        )

    def _authorize_preview(self, caller: str) -> None:
        decision = authorize_department_route(
            caller,
            "engineering_airlock",
            "preview",
            operator_approved=False,
        )
        if not decision.allowed:
            raise WorkshopError(decision.reason)

    def _require_operator(self, caller: str) -> None:
        if (caller or "").strip().lower() not in self._OPERATORS:
            raise WorkshopError("Only the trusted operator UI may control Workshop state")

    def _new_mission_id(self) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"ENG-{stamp}-{uuid4().hex[:6].upper()}"

    def begin_report(self, payload: str, *, caller: str) -> str:
        self._require_operator(caller)
        self._authorize_preview(caller)
        title, sep, mission_text = payload.partition("::")
        if not sep or not title.strip() or not mission_text.strip():
            raise ValueError("Use: workshop begin TITLE :: IMPLEMENTATION MISSION")
        mission_id = self._new_mission_id()
        state = self.workshop.begin_mission(
            mission_id,
            title.strip(),
            mission_text.strip(),
            self.project_root,
        )
        return (
            "ENGINEERING WORKSHOP — MISSION STAGED\n\n"
            f"Mission ID: {state.mission_id}\n"
            f"Title: {state.title}\n"
            f"Route: {state.mission_type}\n"
            f"Explicit implementation authorization detected: {state.authorized}\n"
            f"Project root: {state.project_root}\n"
            f"Stage: {state.stage}\n\n"
            "No project files were changed. Next: locate relevant source or save an exact JSON plan."
        )

    def status_report(self, mission_id: str | None = None) -> str:
        state = (
            self.workshop.state_store.load(self._clean_token(mission_id))
            if mission_id
            else self.workshop.state_store.load_active()
        )
        if state is None:
            return "ENGINEERING WORKSHOP STATUS\n\nNo active mission."
        data = state.to_dict()
        lines = [
            "ENGINEERING WORKSHOP STATUS",
            "",
            f"Mission ID: {data['mission_id']}",
            f"Title: {data['title']}",
            f"Route: {data['mission_type']}",
            f"Authorized: {data['authorized']}",
            f"Stage: {data['stage']}",
            f"Plan SHA-256: {data.get('plan_sha256') or '[none]'}",
            f"Snapshot: {data.get('snapshot_path') or '[none]'}",
            f"Receipt: {data.get('receipt_path') or '[none]'}",
            f"Blocker: {data.get('blocker') or '[none]'}",
        ]
        if data.get("discovered_files"):
            lines.extend(["", "Located source:"])
            lines.extend(f"• {path}" for path in data["discovered_files"][:20])
        if data.get("outstanding_validations"):
            lines.extend(["", "Outstanding validations:"])
            lines.extend(f"• {item}" for item in data["outstanding_validations"])
        return "\n".join(lines)

    def locate_report(self, payload: str, *, caller: str) -> str:
        self._require_operator(caller)
        self._authorize_preview(caller)
        mission_id, sep, terms_text = payload.partition("::")
        mission_id = self._clean_token(mission_id)
        terms = [term.strip() for term in terms_text.split("|") if term.strip()]
        if not sep or not mission_id or not terms:
            raise ValueError("Use: workshop locate MISSION-ID :: term one | term two")
        results = self.workshop.locate(mission_id, terms)
        lines = [
            "ENGINEERING WORKSHOP — LIVE SOURCE DISCOVERY",
            "",
            f"Mission ID: {mission_id}",
            f"Terms: {', '.join(terms)}",
            f"Matches: {len(results)}",
            "",
        ]
        if results:
            for item in results[:30]:
                lines.append(
                    f"• {item['relative_path']} — score {item['score']} ({item['reason']})"
                )
        else:
            lines.append("No matching live source found inside the approved project root.")
        lines.extend(["", "Safety: read-only discovery; no project files changed."])
        return "\n".join(lines)

    def save_plan_report(self, payload: str, *, caller: str) -> str:
        self._require_operator(caller)
        self._authorize_preview(caller)
        mission_id, sep, json_text = payload.partition("::")
        mission_id = self._clean_token(mission_id)
        if not sep or not mission_id or not json_text.strip():
            raise ValueError("Use: workshop save-plan MISSION-ID :: {JSON PLAN}")
        state = self.workshop.state_store.load(mission_id)
        if state is None:
            raise WorkshopError(f"Unknown mission: {mission_id}")
        plan = json.loads(json_text.strip())
        if not isinstance(plan, dict):
            raise ValueError("Plan JSON must be one object")
        supplied_mission = str(plan.get("mission_id") or mission_id)
        if supplied_mission != mission_id:
            raise WorkshopError("Plan mission_id does not match the staged mission")
        plan["schema"] = "foxai.engineering.plan.v1"
        plan["mission_id"] = mission_id
        plan["project_root"] = str(self.project_root)
        mission_dir = self.plan_root / mission_id
        mission_dir.mkdir(parents=True, exist_ok=True)
        plan_sha = sha256_json(plan)
        path = mission_dir / f"{plan_sha}.plan.json"
        write_json(path, plan)
        preview = self.workshop.preview_plan(path)
        return self._format_preview(preview, saved_plan=path)

    def preview_report(self, payload: str, *, caller: str) -> str:
        self._require_operator(caller)
        self._authorize_preview(caller)
        path = self._parse_path(payload)
        preview = self.workshop.preview_plan(path)
        return self._format_preview(preview, saved_plan=path)

    def _format_preview(self, preview: dict[str, Any], *, saved_plan: Path) -> str:
        changed = preview.get("changed_paths") or []
        lines = [
            "ENGINEERING WORKSHOP — EXACT PLAN PREVIEW",
            "",
            f"Mission ID: {preview['mission_id']}",
            f"Plan: {saved_plan}",
            f"Plan SHA-256: {preview['plan_sha256']}",
            f"Diff: {preview['diff_path']}",
            f"Changed paths: {len(changed)}",
        ]
        lines.extend(f"• {path}" for path in changed)
        lines.extend(
            [
                "",
                "Nothing has been applied.",
                "To approve this exact plan, enter:",
                f'/engineer workshop apply "{saved_plan}" :: APPLY {preview["plan_sha256"]}',
            ]
        )
        return "\n".join(lines)

    def apply_report(self, payload: str, *, caller: str) -> str:
        self._require_operator(caller)
        path_text, sep, confirmation = payload.partition("::")
        if not sep:
            raise ValueError(
                'Use: workshop apply "ABSOLUTE PLAN PATH" :: APPLY PLAN-SHA256'
            )
        path = self._parse_path(path_text)
        plan, plan_sha = self.workshop.patch_engine.load_plan(path)
        decision = authorize_repair_action(
            caller,
            "ui_operator",
            confirmation.strip(),
            plan_sha,
        )
        if not decision.allowed:
            raise WorkshopError(decision.reason)
        receipt = self.workshop.apply_plan(path, plan_sha)
        lines = [
            "ENGINEERING WORKSHOP — IMPLEMENTATION RECEIPT",
            "",
            f"Result: {receipt['result']}",
            f"Mission ID: {receipt['mission_id']}",
            f"Plan SHA-256: {receipt['plan_sha256']}",
            f"Snapshot: {receipt['snapshot_path']}",
            f"Snapshot SHA-256: {receipt['snapshot_sha256']}",
            f"Receipt: {receipt['receipt_path']}",
            f"Rolled back: {receipt['rolled_back']}",
            f"Changes recorded: {len(receipt.get('changes') or [])}",
            f"Validations recorded: {len(receipt.get('validations') or [])}",
        ]
        if receipt.get("failure"):
            lines.extend(["", f"Failure: {receipt['failure']}"])
        return "\n".join(lines)

    def rollback_report(self, payload: str, *, caller: str) -> str:
        self._require_operator(caller)
        mission_text, sep, confirmation = payload.partition("::")
        mission_id = self._clean_token(mission_text)
        expected = f"ROLLBACK {mission_id}".upper()
        if not sep or confirmation.strip().upper() != expected:
            raise WorkshopError(f"Exact confirmation required: {expected}")
        result = self.workshop.rollback(mission_id)
        return (
            "ENGINEERING WORKSHOP — ROLLBACK RECEIPT\n\n"
            f"Mission ID: {result['mission_id']}\n"
            f"Result: {result['result']}\n"
            f"Snapshot: {result['snapshot_path']}\n"
            f"Restored paths: {len(result.get('restored_paths') or [])}\n"
            f"Completed: {result['completed_at']}"
        )

    def capabilities_report(self) -> str:
        capabilities = self.workshop.capabilities(self.project_root)
        return (
            "ENGINEERING WORKSHOP CAPABILITIES\n\n"
            + json.dumps(capabilities, indent=2, sort_keys=True)
        )

    @staticmethod
    def _clean_token(value: str | None) -> str:
        return (value or "").strip().strip('"').strip("'")

    @staticmethod
    def _parse_path(value: str) -> Path:
        text = value.strip()
        if not text:
            raise ValueError("No plan path supplied")
        try:
            parts = shlex.split(text, posix=False)
        except ValueError as exc:
            raise ValueError(f"Invalid quoted path: {exc}") from exc
        if len(parts) != 1:
            raise ValueError("Supply exactly one absolute plan path")
        cleaned = parts[0].strip().strip('"').strip("'")
        path = Path(cleaned).expanduser().resolve(strict=False)
        if not path.exists() or not path.is_file():
            raise ValueError(f"Plan file does not exist: {path}")
        return path
