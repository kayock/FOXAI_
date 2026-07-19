from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from .evidence import utc_now
from .models import CommandEvidence
from .policy import (
    DEFAULT_COMMAND_TIMEOUT_SECONDS,
    MAX_COMMAND_OUTPUT_CHARS,
    PolicyError,
    ensure_project_root,
    is_within,
)


class Validator:
    def run(self, project_root: str | Path, validations: list[dict[str, Any]]) -> list[CommandEvidence]:
        root = ensure_project_root(Path(project_root))
        results: list[CommandEvidence] = []
        for index, item in enumerate(validations):
            name = str(item.get("name") or f"validation-{index + 1}")
            argv = item.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
                raise PolicyError(f"Validation {name} must use a non-empty argv string list")
            cwd_rel = str(item.get("cwd") or ".")
            cwd = (root / cwd_rel).resolve(strict=False)
            if not is_within(cwd, root) or not cwd.exists() or not cwd.is_dir():
                raise PolicyError(f"Validation cwd is outside or missing from project root: {cwd_rel}")
            timeout = int(item.get("timeout_seconds", DEFAULT_COMMAND_TIMEOUT_SECONDS))
            env = os.environ.copy()
            env["PYTHONNOUSERSITE"] = "1"
            started = utc_now()
            timed_out = False
            try:
                completed = subprocess.run(
                    argv,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=False,
                    env=env,
                )
                returncode = completed.returncode
                stdout = completed.stdout[-MAX_COMMAND_OUTPUT_CHARS:]
                stderr = completed.stderr[-MAX_COMMAND_OUTPUT_CHARS:]
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                returncode = 124
                stdout = (exc.stdout or "")[-MAX_COMMAND_OUTPUT_CHARS:]
                stderr = ((exc.stderr or "") + f"\nTimed out after {timeout} seconds")[-MAX_COMMAND_OUTPUT_CHARS:]
            results.append(
                CommandEvidence(
                    name=name,
                    argv=argv,
                    cwd=str(cwd),
                    started_at=started,
                    finished_at=utc_now(),
                    returncode=returncode,
                    stdout=stdout,
                    stderr=stderr,
                    timed_out=timed_out,
                )
            )
            if returncode != 0:
                break
        return results
