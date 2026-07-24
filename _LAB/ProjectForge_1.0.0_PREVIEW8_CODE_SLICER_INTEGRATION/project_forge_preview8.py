from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import py_compile
import queue
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable

from code_slicer_v1 import CodeSlicer

APP_NAME = "Project Forge Preview 8 — Code Slicer Integration"
APP_VERSION = "1.0.0-preview8"
TARGET_FILE = "dirty_python_lab.py"
DEFAULT_MODEL_ID = r"Z:\FOXAI\Models\Chat\Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
DEFAULT_ENDPOINT = "http://127.0.0.1:8080/v1"
DEFAULT_SOURCE = r"Z:\FOXAI\_LAB\DirtyPythonLab"
DEFAULT_WORKSPACES = r"Z:\FOXAI\_LAB\ProjectForge\Preview8Workspaces"
DEFAULT_TASK = """Improve Dirty Python Lab so long local-model requests cannot leave the browser with an unexplained Failed to fetch message.

Acceptance requirements:
- The browser run request must return quickly and long generation/repair work must continue as a background job.
- The page must poll and visibly show stages such as generating, running, repairing, and finished.
- Every run must record the exact model ID reported by /v1/models.
- Every run must maintain an append-only progress log.
- RESULT.json must always be written, including endpoint errors, model timeouts, execution timeouts, and exhausted repairs.
- Preserve the current disposable run folders and no-overwrite behavior.
- Use Python standard library only. Do not add tkinter or third-party runtime packages.
- Update or add automated tests for the new behavior.
- Run the complete test suite and keep repairing until it passes."""
DEFAULT_SEED_SYMBOLS = [
    "DirtyPythonLabEngine",
    "LabApplication",
    "LabRequestHandler",
    "run_code_in_background",
    "handle_run_request",
    "handle_poll_request",
    "save_result",
    "main",
]


class ForgeError(RuntimeError):
    pass


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat()


def stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def random_id() -> str:
    return uuid.uuid4().hex[:8].upper()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 300,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
        return {
            "command": command,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_seconds": round(time.monotonic() - started, 3),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + f"\nTimed out after {timeout} seconds.",
            "duration_seconds": round(time.monotonic() - started, 3),
            "timed_out": True,
        }


def tree_manifest(root: Path, excludes: Iterable[str] = ()) -> dict[str, str]:
    excluded = set(excludes)
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if any(rel == item or rel.startswith(item.rstrip("/") + "/") for item in excluded):
            continue
        result[rel] = sha256_file(path)
    return result


def changed_manifest(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))


def safe_slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return value[:100] or "symbol"


def split_name_tokens(name: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name.replace(".", " ").replace("_", " "))
    return [item.lower() for item in re.findall(r"[A-Za-z0-9]+", spaced) if len(item) > 1]


@dataclasses.dataclass
class ForgeConfig:
    source_root: str = DEFAULT_SOURCE
    workspace_root: str = DEFAULT_WORKSPACES
    endpoint: str = DEFAULT_ENDPOINT
    model_id: str = DEFAULT_MODEL_ID
    context_limit: int = 16384
    output_limit: int = 4096
    target_file: str = TARGET_FILE
    max_rounds: int = 3
    opencode_timeout_seconds: int = 900
    test_timeout_seconds: int = 300
    initial_symbol_limit: int = 14
    repair_symbol_limit: int = 10
    seed_symbols: list[str] = dataclasses.field(default_factory=lambda: list(DEFAULT_SEED_SYMBOLS))
    opencode_command: list[str] = dataclasses.field(default_factory=lambda: ["opencode"])
    test_commands: list[list[str]] = dataclasses.field(
        default_factory=lambda: [["{python}", "-m", "unittest", "discover", "-s", "tests", "-v"]]
    )
    host: str = "127.0.0.1"
    port: int = 8788

    @classmethod
    def load(cls, path: Path) -> "ForgeConfig":
        payload = read_json(path, {}) or {}
        known = {field.name for field in dataclasses.fields(cls)}
        return cls(**{key: value for key, value in payload.items() if key in known})

    def with_overrides(self, **values: Any) -> "ForgeConfig":
        current = dataclasses.asdict(self)
        current.update({key: value for key, value in values.items() if value is not None})
        return ForgeConfig(**current)


class StatusStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: dict[str, Any] = {
            "busy": False,
            "stage": "idle",
            "message": "Ready. Preview 7 is not used.",
            "details": [],
            "error": "",
            "workspace": "",
            "latest_patch": "",
            "latest_receipt": "",
            "source_root": DEFAULT_SOURCE,
            "updated_at": now_iso(),
            "stop_requested": False,
        }

    def update(self, **values: Any) -> None:
        with self._lock:
            self._data.update(values)
            self._data["updated_at"] = now_iso()

    def add_detail(self, message: str) -> None:
        with self._lock:
            details = list(self._data.get("details") or [])
            details.append(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {message}")
            self._data["details"] = details[-250:]
            self._data["updated_at"] = now_iso()

    def get(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))


class SurgicalForge:
    def __init__(self, config: ForgeConfig, status: StatusStore | None = None) -> None:
        self.config = config
        self.status = status or StatusStore()
        self.current_workspace: Path | None = None
        self.current_project: Path | None = None
        self.current_patch: Path | None = None
        self.baseline_commit: str | None = None
        self._active_process: subprocess.Popen[str] | None = None
        self._process_lock = threading.RLock()

    def _set_stage(self, stage: str, message: str) -> None:
        self.status.update(stage=stage, message=message)
        self.status.add_detail(message)

    def _source(self, override: str | None = None) -> Path:
        return Path(override or self.config.source_root).expanduser().resolve()

    def _workspace_root(self) -> Path:
        return Path(self.config.workspace_root).expanduser().resolve()

    def _target(self, project: Path) -> Path:
        return project / self.config.target_file

    def _validate_source(self, source: Path) -> None:
        if not source.exists() or not source.is_dir():
            raise ForgeError(f"Source project folder not found: {source}")
        target = source / self.config.target_file
        if not target.exists() or not target.is_file():
            raise ForgeError(f"Required target file not found: {target}")

    def _load_tests_text(self, source: Path) -> str:
        chunks: list[str] = []
        tests = source / "tests"
        if tests.exists():
            for path in sorted(tests.rglob("*.py")):
                try:
                    chunks.append(path.read_text(encoding="utf-8"))
                except OSError:
                    continue
        return "\n".join(chunks)

    def _select_symbols(
        self,
        slicer: CodeSlicer,
        task: str,
        project_root: Path,
        *,
        failure_text: str = "",
        extra_names: Iterable[str] = (),
        limit: int | None = None,
    ) -> list[str]:
        symbols = slicer.get_symbol_map()
        if not symbols:
            return []
        corpus = "\n".join([task, self._load_tests_text(project_root), failure_text]).lower()
        requested = {name.lower() for name in [*self.config.seed_symbols, *extra_names] if name}
        line_numbers = {int(value) for value in re.findall(r"line\s+(\d+)", failure_text, re.I)}
        scored: list[tuple[int, int, str]] = []
        for index, symbol in enumerate(symbols):
            name = str(symbol["name"])
            qualified = str(symbol["qualified_name"])
            score = 0
            if name.lower() in requested or qualified.lower() in requested:
                score += 200
            if re.search(rf"\b{re.escape(name.lower())}\b", corpus):
                score += 90
            if qualified.lower() in corpus:
                score += 120
            for token in split_name_tokens(qualified):
                score += min(corpus.count(token), 8) * 4
            start = int(symbol["start_line"])
            end = int(symbol["end_line"])
            if any(start <= line <= end for line in line_numbers):
                score += 250
            depth = qualified.count(".")
            score += max(0, 4 - depth)
            scored.append((score, -index, qualified))
        scored.sort(reverse=True)
        chosen: list[str] = []
        wanted = limit or self.config.initial_symbol_limit
        for score, _, name in scored:
            if score <= 4 and len(chosen) >= min(5, wanted):
                continue
            if name not in chosen:
                chosen.append(name)
            if len(chosen) >= wanted:
                break
        if not chosen:
            chosen = [str(item["qualified_name"]) for item in symbols[:wanted]]
        return chosen

    def review(self, source_override: str | None = None, task: str = DEFAULT_TASK) -> dict[str, Any]:
        source = self._source(source_override)
        self._validate_source(source)
        target = self._target(source)
        slicer = CodeSlicer(str(target))
        symbols = slicer.get_symbol_map()
        selected = self._select_symbols(slicer, task, source)
        report = {
            "schema": "project_forge_preview8_review_v1",
            "created_at": now_iso(),
            "source": str(source),
            "target": str(target),
            "target_sha256": sha256_file(target),
            "target_lines": len(slicer.lines),
            "parse_error": slicer.parse_error,
            "symbol_count": len(symbols),
            "selected_symbols": selected,
            "symbols": symbols,
            "whole_file_read_blocked_for_opencode": True,
            "original_modified": False,
        }
        self.status.update(source_root=str(source))
        return report

    def _copy_source(self, source: Path, project: Path) -> None:
        ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache")
        shutil.copytree(source, project, ignore=ignore)

    def _git(self, project: Path, *args: str, timeout: int = 120) -> dict[str, Any]:
        git = shutil.which("git")
        if not git:
            raise ForgeError("Git was not found on PATH. Project Forge requires Git for snapshot and rollback.")
        return run_command([git, *args], cwd=project, timeout=timeout)

    def create_snapshot(self, source_override: str | None = None, task: str = DEFAULT_TASK) -> dict[str, Any]:
        source = self._source(source_override)
        self._validate_source(source)
        root = self._workspace_root()
        root.mkdir(parents=True, exist_ok=True)
        workspace = root / f"{stamp()}_{random_id()}_PREVIEW8_SLICER"
        project = workspace / "project"
        meta = workspace / "meta"
        review_dir = workspace / "review"
        meta.mkdir(parents=True)
        review_dir.mkdir(parents=True)

        source_before = tree_manifest(source, excludes=(".git", "__pycache__"))
        self._copy_source(source, project)
        copied_manifest = tree_manifest(project, excludes=(".git", "__pycache__"))
        if source_before != copied_manifest:
            differences = changed_manifest(source_before, copied_manifest)
            raise ForgeError(f"Disposable copy did not match source. Differences: {differences[:20]}")

        for args in (("init",), ("config", "user.name", "Project Forge Preview 8"), ("config", "user.email", "preview8@local.invalid"), ("add", "-A"), ("commit", "-m", "Project Forge Preview 8 baseline")):
            result = self._git(project, *args)
            if result["exit_code"] != 0:
                raise ForgeError(f"Git command failed: {' '.join(args)}\n{result['stderr']}")
        rev = self._git(project, "rev-parse", "HEAD")
        baseline = rev["stdout"].strip()

        review = self.review(str(source), task)
        write_json(meta / "SOURCE_MANIFEST_BEFORE.json", source_before)
        write_json(meta / "SNAPSHOT.json", {
            "schema": "project_forge_preview8_snapshot_v1",
            "created_at": now_iso(),
            "source": str(source),
            "workspace": str(workspace),
            "project": str(project),
            "baseline_commit": baseline,
            "target_sha256": review["target_sha256"],
            "task": task,
            "source_file_count": len(source_before),
            "no_live_source_edits": True,
        })
        write_json(review_dir / "INITIAL_REVIEW.json", review)
        (workspace / "TASK.txt").write_text(task, encoding="utf-8")

        self.current_workspace = workspace
        self.current_project = project
        self.baseline_commit = baseline
        self.current_patch = None
        self.status.update(workspace=str(workspace), latest_patch="")
        return {
            "workspace": str(workspace),
            "project": str(project),
            "baseline_commit": baseline,
            "review": review,
        }

    def _module_range_context(self, slicer: CodeSlicer, selected: list[str], destination: Path) -> list[dict[str, Any]]:
        symbols = slicer.get_symbol_map()
        selected_set = set(selected)
        records: list[dict[str, Any]] = []
        for ordinal, symbol in enumerate(symbols, 1):
            qualified = str(symbol["qualified_name"])
            if qualified not in selected_set:
                continue
            start = int(symbol["start_line"])
            end = int(symbol["end_line"])
            slug = safe_slug(qualified)
            numbered = destination / f"{ordinal:03d}_{slug}.lines.txt"
            raw = destination / f"{ordinal:03d}_{slug}.patch_context.py"
            numbered.write_text(slicer.extract_slice([qualified]), encoding="utf-8")
            raw_lines = slicer.lines[max(0, start - 1): min(len(slicer.lines), end)]
            raw.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
            records.append({
                "qualified_name": qualified,
                "type": symbol["type"],
                "start_line": start,
                "end_line": end,
                "numbered_slice": numbered.name,
                "patch_context": raw.name,
            })
        return records

    def _opencode_config(self) -> dict[str, Any]:
        return {
            "$schema": "https://opencode.ai/config.json",
            "model": "projectforge/qwen3-coder-local",
            "small_model": "projectforge/qwen3-coder-local",
            "enabled_providers": ["projectforge"],
            "provider": {
                "projectforge": {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": "Project Forge Local Qwen3-Coder",
                    "options": {"baseURL": self.config.endpoint, "apiKey": "local-project-forge"},
                    "models": {
                        "qwen3-coder-local": {
                            "id": self.config.model_id,
                            "name": "Qwen3-Coder 30B A3B Local",
                            "limit": {"context": self.config.context_limit, "output": self.config.output_limit},
                        }
                    },
                }
            },
            "compaction": {"auto": False, "prune": True, "reserved": 4096},
            "permission": {
                "*": "deny",
                "read": {"*": "allow", "**/dirty_python_lab.py": "deny"},
                "list": "allow",
                "glob": "allow",
                "grep": "allow",
                "edit": {"*": "deny", "PROPOSED.patch": "allow", "./PROPOSED.patch": "allow"},
                "bash": "deny",
                "external_directory": "deny",
                "task": "deny",
                "skill": "deny",
                "lsp": "deny",
                "question": "deny",
                "webfetch": "deny",
                "websearch": "deny",
                "doom_loop": "deny",
            },
        }

    def _write_agent_instructions(self, agent_view: Path) -> None:
        text = """# Project Forge Preview 8 — Surgical Patch Agent

You are operating inside a deliberately restricted agent-view workspace.

Hard rules:
1. The full target `dirty_python_lab.py` is intentionally absent. Do not look outside this workspace.
2. Read `TASK.txt`, `context/PROJECT_MAP.json`, `context/tests/`, `slices/SYMBOL_MAP.json`, `slices/SELECTED_SYMBOLS.json`, and the slice files.
3. Produce exactly one unified diff in `PROPOSED.patch`.
4. The patch may modify only `dirty_python_lab.py`.
5. Do not modify tests, configuration, instructions, slice files, or any other file.
6. Do not use shell commands, web access, external directories, subagents, or package installation.
7. Use the raw `*.patch_context.py` files for exact hunk context. Line-numbered `*.lines.txt` files are evidence only.
8. Keep the patch focused on the requested task. Do not rewrite the whole file.
9. `PROPOSED.patch` must use standard paths `a/dirty_python_lab.py` and `b/dirty_python_lab.py`.
10. Stop after writing `PROPOSED.patch`.
"""
        (agent_view / "AGENTS.md").write_text(text, encoding="utf-8")

    def _build_project_map(self, project: Path) -> dict[str, Any]:
        files = []
        for path in sorted(p for p in project.rglob("*") if p.is_file() and ".git" not in p.parts):
            rel = path.relative_to(project).as_posix()
            files.append({"path": rel, "size_bytes": path.stat().st_size, "target_blocked": rel == self.config.target_file})
        return {
            "schema": "project_forge_preview8_project_map_v1",
            "project": str(project),
            "target_file": self.config.target_file,
            "target_whole_file_available_to_agent": False,
            "files": files,
        }

    def build_agent_view(
        self,
        project: Path,
        task: str,
        round_number: int,
        *,
        failure_text: str = "",
        extra_names: Iterable[str] = (),
    ) -> dict[str, Any]:
        workspace = project.parent
        agent_view = workspace / f"agent_view_round_{round_number}"
        if agent_view.exists():
            shutil.rmtree(agent_view)
        (agent_view / "context" / "tests").mkdir(parents=True)
        slices_dir = agent_view / "slices"
        slices_dir.mkdir()

        target = self._target(project)
        slicer = CodeSlicer(str(target))
        limit = self.config.initial_symbol_limit if round_number == 1 else self.config.repair_symbol_limit
        selected = self._select_symbols(
            slicer,
            task,
            project,
            failure_text=failure_text,
            extra_names=extra_names,
            limit=limit,
        )
        symbols = slicer.get_symbol_map()
        records = self._module_range_context(slicer, selected, slices_dir)
        write_json(slices_dir / "SYMBOL_MAP.json", symbols)
        write_json(slices_dir / "SELECTED_SYMBOLS.json", records)

        tests = project / "tests"
        if tests.exists():
            for path in tests.rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix in {".py", ".json", ".txt", ".md"}:
                    destination = agent_view / "context" / "tests" / path.relative_to(tests)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)

        small_files = []
        for name in ("config.json", "README_FIRST.txt", "PACKAGE_MANIFEST.json", "LATEST_RUN.txt"):
            source = project / name
            if source.exists() and source.is_file() and source.stat().st_size <= 100_000:
                shutil.copy2(source, agent_view / "context" / name)
                small_files.append(name)

        project_map = self._build_project_map(project)
        write_json(agent_view / "context" / "PROJECT_MAP.json", project_map)
        (agent_view / "TASK.txt").write_text(task, encoding="utf-8")
        (agent_view / "FAILURE_CONTEXT.txt").write_text(failure_text or "No prior failure; this is the first surgical round.\n", encoding="utf-8")
        (agent_view / "TARGET_FILE_BLOCKED.txt").write_text(
            "dirty_python_lab.py is intentionally absent. Use only Code Slicer V1 outputs under slices/.\n",
            encoding="utf-8",
        )
        (agent_view / "PROPOSED.patch").write_text("", encoding="utf-8")
        write_json(agent_view / "opencode.json", self._opencode_config())
        self._write_agent_instructions(agent_view)

        prompt = f"""Perform Project Forge Preview 8 surgical round {round_number}.
Read AGENTS.md and obey it exactly. The target whole file is unavailable by design.
Use the Code Slicer V1 evidence under slices/ and the protected tests under context/tests/.
Write only a focused unified diff to PROPOSED.patch, modifying only dirty_python_lab.py.
Do not explain the result in chat after the patch is written."""
        (agent_view / "PROMPT.txt").write_text(prompt, encoding="utf-8")

        git = shutil.which("git")
        if git:
            run_command([git, "init"], cwd=agent_view)
            run_command([git, "config", "user.name", "Project Forge Agent View"], cwd=agent_view)
            run_command([git, "config", "user.email", "agent-view@local.invalid"], cwd=agent_view)
            run_command([git, "add", "-A"], cwd=agent_view)
            run_command([git, "commit", "-m", f"Agent view round {round_number}"], cwd=agent_view)

        forbidden = [path for path in agent_view.rglob(self.config.target_file)]
        if forbidden:
            raise ForgeError(f"Safety failure: whole target leaked into agent view: {forbidden}")

        return {
            "agent_view": str(agent_view),
            "selected_symbols": selected,
            "slice_records": records,
            "symbol_count": len(symbols),
            "small_files": small_files,
            "prompt": prompt,
            "target_present": False,
        }

    def _model_probe(self) -> dict[str, Any]:
        url = self.config.endpoint.rstrip("/") + "/models"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise ForgeError(f"Could not query local model endpoint {url}: {exc}") from exc
        ids = [str(item.get("id", "")) for item in payload.get("data", []) if isinstance(item, dict)]
        meta_context = None
        meta = payload.get("meta")
        if isinstance(meta, dict):
            meta_context = meta.get("n_ctx")
        if self.config.model_id not in ids:
            raise ForgeError(
                "Exact Qwen3-Coder model was not reported by /v1/models. "
                f"Expected: {self.config.model_id}; reported: {ids}"
            )
        try:
            reported_context = int(meta_context)
        except (TypeError, ValueError) as exc:
            raise ForgeError(
                "The local /v1/models response did not report meta.n_ctx, so the 16,384 context gate cannot be proven."
            ) from exc
        if reported_context != self.config.context_limit:
            raise ForgeError(
                "The local model context does not match Project Forge Preview 8. "
                f"Expected {self.config.context_limit}; reported {reported_context}."
            )
        return {
            "url": url,
            "model_id": self.config.model_id,
            "reported_ids": ids,
            "meta_n_ctx": reported_context,
            "exact_model_verified": True,
            "context_verified": True,
        }

    def _profile_paths(self) -> list[Path]:
        candidates: list[Path] = []
        env = os.environ
        user = Path(env.get("USERPROFILE") or Path.home())
        candidates.extend([
            user / ".config" / "opencode",
            user / ".local" / "share" / "opencode",
        ])
        if env.get("APPDATA"):
            candidates.append(Path(env["APPDATA"]) / "opencode")
        if env.get("LOCALAPPDATA"):
            candidates.append(Path(env["LOCALAPPDATA"]) / "opencode")
        unique: list[Path] = []
        seen = set()
        for path in candidates:
            key = str(path).lower()
            if key not in seen:
                unique.append(path)
                seen.add(key)
        return unique

    def _profile_manifest(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for root in self._profile_paths():
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file():
                    try:
                        result[f"{root}|{path.relative_to(root).as_posix()}"] = sha256_file(path)
                    except OSError:
                        continue
        return result

    def _isolated_opencode_env(self, agent_view: Path) -> dict[str, str]:
        env = dict(os.environ)
        home = agent_view / ".isolated_opencode_home"
        appdata = home / "AppData" / "Roaming"
        localappdata = home / "AppData" / "Local"
        xdg_config = home / ".config"
        xdg_data = home / ".local" / "share"
        xdg_cache = home / ".cache"
        for path in (home, appdata, localappdata, xdg_config, xdg_data, xdg_cache):
            path.mkdir(parents=True, exist_ok=True)
        env.update({
            "HOME": str(home),
            "USERPROFILE": str(home),
            "APPDATA": str(appdata),
            "LOCALAPPDATA": str(localappdata),
            "XDG_CONFIG_HOME": str(xdg_config),
            "XDG_DATA_HOME": str(xdg_data),
            "XDG_CACHE_HOME": str(xdg_cache),
            "OPENCODE_CONFIG": str(agent_view / "opencode.json"),
            "OPENCODE_CONFIG_DIR": str(agent_view / ".opencode"),
            "OPENCODE_DISABLE_AUTOUPDATE": "true",
            "OPENCODE_DISABLE_DEFAULT_PLUGINS": "true",
            "OPENCODE_DISABLE_LSP_DOWNLOAD": "true",
            "OPENCODE_DISABLE_MODELS_FETCH": "true",
            "OPENCODE_DISABLE_AUTOCOMPACT": "true",
            "OPENCODE_DISABLE_CLAUDE_CODE": "true",
            "OPENCODE_AUTO_SHARE": "false",
            "OPENCODE_EXPERIMENTAL_DISABLE_FILEWATCHER": "true",
            "OPENCODE_CLIENT": "project-forge-preview8",
        })
        return env

    def _resolve_opencode_command(self) -> list[str]:
        command = list(self.config.opencode_command)
        if not command:
            command = ["opencode"]
        first = command[0]
        if Path(first).is_file() or shutil.which(first):
            return command
        raise ForgeError(f"Native OpenCode executable not found: {first}")

    def invoke_opencode(self, agent_view: Path, prompt: str) -> dict[str, Any]:
        profile_before = self._profile_manifest()
        env = self._isolated_opencode_env(agent_view)
        command = self._resolve_opencode_command() + [
            "run",
            "--auto",
            "--format",
            "json",
            "--model",
            "projectforge/qwen3-coder-local",
            "--dir",
            str(agent_view),
            prompt,
        ]
        log_path = agent_view / "OPENCODE_EVENTS.jsonl"
        err_path = agent_view / "OPENCODE_STDERR.txt"
        started = time.monotonic()
        with self._process_lock:
            self._active_process = subprocess.Popen(
                command,
                cwd=str(agent_view),
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
        try:
            stdout, stderr = self._active_process.communicate(timeout=self.config.opencode_timeout_seconds)
            exit_code = self._active_process.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            self._active_process.kill()
            stdout, stderr = self._active_process.communicate()
            exit_code = 124
            timed_out = True
        finally:
            with self._process_lock:
                self._active_process = None
        log_path.write_text(stdout or "", encoding="utf-8")
        err_path.write_text(stderr or "", encoding="utf-8")
        profile_after = self._profile_manifest()
        profile_changes = changed_manifest(profile_before, profile_after)
        result = {
            "command": command,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout_log": str(log_path),
            "stderr_log": str(err_path),
            "stderr_tail": (stderr or "")[-6000:],
            "host_profile_write_count": len(profile_changes),
            "host_profile_changes": profile_changes,
            "isolated_home": str(agent_view / ".isolated_opencode_home"),
        }
        return result

    def stop(self) -> bool:
        self.status.update(stop_requested=True)
        with self._process_lock:
            proc = self._active_process
            if proc and proc.poll() is None:
                proc.terminate()
                return True
        return False

    def _patch_targets(self, text: str) -> list[str]:
        targets: list[str] = []
        for line in text.splitlines():
            if line.startswith("+++ ") or line.startswith("--- "):
                value = line[4:].split("\t", 1)[0].strip()
                if value == "/dev/null":
                    continue
                value = value.replace("\\", "/")
                if value.startswith("a/") or value.startswith("b/"):
                    value = value[2:]
                targets.append(value)
        return sorted(set(targets))

    def validate_patch(self, project: Path, patch: Path) -> dict[str, Any]:
        text = patch.read_text(encoding="utf-8", errors="replace") if patch.exists() else ""
        errors: list[str] = []
        if not text.strip():
            errors.append("PROPOSED.patch is empty.")
        if "GIT binary patch" in text or "Binary files" in text:
            errors.append("Binary patches are not allowed.")
        targets = self._patch_targets(text)
        if not targets:
            errors.append("No unified-diff file headers were found.")
        allowed = {self.config.target_file.replace("\\", "/")}
        unexpected = [item for item in targets if item not in allowed]
        if unexpected:
            errors.append(f"Patch targets are not allowed: {unexpected}")
        if any(".." in Path(item).parts or Path(item).is_absolute() for item in targets):
            errors.append("Absolute paths and parent traversal are not allowed.")
        test_before = tree_manifest(project / "tests")
        apply_check = {"exit_code": -1, "stdout": "", "stderr": "Not run."}
        if not errors:
            apply_check = self._git(project, "apply", "--check", "--whitespace=nowarn", str(patch))
            if apply_check["exit_code"] != 0:
                errors.append("git apply --check failed.")
        test_after = tree_manifest(project / "tests")
        if test_before != test_after:
            errors.append("Protected tests changed during patch validation.")
        return {
            "valid": not errors,
            "errors": errors,
            "targets": targets,
            "apply_check": apply_check,
            "protected_tests_unchanged": test_before == test_after,
            "patch_sha256": sha256_file(patch) if patch.exists() else "",
            "patch_bytes": patch.stat().st_size if patch.exists() else 0,
        }

    def apply_patch(self, project: Path | None = None, patch: Path | None = None, round_number: int = 0) -> dict[str, Any]:
        project = project or self.current_project
        patch = patch or self.current_patch
        if not project or not patch:
            raise ForgeError("No disposable project and patch are ready.")
        validation = self.validate_patch(project, patch)
        if not validation["valid"]:
            raise ForgeError("Patch validation failed: " + "; ".join(validation["errors"]))
        tests_before = tree_manifest(project / "tests")
        apply_result = self._git(project, "apply", "--whitespace=nowarn", str(patch))
        if apply_result["exit_code"] != 0:
            raise ForgeError(f"Could not apply patch to disposable copy: {apply_result['stderr']}")
        tests_after = tree_manifest(project / "tests")
        if tests_before != tests_after:
            self._git(project, "reset", "--hard", "HEAD")
            raise ForgeError("Protected tests changed after patch application; disposable round was rolled back.")
        self._git(project, "add", self.config.target_file)
        commit = self._git(project, "commit", "-m", f"Project Forge Preview 8 surgical round {round_number or 1}")
        if commit["exit_code"] != 0:
            raise ForgeError(f"Could not commit disposable patch: {commit['stderr']}")
        revision = self._git(project, "rev-parse", "HEAD")["stdout"].strip()
        return {
            "applied": True,
            "project": str(project),
            "patch": str(patch),
            "revision": revision,
            "protected_tests_unchanged": True,
        }

    def run_tests(self, project: Path | None = None) -> dict[str, Any]:
        project = project or self.current_project
        if not project:
            raise ForgeError("No disposable project is ready.")
        target = self._target(project)
        compile_error = ""
        compile_exit = 0
        try:
            py_compile.compile(str(target), doraise=True)
        except py_compile.PyCompileError as exc:
            compile_exit = 1
            compile_error = str(exc)
        commands: list[dict[str, Any]] = []
        all_passed = compile_exit == 0
        for configured in self.config.test_commands:
            command = [part.replace("{python}", sys.executable) for part in configured]
            result = run_command(command, cwd=project, timeout=self.config.test_timeout_seconds)
            commands.append(result)
            all_passed = all_passed and result["exit_code"] == 0
        return {
            "passed": all_passed,
            "compile_exit_code": compile_exit,
            "compile_error": compile_error,
            "test_commands": commands,
            "failure_text": "\n".join(
                [compile_error] + [item["stdout"] + "\n" + item["stderr"] for item in commands if item["exit_code"] != 0]
            ).strip(),
        }

    def rollback(self, project: Path | None = None) -> dict[str, Any]:
        project = project or self.current_project
        if not project:
            raise ForgeError("No disposable project is ready.")
        baseline = self.baseline_commit
        if not baseline:
            snapshot = read_json(project.parent / "meta" / "SNAPSHOT.json", {}) or {}
            baseline = snapshot.get("baseline_commit")
        if not baseline:
            raise ForgeError("Baseline commit is unknown.")
        result = self._git(project, "reset", "--hard", baseline)
        clean_result = self._git(project, "clean", "-fdx")
        clean = self._git(project, "status", "--porcelain")["stdout"].strip() == ""
        return {
            "rolled_back": result["exit_code"] == 0 and clean_result["exit_code"] == 0 and clean,
            "baseline_commit": baseline,
            "clean": clean,
            "reset": result,
            "clean_result": clean_result,
        }

    def _copy_patch_for_review(self, source_patch: Path, round_number: int) -> Path:
        assert self.current_workspace is not None
        destination = self.current_workspace / "review" / f"ROUND_{round_number}_PROPOSED.patch"
        shutil.copy2(source_patch, destination)
        self.current_patch = destination
        self.status.update(latest_patch=str(destination))
        return destination

    def run_surgical_build(
        self,
        source_override: str | None = None,
        task: str = DEFAULT_TASK,
        *,
        require_live_model_probe: bool = True,
    ) -> dict[str, Any]:
        self.status.update(stop_requested=False)
        snapshot = self.create_snapshot(source_override, task)
        project = Path(snapshot["project"])
        workspace = Path(snapshot["workspace"])
        source = self._source(source_override)
        original_before = tree_manifest(source, excludes=(".git", "__pycache__"))
        model_probe: dict[str, Any] | None = None
        if require_live_model_probe:
            self._set_stage("model_check", "Verifying exact Qwen3-Coder model and 16,384 context endpoint.")
            model_probe = self._model_probe()

        rounds: list[dict[str, Any]] = []
        failure_text = ""
        final_tests: dict[str, Any] | None = None
        terminal_error = ""
        host_profile_write_count = 0
        for round_number in range(1, self.config.max_rounds + 1):
            if self.status.get().get("stop_requested"):
                terminal_error = "Stopped by user before source application."
                break
            self._set_stage("slicing", f"Round {round_number}: mapping and extracting targeted symbols with exact Code Slicer V1.")
            view = self.build_agent_view(project, task, round_number, failure_text=failure_text)
            agent_view = Path(view["agent_view"])
            self._set_stage("opencode", f"Round {round_number}: OpenCode is inspecting slices only; the whole target file is absent.")
            invocation = self.invoke_opencode(agent_view, view["prompt"])
            host_profile_write_count += int(invocation.get("host_profile_write_count", 0))
            patch_source = agent_view / "PROPOSED.patch"
            patch_review = self._copy_patch_for_review(patch_source, round_number)
            validation = self.validate_patch(project, patch_review)
            round_record: dict[str, Any] = {
                "round": round_number,
                "agent_view": view,
                "opencode": invocation,
                "patch": str(patch_review),
                "validation": validation,
            }
            if invocation["exit_code"] != 0:
                terminal_error = f"OpenCode exited {invocation['exit_code']}."
                failure_text = invocation.get("stderr_tail", "")
                round_record["accepted"] = False
                rounds.append(round_record)
                if invocation.get("timed_out"):
                    break
                continue
            if not validation["valid"]:
                terminal_error = "OpenCode produced a patch that failed safety or apply validation."
                failure_text = "\n".join(validation["errors"]) + "\n" + validation["apply_check"].get("stderr", "")
                round_record["accepted"] = False
                rounds.append(round_record)
                continue

            self._set_stage("apply_disposable", f"Round {round_number}: applying validated patch only to the disposable Git copy.")
            applied = self.apply_patch(project, patch_review, round_number)
            self._set_stage("testing", f"Round {round_number}: compiling and running the full protected test suite.")
            tests = self.run_tests(project)
            round_record.update({"accepted": True, "applied": applied, "tests": tests})
            rounds.append(round_record)
            final_tests = tests
            if tests["passed"]:
                terminal_error = ""
                break
            failure_text = tests["failure_text"]
            terminal_error = "Tests still failed after the latest targeted patch."

        original_after = tree_manifest(source, excludes=(".git", "__pycache__"))
        original_changes = changed_manifest(original_before, original_after)
        passed = bool(final_tests and final_tests["passed"] and not original_changes and host_profile_write_count == 0)
        status_value = "passed_disposable_only" if passed else "not_passed"
        receipt = {
            "schema": "project_forge_preview8_build_v1",
            "status": status_value,
            "created_at": now_iso(),
            "version": APP_VERSION,
            "source": str(source),
            "workspace": str(workspace),
            "project": str(project),
            "target_file": self.config.target_file,
            "exact_slicer_sha256": sha256_file(Path(__file__).with_name("code_slicer_v1.py")),
            "whole_target_available_to_opencode": False,
            "model": model_probe or {
                "model_id": self.config.model_id,
                "context_limit": self.config.context_limit,
                "probe_skipped_for_test": True,
            },
            "rounds": rounds,
            "final_tests": final_tests,
            "baseline_commit": self.baseline_commit,
            "host_profile_write_count": host_profile_write_count,
            "original_source_changes": original_changes,
            "live_foxai_modified": False,
            "original_dirty_python_lab_modified": self.config.target_file in original_changes,
            "stopped_before_original_apply": True,
            "terminal_error": terminal_error,
        }
        receipt_path = workspace / "BUILD_RECEIPT.json"
        write_json(receipt_path, receipt)
        (workspace / "BUILD_RECEIPT.txt").write_text(self._receipt_text(receipt), encoding="utf-8")
        self.status.update(latest_receipt=str(receipt_path), workspace=str(workspace))
        if passed:
            self._set_stage("finished", "Disposable build passed. Original Dirty Python Lab remains untouched.")
        else:
            self._set_stage("finished", terminal_error or "Build stopped without modifying the original source.")
        return receipt

    def _receipt_text(self, receipt: dict[str, Any]) -> str:
        tests = receipt.get("final_tests") or {}
        return "\n".join([
            "PROJECT FORGE PREVIEW 8 RECEIPT",
            "=" * 44,
            f"status: {receipt.get('status')}",
            f"created_at: {receipt.get('created_at')}",
            f"workspace: {receipt.get('workspace')}",
            f"model_id: {(receipt.get('model') or {}).get('model_id')}",
            f"context_limit: {self.config.context_limit}",
            f"whole_target_available_to_opencode: {receipt.get('whole_target_available_to_opencode')}",
            f"rounds_attempted: {len(receipt.get('rounds') or [])}",
            f"compile_exit_code: {tests.get('compile_exit_code')}",
            f"tests_passed: {tests.get('passed')}",
            f"host_profile_write_count: {receipt.get('host_profile_write_count')}",
            f"original_source_changes: {receipt.get('original_source_changes')}",
            f"live_foxai_modified: {receipt.get('live_foxai_modified')}",
            f"stopped_before_original_apply: {receipt.get('stopped_before_original_apply')}",
            f"terminal_error: {receipt.get('terminal_error') or ''}",
            "",
        ])


INDEX_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Forge Preview 8</title>
<style>
:root{color-scheme:dark;--bg:#0e0b14;--panel:#191326;--panel2:#211832;--purple:#a970ff;--cyan:#5ee7ff;--green:#67e89b;--orange:#ffb86b;--red:#ff6b85;--text:#f6f1ff;--muted:#b8abc9}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#09070e,#171023 60%,#0c1118);font-family:Segoe UI,Arial,sans-serif;color:var(--text);font-size:18px}.wrap{max-width:1280px;margin:auto;padding:24px}.hero{padding:26px;border:1px solid #4a3568;border-radius:18px;background:rgba(24,17,36,.94);box-shadow:0 15px 50px #0008}.hero h1{font-size:34px;margin:0 0 8px}.tag{color:var(--cyan);font-weight:700}.warning{margin-top:14px;padding:13px;border-left:5px solid var(--orange);background:#2b211a;border-radius:8px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}.panel{background:var(--panel);border:1px solid #3c2b55;border-radius:15px;padding:18px}.wide{grid-column:1/-1}label{display:block;color:var(--muted);font-weight:700;margin:8px 0}input,textarea{width:100%;padding:14px;border-radius:10px;border:1px solid #55406f;background:#0d0a13;color:var(--text);font-size:17px}textarea{min-height:230px;font-family:Consolas,monospace}.buttons{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.buttons button{min-height:64px;border:0;border-radius:12px;padding:12px;font-size:17px;font-weight:800;cursor:pointer;background:#38244f;color:white}.buttons button.primary{background:linear-gradient(135deg,#7542bd,#a970ff);color:#fff}.buttons button.good{background:#174b34}.buttons button.warn{background:#66421c}.buttons button.danger{background:#64243a}.buttons button:disabled{opacity:.45;cursor:not-allowed}.status{display:grid;grid-template-columns:180px 1fr;gap:8px 16px}.key{color:var(--muted)}pre{white-space:pre-wrap;word-break:break-word;background:#09070e;border:1px solid #342449;padding:15px;border-radius:10px;max-height:430px;overflow:auto;font-size:15px}.badge{display:inline-block;padding:6px 10px;border-radius:999px;background:#332348;color:var(--cyan);font-weight:800}.footer{color:var(--muted);font-size:14px;margin-top:16px}@media(max-width:850px){.grid{grid-template-columns:1fr}.buttons{grid-template-columns:1fr}.wide{grid-column:auto}.status{grid-template-columns:1fr}}
</style></head><body><div class="wrap"><section class="hero"><div class="tag">CLEAN PREVIEW — SURGICAL SOURCE READING</div><h1>Project Forge Preview 8</h1><div>Exact Code Slicer V1 + native OpenCode + disposable Git workspace.</div><div class="warning"><b>Preview 7 is not installed or run.</b> “Apply” means the disposable copy only. This preview contains no route or button that applies changes to the original Dirty Python Lab or live FOXAI.</div></section>
<div class="grid"><section class="panel wide"><label>Dirty Python Lab source folder</label><input id="source" value="Z:\FOXAI\_LAB\DirtyPythonLab"><label>Build task</label><textarea id="task"></textarea></section>
<section class="panel wide"><div class="buttons"><button onclick="act('review')">1. REVIEW SYMBOL MAP</button><button onclick="act('snapshot')">2. SNAPSHOT DISPOSABLE COPY</button><button class="primary" onclick="act('run')">3. RUN SURGICAL BUILD + TEST</button><button onclick="act('apply')">APPLY LATEST PATCH TO DISPOSABLE</button><button class="good" onclick="act('test')">RUN FULL TEST SUITE</button><button class="warn" onclick="act('rollback')">ROLLBACK DISPOSABLE</button><button onclick="openItem('workspace')">OPEN WORKSPACE</button><button onclick="openItem('patch')">OPEN LATEST PATCH</button><button onclick="openItem('receipt')">OPEN RECEIPT</button><button class="danger" onclick="act('stop')">STOP OPENCODE</button></div></section>
<section class="panel"><h2>Status <span id="busy" class="badge">idle</span></h2><div class="status"><div class="key">Stage</div><div id="stage"></div><div class="key">Message</div><div id="message"></div><div class="key">Workspace</div><div id="workspace"></div><div class="key">Error</div><div id="error"></div></div></section>
<section class="panel"><h2>Safety gates</h2><pre>✓ Full dirty_python_lab.py absent from agent view
✓ OpenCode external-directory access denied
✓ OpenCode shell access denied
✓ OpenCode may write only PROPOSED.patch
✓ Patch targets limited to dirty_python_lab.py
✓ Protected tests hashed before and after
✓ git apply --check required
✓ Patch applied only to disposable Git copy
✓ Host OpenCode profile redirected and checked
✓ Original source manifest checked after run
✓ No Workshop, tkinter, installer, runtime edits, or live FOXAI edits</pre></section>
<section class="panel wide"><h2>Activity</h2><pre id="details">Ready.</pre></section></div><div class="footer">Project Forge Preview 8 — standard-library browser controller. Close this browser tab only after using STOP if OpenCode is active.</div></div>
<script>
const DEFAULT_TASK=`Improve Dirty Python Lab so long local-model requests cannot leave the browser with an unexplained Failed to fetch message.\n\nAcceptance requirements:\n- The browser run request must return quickly and long generation/repair work must continue as a background job.\n- The page must poll and visibly show stages such as generating, running, repairing, and finished.\n- Every run must record the exact model ID reported by /v1/models.\n- Every run must maintain an append-only progress log.\n- RESULT.json must always be written, including endpoint errors, model timeouts, execution timeouts, and exhausted repairs.\n- Preserve the current disposable run folders and no-overwrite behavior.\n- Use Python standard library only. Do not add tkinter or third-party runtime packages.\n- Update or add automated tests for the new behavior.\n- Run the complete test suite and keep repairing until it passes.`;
document.getElementById('task').value=DEFAULT_TASK;
async function api(path,opts={}){let r=await fetch(path,opts);let d=await r.json();if(!r.ok)throw new Error(d.error||r.statusText);return d}
async function act(name){try{let body={source:document.getElementById('source').value,task:document.getElementById('task').value};await api('/api/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});poll()}catch(e){alert(e.message)}}
async function openItem(kind){try{await api('/api/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind})})}catch(e){alert(e.message)}}
async function poll(){try{let d=await api('/api/status');busy.textContent=d.busy?'busy':'idle';stage.textContent=d.stage||'';message.textContent=d.message||'';workspace.textContent=d.workspace||'';error.textContent=d.error||'';details.textContent=(d.details||[]).join('\n')||'Ready.';document.querySelectorAll('button').forEach(b=>{if(!b.classList.contains('danger'))b.disabled=!!d.busy})}catch(e){details.textContent=e.message}}
setInterval(poll,1200);poll();
</script></body></html>"""


class ForgeWebApp:
    def __init__(self, forge: SurgicalForge) -> None:
        self.forge = forge
        self.status = forge.status
        self.server: ThreadingHTTPServer | None = None

    def _background(self, name: str, function, *args, **kwargs) -> None:
        if self.status.get().get("busy"):
            raise ForgeError("Another Project Forge action is already running.")
        self.status.update(busy=True, stage=name, message=f"Starting {name}.", details=[], error="")

        def worker() -> None:
            try:
                result = function(*args, **kwargs)
                self.status.add_detail(json.dumps(result, indent=2, default=str)[-12000:])
                if self.status.get().get("stage") != "finished":
                    self.status.update(stage="finished", message=f"{name} completed.")
            except Exception as exc:
                self.status.update(stage="failed", message=f"{name} failed.", error=str(exc))
                self.status.add_detail(traceback.format_exc())
            finally:
                self.status.update(busy=False)

        threading.Thread(target=worker, name=f"forge-{name}", daemon=True).start()

    def serve(self, open_browser: bool = True) -> int:
        app = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "ProjectForgePreview8/1.0"

            def log_message(self, format: str, *args: Any) -> None:
                return

            def _json(self, data: Any, status: int = 200) -> None:
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _body(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length <= 0:
                    return {}
                try:
                    return json.loads(self.rfile.read(length).decode("utf-8"))
                except json.JSONDecodeError:
                    return {}

            def do_GET(self) -> None:
                if self.path == "/":
                    body = INDEX_HTML.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if self.path == "/api/status":
                    self._json(app.status.get())
                    return
                self._json({"error": "Not found."}, 404)

            def do_POST(self) -> None:
                payload = self._body()
                source = payload.get("source") or app.forge.config.source_root
                task = payload.get("task") or DEFAULT_TASK
                try:
                    if self.path == "/api/review":
                        app._background("review", app.forge.review, source, task)
                    elif self.path == "/api/snapshot":
                        app._background("snapshot", app.forge.create_snapshot, source, task)
                    elif self.path == "/api/run":
                        app._background("surgical_build", app.forge.run_surgical_build, source, task)
                    elif self.path == "/api/apply":
                        app._background("apply_disposable", app.forge.apply_patch)
                    elif self.path == "/api/test":
                        app._background("test_disposable", app.forge.run_tests)
                    elif self.path == "/api/rollback":
                        app._background("rollback_disposable", app.forge.rollback)
                    elif self.path == "/api/stop":
                        stopped = app.forge.stop()
                        app.status.add_detail("Stop requested." if stopped else "No active OpenCode process was found.")
                    elif self.path == "/api/open":
                        kind = payload.get("kind")
                        mapping = {
                            "workspace": app.forge.current_workspace,
                            "patch": app.forge.current_patch,
                            "receipt": Path(app.status.get().get("latest_receipt")) if app.status.get().get("latest_receipt") else None,
                        }
                        path = mapping.get(kind)
                        if not path or not Path(path).exists():
                            raise ForgeError(f"No {kind} is ready yet.")
                        if os.name == "nt":
                            os.startfile(str(path))  # type: ignore[attr-defined]
                        else:
                            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        self._json({"error": "Not found."}, 404)
                        return
                    self._json({"ok": True})
                except Exception as exc:
                    self._json({"error": str(exc)}, 409)

        self.server = ThreadingHTTPServer((self.forge.config.host, self.forge.config.port), Handler)
        url = f"http://{self.forge.config.host}:{self.server.server_address[1]}/"
        print(APP_NAME)
        print(f"Open: {url}")
        if open_browser:
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        try:
            self.server.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            pass
        finally:
            self.forge.stop()
            self.server.server_close()
        return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.json")))
    parser.add_argument("--source")
    parser.add_argument("--workspace-root")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--run-build", action="store_true")
    parser.add_argument("--task-file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = ForgeConfig.load(Path(args.config)).with_overrides(
        source_root=args.source,
        workspace_root=args.workspace_root,
        host=args.host,
        port=args.port,
    )
    forge = SurgicalForge(config)
    task = DEFAULT_TASK
    if args.task_file:
        task = Path(args.task_file).read_text(encoding="utf-8")
    if args.self_test:
        suite = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=str(Path(__file__).parent),
        )
        return suite.returncode
    if args.review:
        print(json.dumps(forge.review(config.source_root, task), indent=2))
        return 0
    if args.run_build:
        receipt = forge.run_surgical_build(config.source_root, task)
        print(json.dumps(receipt, indent=2))
        return 0 if receipt["status"] == "passed_disposable_only" else 1
    return ForgeWebApp(forge).serve(open_browser=not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
