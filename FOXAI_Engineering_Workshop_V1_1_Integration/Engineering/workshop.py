from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .evidence import sha256_file, utc_now, write_json
from .mission_router import RouteDecision, classify_mission
from .mission_state import MissionStateStore
from .models import MissionState
from .patch_engine import PatchEngine
from .policy import PolicyError, ensure_project_root
from .snapshot import SnapshotManager
from .source_locator import SourceLocator
from .validator import Validator


class WorkshopError(RuntimeError):
    """A truthful, operator-facing Workshop failure."""


class EngineeringWorkshop:
    def __init__(self, data_root: str | Path):
        self.data_root = Path(data_root).expanduser().resolve()
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.state_store = MissionStateStore(self.data_root / "missions")
        self.snapshot_manager = SnapshotManager(self.data_root / "snapshots")
        self.patch_engine = PatchEngine()
        self.validator = Validator()
        self.source_locator = SourceLocator()
        self.receipt_root = self.data_root / "receipts"
        self.preview_root = self.data_root / "previews"
        self.receipt_root.mkdir(parents=True, exist_ok=True)
        self.preview_root.mkdir(parents=True, exist_ok=True)

    def capabilities(self, project_root: str | Path | None = None) -> dict[str, Any]:
        result = {
            "read_files": True,
            "write_state": os.access(self.data_root, os.W_OK),
            "create_snapshots": os.access(self.data_root / "snapshots", os.W_OK),
            "run_local_commands": True,
            "write_project": None,
            "implementation_available": False,
        }
        if project_root is not None:
            root = ensure_project_root(Path(project_root))
            result["write_project"] = os.access(root, os.W_OK)
        result["implementation_available"] = bool(
            result["write_state"]
            and result["create_snapshots"]
            and result["run_local_commands"]
            and (result["write_project"] is not False)
        )
        return result

    def route(self, text: str) -> RouteDecision:
        return classify_mission(text, self.state_store.load_active())

    def begin_mission(
        self,
        mission_id: str,
        title: str,
        text: str,
        project_root: str | Path | None = None,
    ) -> MissionState:
        decision = classify_mission(text, self.state_store.load_active())
        state = MissionState(
            mission_id=mission_id,
            title=title,
            mission_type=decision.mission_type,
            authorized=decision.authorized,
            project_root=str(Path(project_root).resolve()) if project_root else None,
        )
        self.state_store.save(state)
        return state

    def locate(self, mission_id: str, terms: list[str]) -> list[dict[str, Any]]:
        state = self._require_state(mission_id)
        if not state.project_root:
            raise WorkshopError("Mission has no approved project root")
        located = self.source_locator.locate(state.project_root, terms)
        state.discovered_files = [item.relative_path for item in located]
        state.stage = "located"
        state.completed_actions.append("live source discovery completed")
        self.state_store.save(state)
        return [
            {
                "relative_path": item.relative_path,
                "score": item.score,
                "reason": item.reason,
            }
            for item in located
        ]

    def preview_plan(self, plan_path: str | Path) -> dict[str, Any]:
        plan, plan_sha = self.patch_engine.load_plan(plan_path)
        mission_id = str(plan.get("mission_id") or "")
        state = self._require_state(mission_id)
        if state.mission_type not in {"implement", "repair"}:
            raise WorkshopError(
                f"Mission route is {state.mission_type}; implementation preview is unavailable for this route"
            )
        if not state.authorized:
            raise WorkshopError("Mission does not contain explicit implementation authorization")
        preview = self.patch_engine.preview(plan, plan_sha)
        capabilities = self.capabilities(preview.project_root)
        if not capabilities["implementation_available"]:
            state.stage = "blocked"
            state.blocker = (
                "Implementation is unavailable in this interface. Only read-only project search "
                "or analysis is available."
            )
            self.state_store.save(state)
            raise WorkshopError(state.blocker)

        preview_dir = self.preview_root / mission_id
        preview_dir.mkdir(parents=True, exist_ok=True)
        diff_path = preview_dir / f"{plan_sha}.diff"
        diff_path.write_text(preview.diff_text, encoding="utf-8")
        preview_json = preview_dir / f"{plan_sha}.json"
        write_json(
            preview_json,
            {
                "mission_id": mission_id,
                "plan_path": str(Path(plan_path).resolve()),
                "plan_sha256": plan_sha,
                "project_root": str(preview.project_root),
                "changed_paths": preview.changed_paths,
                "diff_path": str(diff_path),
                "capabilities": capabilities,
                "created_at": utc_now(),
            },
        )
        state.stage = "previewed"
        state.project_root = str(preview.project_root)
        state.plan_path = str(Path(plan_path).resolve())
        state.plan_sha256 = plan_sha
        state.completed_actions.append("exact plan preview generated")
        state.outstanding_validations = [str(v.get("name", "validation")) for v in plan.get("validations", [])]
        self.state_store.save(state)
        return json.loads(preview_json.read_text(encoding="utf-8"))

    def apply_plan(self, plan_path: str | Path, approval_sha256: str) -> dict[str, Any]:
        plan, plan_sha = self.patch_engine.load_plan(plan_path)
        mission_id = str(plan.get("mission_id") or "")
        state = self._require_state(mission_id)
        if approval_sha256 != plan_sha:
            raise WorkshopError("Approval hash does not match the exact plan; nothing was changed")
        if state.stage != "previewed" or state.plan_sha256 != plan_sha:
            raise WorkshopError("The exact plan must be previewed before it can be applied")
        if not state.authorized or state.mission_type not in {"implement", "repair"}:
            raise WorkshopError("Mission is not authorized for controlled implementation")

        root, prepared = self.patch_engine.prepare(plan)
        snapshot = self.snapshot_manager.create(
            mission_id,
            root,
            [item.relative_path for item in prepared],
        )
        state.snapshot_path = str(snapshot.snapshot_zip)
        state.stage = "snapshotted"
        state.completed_actions.append("practical snapshot created")
        self.state_store.save(state)

        changes = []
        validations = []
        rolled_back = False
        failure: str | None = None
        try:
            changes = [item.to_dict() for item in self.patch_engine.apply(prepared)]
            state.stage = "applied"
            state.completed_actions.append("approved exact plan applied atomically")
            self.state_store.save(state)
            validation_items = plan.get("validations") or []
            validations = [item.to_dict() for item in self.validator.run(root, validation_items)]
            failed = next((item for item in validations if item["returncode"] != 0), None)
            if failed:
                failure = f"Validation failed: {failed['name']} (return code {failed['returncode']})"
                self.snapshot_manager.restore(snapshot.snapshot_zip, root)
                rolled_back = True
                state.stage = "rolled_back"
                state.blocker = failure
                state.completed_actions.append("validation failed; snapshot restored")
            else:
                state.stage = "validated"
                state.completed_actions.append("all approved validations passed")
        except Exception as exc:
            failure = f"Implementation error: {type(exc).__name__}: {exc}"
            self.snapshot_manager.restore(snapshot.snapshot_zip, root)
            rolled_back = True
            state.stage = "rolled_back"
            state.blocker = failure
            state.completed_actions.append("implementation error; snapshot restored")

        receipt = {
            "schema": "foxai.engineering.receipt.v1",
            "mission_id": mission_id,
            "mission_title": state.title,
            "mission_type": state.mission_type,
            "authorized": state.authorized,
            "result": "rolled_back" if rolled_back else "applied_verified",
            "created_at": utc_now(),
            "project_root": str(root),
            "plan_path": str(Path(plan_path).resolve()),
            "plan_sha256": plan_sha,
            "snapshot_path": str(snapshot.snapshot_zip),
            "snapshot_sha256": snapshot.snapshot_sha256,
            "snapshot_manifest": str(snapshot.manifest_path),
            "changes": changes,
            "validations": validations,
            "rolled_back": rolled_back,
            "failure": failure,
            "no_deletions": True,
            "no_renames": True,
            "evidence_is_tool_generated": True,
        }
        receipt_dir = self.receipt_root / mission_id
        receipt_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = receipt_dir / f"{plan_sha}.receipt.json"
        write_json(receipt_path, receipt)
        receipt["receipt_path"] = str(receipt_path)
        state.receipt_path = str(receipt_path)
        if not rolled_back:
            state.stage = "completed"
            state.outstanding_validations = []
        self.state_store.save(state)
        return receipt

    def rollback(self, mission_id: str) -> dict[str, Any]:
        state = self._require_state(mission_id)
        if not state.snapshot_path or not state.project_root:
            raise WorkshopError("Mission has no snapshot available for rollback")
        restored = self.snapshot_manager.restore(state.snapshot_path, state.project_root)
        state.stage = "rolled_back"
        state.completed_actions.append("operator-requested rollback completed")
        self.state_store.save(state)
        return {
            "mission_id": mission_id,
            "result": "rolled_back",
            "snapshot_path": state.snapshot_path,
            "restored_paths": restored,
            "completed_at": utc_now(),
        }

    def _require_state(self, mission_id: str) -> MissionState:
        state = self.state_store.load(mission_id)
        if state is None:
            raise WorkshopError(f"Unknown mission: {mission_id}")
        return state
