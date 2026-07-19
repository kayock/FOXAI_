from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evidence import sha256_bytes, sha256_json
from .models import FileChangeEvidence, PlanPreview
from .policy import (
    ALLOWED_ACTIONS,
    MAX_TEXT_FILE_BYTES,
    PolicyError,
    ensure_project_root,
    resolve_project_path,
    writable_parent,
)


@dataclass(slots=True)
class PreparedChange:
    action: str
    relative_path: str
    target: Path
    before_text: str
    after_text: str
    existed: bool


class PatchEngine:
    def load_plan(self, plan_path: str | Path) -> tuple[dict[str, Any], str]:
        path = Path(plan_path).expanduser().resolve()
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != "foxai.engineering.plan.v1":
            raise PolicyError("Unsupported or missing plan schema")
        return data, sha256_json(data)

    def prepare(self, plan: dict[str, Any]) -> tuple[Path, list[PreparedChange]]:
        root = ensure_project_root(Path(plan["project_root"]))
        changes = plan.get("changes")
        if not isinstance(changes, list) or not changes:
            raise PolicyError("Plan must contain at least one change")
        prepared: list[PreparedChange] = []
        seen: set[str] = set()

        for item in changes:
            action = item.get("action")
            relative = item.get("path")
            if action not in ALLOWED_ACTIONS:
                raise PolicyError(f"Unsupported action: {action}")
            if not isinstance(relative, str) or not relative:
                raise PolicyError("Each change requires a non-empty relative path")
            if relative in seen:
                raise PolicyError(f"Plan contains duplicate target path: {relative}")
            seen.add(relative)
            target = resolve_project_path(root, relative)
            if not writable_parent(target):
                raise PolicyError(f"Target parent is not writable: {relative}")
            existed = target.exists()
            if existed:
                if not target.is_file():
                    raise PolicyError(f"Target is not a regular file: {relative}")
                if target.stat().st_size > MAX_TEXT_FILE_BYTES:
                    raise PolicyError(f"Target exceeds Workshop V1 text-file limit: {relative}")
                try:
                    before = target.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    raise PolicyError(f"Target is not UTF-8 text: {relative}") from exc
            else:
                before = ""

            if action == "replace_text":
                old = item.get("old")
                new = item.get("new")
                expected = int(item.get("expected_occurrences", 1))
                if not isinstance(old, str) or not isinstance(new, str) or not old:
                    raise PolicyError(f"replace_text requires non-empty old and string new: {relative}")
                actual = before.count(old)
                if actual != expected:
                    raise PolicyError(
                        f"Expected {expected} occurrence(s) in {relative}, found {actual}; no change applied"
                    )
                after = before.replace(old, new)
            else:
                content = item.get("content")
                if not isinstance(content, str):
                    raise PolicyError(f"write_file requires string content: {relative}")
                if item.get("must_not_exist") and existed:
                    raise PolicyError(f"Plan expected a new file, but target exists: {relative}")
                if item.get("must_exist") and not existed:
                    raise PolicyError(f"Plan expected an existing file, but target is missing: {relative}")
                before_hash = item.get("expected_before_sha256")
                if before_hash is not None and sha256_bytes(before.encode("utf-8")) != before_hash:
                    raise PolicyError(f"Existing file hash does not match plan: {relative}")
                after = content

            if before == after:
                raise PolicyError(f"Plan produces no change for: {relative}")
            prepared.append(PreparedChange(action, relative, target, before, after, existed))

        return root, prepared

    def preview(self, plan: dict[str, Any], plan_sha256: str) -> PlanPreview:
        root, prepared = self.prepare(plan)
        chunks: list[str] = []
        for change in prepared:
            chunks.extend(
                difflib.unified_diff(
                    change.before_text.splitlines(keepends=True),
                    change.after_text.splitlines(keepends=True),
                    fromfile=f"a/{change.relative_path}" if change.existed else "/dev/null",
                    tofile=f"b/{change.relative_path}",
                )
            )
        return PlanPreview(
            plan_sha256=plan_sha256,
            mission_id=str(plan.get("mission_id", "unassigned")),
            project_root=root,
            changed_paths=[item.relative_path for item in prepared],
            diff_text="".join(chunks),
        )

    def apply(self, prepared: list[PreparedChange]) -> list[FileChangeEvidence]:
        evidence: list[FileChangeEvidence] = []
        for change in prepared:
            before_bytes = change.before_text.encode("utf-8") if change.existed else None
            after_bytes = change.after_text.encode("utf-8")
            change.target.parent.mkdir(parents=True, exist_ok=True)
            temp = change.target.with_name(change.target.name + ".foxai-write.tmp")
            temp.write_bytes(after_bytes)
            temp.replace(change.target)
            evidence.append(
                FileChangeEvidence(
                    action=change.action,
                    relative_path=change.relative_path,
                    before_sha256=sha256_bytes(before_bytes) if before_bytes is not None else None,
                    after_sha256=sha256_bytes(after_bytes),
                    before_size=len(before_bytes) if before_bytes is not None else None,
                    after_size=len(after_bytes),
                )
            )
        return evidence
