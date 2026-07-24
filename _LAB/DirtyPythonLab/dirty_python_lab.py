from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

APP_NAME = "FOXAI Dirty Python Lab"
APP_VERSION = "0.2.0"
DEFAULT_WORKSPACE = r"Z:\FOXAI\_LAB\DirtyPythonLab"
DEFAULT_QWEN_ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8788
DEFAULT_VSCODE_SEARCH_ROOT = r"Z:\Hanger Bay\Development\VSCode\4fe60c8b1c"


@dataclass(frozen=True)
class LabConfig:
    workspace_root: str = DEFAULT_WORKSPACE
    qwen_endpoint: str = DEFAULT_QWEN_ENDPOINT
    model: str = "auto"
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    max_repairs: int = 2
    run_timeout_seconds: int = 30
    request_timeout_seconds: int = 180
    max_output_characters: int = 120_000
    vscode_search_root: str = DEFAULT_VSCODE_SEARCH_ROOT
    vscode_executable: str = ""
    history_limit: int = 12

    @classmethod
    def load(cls, path: Path) -> "LabConfig":
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        clean = {key: value for key, value in raw.items() if key in allowed}
        return cls(**clean)

    def with_overrides(self, **overrides: Any) -> "LabConfig":
        values = asdict(self)
        values.update({key: value for key, value in overrides.items() if value is not None})
        return LabConfig(**values)


@dataclass
class AttemptResult:
    number: int
    code_file: str
    response_file: str
    stdout_file: str
    stderr_file: str
    return_code: int
    timed_out: bool
    duration_seconds: float
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return not self.timed_out and self.return_code == 0


@dataclass
class LabRunResult:
    run_id: str
    run_folder: str
    prompt: str
    success: bool
    attempts: list[AttemptResult]
    final_code: str
    started_at: str
    finished_at: str
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_folder": self.run_folder,
            "prompt": self.prompt,
            "success": self.success,
            "attempts": [
                {
                    **asdict(attempt),
                    "succeeded": attempt.succeeded,
                }
                for attempt in self.attempts
            ],
            "final_code": self.final_code,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }


class QwenClient:
    def __init__(self, config: LabConfig):
        self.config = config
        self._resolved_model: str | None = None

    def _models_url(self) -> str:
        models_url = self.config.qwen_endpoint
        suffix = "/v1/chat/completions"
        if models_url.endswith(suffix):
            return models_url[: -len(suffix)] + "/v1/models"
        return models_url.rstrip("/") + "/../models"

    def probe(self) -> dict[str, Any]:
        models_url = self._models_url()
        try:
            request = Request(models_url, headers={"Accept": "application/json"}, method="GET")
            with urlopen(request, timeout=min(5, self.config.request_timeout_seconds)) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            models = payload.get("data", [])
            model = ""
            if models and isinstance(models[0], dict):
                model = str(models[0].get("id", ""))
            if model:
                self._resolved_model = model
            return {
                "reachable": True,
                "endpoint": self.config.qwen_endpoint,
                "models_url": models_url,
                "model": model or self._resolved_model or "available",
                "message": "Qwen is reachable.",
            }
        except Exception as exc:
            return {
                "reachable": False,
                "endpoint": self.config.qwen_endpoint,
                "models_url": models_url,
                "model": self._resolved_model or "",
                "message": f"Qwen was not confirmed: {type(exc).__name__}: {exc}",
            }

    def _model_name(self) -> str:
        if self._resolved_model:
            return self._resolved_model
        if self.config.model and self.config.model.lower() != "auto":
            self._resolved_model = self.config.model
            return self._resolved_model

        models_url = self._models_url()
        try:
            request = Request(models_url, headers={"Accept": "application/json"}, method="GET")
            with urlopen(request, timeout=min(10, self.config.request_timeout_seconds)) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            models = payload.get("data", [])
            if models and isinstance(models[0], dict) and models[0].get("id"):
                self._resolved_model = str(models[0]["id"])
            else:
                self._resolved_model = "qwen-local"
        except Exception:
            self._resolved_model = "qwen-local"
        return self._resolved_model

    def _request(self, messages: list[dict[str, str]]) -> str:
        body = json.dumps(
            {
                "model": self._model_name(),
                "messages": messages,
                "temperature": 0.15,
                "max_tokens": 4096,
                "stream": False,
            }
        ).encode("utf-8")
        request = Request(
            self.config.qwen_endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.request_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Qwen endpoint returned HTTP {exc.code}: {details}") from exc
        except URLError as exc:
            raise RuntimeError(
                "Qwen endpoint is not reachable at "
                f"{self.config.qwen_endpoint}. Start the shared Qwen server and try again."
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError("Qwen request timed out.") from exc

        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Qwen response: {payload!r}") from exc

    @staticmethod
    def extract_python_code(response_text: str) -> str:
        fenced = re.findall(
            r"```(?:python|py)?\s*\n(.*?)```",
            response_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if fenced:
            code = max(fenced, key=len).strip()
        else:
            code = response_text.strip()
            code = re.sub(r"^\s*(?:Here(?:'s| is).*?:)\s*", "", code, flags=re.IGNORECASE)
        if not code:
            raise RuntimeError("Qwen returned no Python code.")
        return code.rstrip() + "\n"

    def generate(self, prompt: str) -> tuple[str, str]:
        system = (
            "You are the code-writing engine inside FOXAI Dirty Python Lab. "
            "Write one complete runnable Python script for the user's request. "
            "Use the Python standard library only unless the user explicitly names an already-installed package. "
            "Do not install packages. Do not modify Windows services, registry, startup items, or system files. "
            "Keep file reads and writes inside the current working directory unless the user explicitly requests another path. "
            "Return only one fenced Python code block and no explanation."
        )
        response = self._request(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
        )
        return response, self.extract_python_code(response)

    def repair(
        self,
        original_prompt: str,
        previous_code: str,
        stdout: str,
        stderr: str,
        timed_out: bool,
    ) -> tuple[str, str]:
        failure = "The script timed out." if timed_out else "The script exited with an error."
        repair_prompt = f"""
Original user request:
{original_prompt}

Previous script:
```python
{previous_code}
```

Execution result:
{failure}

STDOUT:
{stdout or '(empty)'}

STDERR:
{stderr or '(empty)'}

Return a complete corrected replacement script. Preserve the user's requested behavior. Use no package installation. Return only one fenced Python code block.
""".strip()
        system = (
            "You repair Python scripts from exact execution evidence. "
            "Return the entire corrected script, not a patch or explanation. "
            "Use one fenced Python code block only."
        )
        response = self._request(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": repair_prompt},
            ]
        )
        return response, self.extract_python_code(response)


class DirtyPythonLabEngine:
    def __init__(self, config: LabConfig):
        self.config = config
        self.root = Path(config.workspace_root)
        self.runs_root = self.root / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.client = QwenClient(config)

    def _trim(self, text: str) -> str:
        limit = self.config.max_output_characters
        if len(text) <= limit:
            return text
        half = max(1, limit // 2)
        return (
            text[:half]
            + f"\n\n--- OUTPUT TRUNCATED: {len(text) - limit} CHARACTERS OMITTED ---\n\n"
            + text[-half:]
        )

    def _create_run_folder(self) -> tuple[str, Path]:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{stamp}_{uuid.uuid4().hex[:8].upper()}"
        folder = self.runs_root / run_id
        folder.mkdir(parents=True, exist_ok=False)
        return run_id, folder

    def _execute(self, code_file: Path, run_folder: Path) -> tuple[int, bool, float, str, str]:
        env = os.environ.copy()
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                [sys.executable, "-I", str(code_file)],
                cwd=str(run_folder),
                env=env,
                text=True,
                capture_output=True,
                timeout=self.config.run_timeout_seconds,
                shell=False,
                creationflags=creationflags,
            )
            duration = time.perf_counter() - started
            return (
                completed.returncode,
                False,
                duration,
                self._trim(completed.stdout),
                self._trim(completed.stderr),
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            stderr = f"{stderr}\nExecution stopped after {self.config.run_timeout_seconds} seconds.".strip()
            return -1, True, duration, self._trim(stdout), self._trim(stderr)

    def run(self, prompt: str) -> LabRunResult:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Describe what you want the Python script to do.")

        run_id, run_folder = self._create_run_folder()
        started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        (run_folder / "PROMPT.txt").write_text(prompt + "\n", encoding="utf-8")
        attempts: list[AttemptResult] = []
        final_code = ""

        try:
            response_text, code = self.client.generate(prompt)
            for attempt_number in range(1, self.config.max_repairs + 2):
                response_file = run_folder / f"MODEL_RESPONSE_{attempt_number}.txt"
                code_file = run_folder / f"ATTEMPT_{attempt_number}.py"
                stdout_file = run_folder / f"STDOUT_{attempt_number}.txt"
                stderr_file = run_folder / f"STDERR_{attempt_number}.txt"

                response_file.write_text(response_text, encoding="utf-8")
                code_file.write_text(code, encoding="utf-8")
                return_code, timed_out, duration, stdout, stderr = self._execute(code_file, run_folder)
                stdout_file.write_text(stdout, encoding="utf-8")
                stderr_file.write_text(stderr, encoding="utf-8")

                attempt = AttemptResult(
                    number=attempt_number,
                    code_file=str(code_file),
                    response_file=str(response_file),
                    stdout_file=str(stdout_file),
                    stderr_file=str(stderr_file),
                    return_code=return_code,
                    timed_out=timed_out,
                    duration_seconds=round(duration, 3),
                    stdout=stdout,
                    stderr=stderr,
                )
                attempts.append(attempt)
                final_code = code
                if attempt.succeeded:
                    break
                if attempt_number > self.config.max_repairs:
                    break
                response_text, code = self.client.repair(
                    original_prompt=prompt,
                    previous_code=code,
                    stdout=stdout,
                    stderr=stderr,
                    timed_out=timed_out,
                )

            success = bool(attempts and attempts[-1].succeeded)
            result = LabRunResult(
                run_id=run_id,
                run_folder=str(run_folder),
                prompt=prompt,
                success=success,
                attempts=attempts,
                final_code=final_code,
                started_at=started_at,
                finished_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            )
        except Exception as exc:
            result = LabRunResult(
                run_id=run_id,
                run_folder=str(run_folder),
                prompt=prompt,
                success=False,
                attempts=attempts,
                final_code=final_code,
                started_at=started_at,
                finished_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                error=f"{type(exc).__name__}: {exc}",
            )
            (run_folder / "LAB_ERROR.txt").write_text(
                traceback.format_exc(), encoding="utf-8"
            )

        (run_folder / "RESULT.json").write_text(
            json.dumps(result.to_dict(), indent=2), encoding="utf-8"
        )
        (self.root / "LATEST_RUN.txt").write_text(str(run_folder), encoding="utf-8")
        return result

    def list_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        count = max(1, limit or self.config.history_limit)
        history: list[dict[str, Any]] = []
        try:
            folders = sorted(
                (item for item in self.runs_root.iterdir() if item.is_dir()),
                key=lambda item: item.name,
                reverse=True,
            )
        except OSError:
            return history
        for folder in folders:
            result_path = folder / "RESULT.json"
            if not result_path.is_file():
                continue
            try:
                raw = json.loads(result_path.read_text(encoding="utf-8"))
                attempts = raw.get("attempts", [])
                history.append(
                    {
                        "run_id": str(raw.get("run_id", folder.name)),
                        "run_folder": str(folder),
                        "prompt": str(raw.get("prompt", "")),
                        "success": bool(raw.get("success", False)),
                        "attempt_count": len(attempts) if isinstance(attempts, list) else 0,
                        "started_at": str(raw.get("started_at", "")),
                        "finished_at": str(raw.get("finished_at", "")),
                        "error": str(raw.get("error", "")),
                    }
                )
            except (OSError, ValueError, TypeError):
                continue
            if len(history) >= count:
                break
        return history

    def run_folder(self, run_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
            raise ValueError("Invalid run identifier.")
        folder = self.runs_root / run_id
        if not folder.is_dir():
            raise FileNotFoundError("That run folder no longer exists.")
        return folder


class WorkspaceTools:
    def __init__(self, config: LabConfig):
        self.config = config
        self.workspace = Path(config.workspace_root)
        self.state_path = self.workspace / "lab_state.json"

    def _load_state(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save_state(self, state: dict[str, Any]) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temporary.replace(self.state_path)

    @staticmethod
    def _valid_code_executable(candidate: Path) -> bool:
        return candidate.is_file() and candidate.name.lower() == "code.exe"

    def locate_vscode(self, force: bool = False) -> dict[str, Any]:
        configured = Path(self.config.vscode_executable) if self.config.vscode_executable else None
        state = self._load_state()
        remembered_value = str(state.get("vscode_executable", "")).strip()
        remembered = Path(remembered_value) if remembered_value else None

        if not force:
            for source, candidate in (("configured", configured), ("remembered", remembered)):
                if candidate and self._valid_code_executable(candidate):
                    return {
                        "found": True,
                        "path": str(candidate),
                        "source": source,
                        "search_root": self.config.vscode_search_root,
                        "message": f"Portable VS Code is ready: {candidate}",
                    }

        root = Path(self.config.vscode_search_root)
        if not root.is_dir():
            return {
                "found": False,
                "path": "",
                "source": "search",
                "search_root": str(root),
                "message": f"Portable VS Code search folder was not found: {root}",
            }

        candidates: list[Path] = []
        direct = root / "Code.exe"
        if self._valid_code_executable(direct):
            candidates.append(direct)
        try:
            for current_root, directories, files in os.walk(root):
                directories[:] = [
                    name for name in directories
                    if name.lower() not in {"node_modules", "cache", "logs", "temp", "tmp"}
                ]
                if any(name.lower() == "code.exe" for name in files):
                    candidate = Path(current_root) / next(
                        name for name in files if name.lower() == "code.exe"
                    )
                    if candidate not in candidates and self._valid_code_executable(candidate):
                        candidates.append(candidate)
        except OSError as exc:
            return {
                "found": False,
                "path": "",
                "source": "search",
                "search_root": str(root),
                "message": f"VS Code search could not finish: {exc}",
            }

        if not candidates:
            return {
                "found": False,
                "path": "",
                "source": "search",
                "search_root": str(root),
                "message": f"No Code.exe was found under {root}",
            }

        candidates.sort(key=lambda item: (len(item.relative_to(root).parts), len(str(item))))
        selected = candidates[0]
        state["vscode_executable"] = str(selected)
        state["vscode_verified_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        self._save_state(state)
        return {
            "found": True,
            "path": str(selected),
            "source": "search",
            "search_root": str(root),
            "candidate_count": len(candidates),
            "message": f"Located and remembered portable VS Code: {selected}",
        }

    def open_vscode(self) -> dict[str, Any]:
        result = self.locate_vscode(force=False)
        if not result["found"]:
            return result
        executable = Path(str(result["path"]))
        self.workspace.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(
            [str(executable), str(self.workspace)],
            cwd=str(executable.parent),
            shell=False,
        )
        return {
            **result,
            "message": f"Opened the workspace in portable VS Code: {self.workspace}",
        }


def open_path(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FOXAI Dirty Python Lab</title>
<style>
:root { color-scheme: dark; font-family: Segoe UI, Arial, sans-serif; }
body { margin: 0; background: #111218; color: #f4f1ff; font-size: 22px; }
main { max-width: 1240px; margin: 0 auto; padding: 28px; }
h1 { font-size: 46px; margin: 0 0 8px; }
h2 { font-size: 30px; margin-top: 0; }
.subtitle { color: #c9bedf; margin-bottom: 24px; }
.card { background: #1d1f2a; border: 2px solid #4a4260; border-radius: 16px; padding: 22px; margin: 18px 0; }
.readiness { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 14px; }
.readiness-item { background: #11131a; border-radius: 12px; padding: 16px; min-height: 72px; }
.readiness-item strong { display: block; font-size: 18px; color: #c9bedf; margin-bottom: 6px; }
.ready { border-left: 8px solid #62d696; }
.not-ready { border-left: 8px solid #ef7f7f; }
.unknown { border-left: 8px solid #d6bb68; }
textarea { width: 100%; min-height: 220px; box-sizing: border-box; resize: vertical; border-radius: 12px; border: 2px solid #7f6aa8; background: #0e0f14; color: white; padding: 18px; font-size: 25px; line-height: 1.35; }
button { border: 0; border-radius: 12px; padding: 18px 24px; font-size: 23px; font-weight: 700; cursor: pointer; margin: 8px 8px 8px 0; }
.primary { background: #8d64d8; color: #100b18; min-width: 355px; min-height: 76px; }
.secondary { background: #d6c7f2; color: #17121e; min-width: 290px; min-height: 70px; }
.code { background: #83c7db; color: #07191f; min-width: 355px; min-height: 70px; }
.small-button { padding: 11px 15px; min-width: 0; min-height: 0; font-size: 18px; }
.danger { background: #d88b8b; color: #251010; min-width: 210px; }
button:disabled { opacity: .48; cursor: not-allowed; }
.status { font-weight: 700; padding: 15px; border-radius: 10px; background: #11131a; margin-top: 10px; }
.success { border-left: 10px solid #62d696; }
.failure { border-left: 10px solid #ef7f7f; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #0d0e13; border-radius: 10px; padding: 16px; font-size: 18px; line-height: 1.35; max-height: 440px; overflow: auto; }
details { margin: 14px 0; }
summary { cursor: pointer; font-weight: 700; font-size: 24px; }
.small { font-size: 17px; color: #c7bfd4; }
.path { font-family: Consolas, monospace; font-size: 16px; overflow-wrap: anywhere; }
.history-row { border-top: 1px solid #4a4260; padding: 14px 0; }
.history-row:first-child { border-top: 0; }
.history-title { font-size: 20px; font-weight: 700; }
.history-meta { font-size: 16px; color: #c7bfd4; }
@media (max-width: 850px) { .readiness { grid-template-columns: 1fr; } }
@media (max-width: 720px) { main { padding: 16px; } h1 { font-size: 34px; } button, .primary, .secondary, .code { width: 100%; min-width: 0; } }
</style>
</head>
<body>
<main>
<h1>FOXAI Dirty Python Lab</h1>
<div class="subtitle">Describe it. Qwen writes it. The lab runs it, reads the errors, repairs it, and tries again.</div>

<div class="card">
<h2>System Readiness</h2>
<div class="readiness">
<div id="pythonReady" class="readiness-item unknown"><strong>HANGER BAY PYTHON</strong><span>Checking...</span></div>
<div id="qwenReady" class="readiness-item unknown"><strong>SHARED QWEN</strong><span>Checking...</span></div>
<div id="codeReady" class="readiness-item unknown"><strong>PORTABLE VS CODE</strong><span>Checking...</span></div>
</div>
<button class="secondary small-button" onclick="refreshPreflight(true)">CHECK AGAIN</button>
<button class="secondary small-button" onclick="locateVSCode()">FIND PORTABLE VS CODE</button>
</div>

<div class="card">
<label for="prompt"><strong>What should Python build or do?</strong></label>
<textarea id="prompt" placeholder="Example: Make a script that scans this run folder and prints the ten largest files."></textarea>
<div>
<button id="run" class="primary" onclick="runLab()">RUN &amp; AUTO-REPAIR</button>
<button class="secondary" onclick="openWorkspace()">OPEN WORKSPACE</button>
<button id="openCode" class="code" onclick="openVSCode()" disabled>OPEN IN PORTABLE VS CODE</button>
<button class="danger" onclick="stopLab()">STOP LAB</button>
</div>
<div id="status" class="status">Ready. Checking the local tools now.</div>
<div class="small">Every run is saved in a separate folder. Existing runs are never overwritten.</div>
</div>

<div id="result"></div>

<div class="card">
<h2>Recent Runs</h2>
<div id="history"><div class="small">Loading saved runs...</div></div>
</div>
</main>
<script>
function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function setReady(id, state, text, detail='') {
  const box = document.getElementById(id);
  box.className = `readiness-item ${state}`;
  box.querySelector('span').innerHTML = `${esc(text)}${detail ? `<div class="path">${esc(detail)}</div>` : ''}`;
}
async function refreshPreflight(force=false) {
  try {
    const response = await fetch(`/api/preflight${force ? '?force=1' : ''}`, {cache:'no-store'});
    const data = await response.json();
    setReady('pythonReady', data.python.available ? 'ready' : 'not-ready', data.python.available ? `Ready — ${data.python.version}` : 'Not available', data.python.executable);
    setReady('qwenReady', data.qwen.reachable ? 'ready' : 'not-ready', data.qwen.reachable ? `Ready — ${data.qwen.model}` : 'Not confirmed', data.qwen.endpoint);
    setReady('codeReady', data.vscode.found ? 'ready' : 'unknown', data.vscode.found ? 'Ready' : 'Not located yet', data.vscode.found ? data.vscode.path : data.vscode.search_root);
    document.getElementById('openCode').disabled = !data.vscode.found;
  } catch (error) {
    document.getElementById('status').textContent = `Readiness check failed: ${error.message}`;
  }
}
async function runLab() {
  const prompt = document.getElementById('prompt').value.trim();
  const button = document.getElementById('run');
  const status = document.getElementById('status');
  const result = document.getElementById('result');
  if (!prompt) { status.textContent = 'Please describe what you want Python to do.'; return; }
  button.disabled = true;
  result.innerHTML = '';
  status.textContent = 'Qwen is writing the first script. The lab will run and repair it automatically.';
  try {
    const response = await fetch('/api/run', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({prompt})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The lab request failed.');
    const cls = data.success ? 'success' : 'failure';
    const heading = data.success ? 'SUCCESS' : 'NOT FIXED YET';
    status.textContent = data.success ? `Finished successfully after ${data.attempts.length} attempt(s).` : `Stopped after ${data.attempts.length} attempt(s). Exact evidence was saved.`;
    const attempts = data.attempts.map(a => `
      <details ${a.number === data.attempts.length ? 'open' : ''}>
        <summary>Attempt ${a.number}: ${a.succeeded ? 'worked' : (a.timed_out ? 'timed out' : 'failed')}</summary>
        <p>Return code: ${a.return_code} &nbsp; | &nbsp; Time: ${a.duration_seconds}s</p>
        <strong>STDOUT</strong><pre>${esc(a.stdout || '(empty)')}</pre>
        <strong>STDERR</strong><pre>${esc(a.stderr || '(empty)')}</pre>
      </details>`).join('');
    result.innerHTML = `<div class="card ${cls}"><h2>${heading}</h2><p><strong>Run folder:</strong> <span class="path">${esc(data.run_folder)}</span></p><button class="secondary small-button" onclick="openRun('${esc(data.run_id)}')">OPEN THIS RUN</button>${data.error ? `<p><strong>Lab error:</strong> ${esc(data.error)}</p>` : ''}${attempts}<details><summary>Final Python script</summary><pre>${esc(data.final_code)}</pre></details></div>`;
    await refreshHistory();
  } catch (error) {
    status.textContent = 'The lab could not complete the request.';
    result.innerHTML = `<div class="card failure"><h2>LAB ERROR</h2><pre>${esc(error.message)}</pre></div>`;
  } finally {
    button.disabled = false;
  }
}
async function refreshHistory() {
  const host = document.getElementById('history');
  try {
    const response = await fetch('/api/history', {cache:'no-store'});
    const data = await response.json();
    if (!data.runs.length) { host.innerHTML = '<div class="small">No runs have been saved yet.</div>'; return; }
    host.innerHTML = data.runs.map(run => `
      <div class="history-row">
        <div class="history-title">${run.success ? '✓' : '✗'} ${esc(run.prompt || '(prompt unavailable)')}</div>
        <div class="history-meta">${esc(run.started_at)} — ${run.attempt_count} attempt(s)</div>
        <button class="secondary small-button" onclick="openRun('${esc(run.run_id)}')">OPEN RUN FOLDER</button>
      </div>`).join('');
  } catch (error) {
    host.innerHTML = `<div class="small">Could not load history: ${esc(error.message)}</div>`;
  }
}
async function postAction(url, body=null) {
  const response = await fetch(url, {method:'POST', headers: body ? {'Content-Type':'application/json'} : {}, body: body ? JSON.stringify(body) : undefined});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.message || 'Action failed.');
  return data;
}
async function openWorkspace() {
  const status = document.getElementById('status');
  try { const data = await postAction('/api/open-workspace'); status.textContent = data.message; }
  catch (error) { status.textContent = error.message; }
}
async function locateVSCode() {
  const status = document.getElementById('status');
  status.textContent = 'Searching the known portable VS Code folder for the exact Code.exe.';
  try { const data = await postAction('/api/vscode/locate', {force:true}); status.textContent = data.message; await refreshPreflight(); }
  catch (error) { status.textContent = error.message; }
}
async function openVSCode() {
  const status = document.getElementById('status');
  try { const data = await postAction('/api/open-vscode'); status.textContent = data.message; }
  catch (error) { status.textContent = error.message; }
}
async function openRun(runId) {
  const status = document.getElementById('status');
  try { const data = await postAction('/api/open-run', {run_id:runId}); status.textContent = data.message; }
  catch (error) { status.textContent = error.message; }
}
async function stopLab() {
  const status = document.getElementById('status');
  status.textContent = 'Stopping the local lab server. You may close this browser tab.';
  await fetch('/api/shutdown', {method:'POST'}).catch(() => {});
}
refreshPreflight();
refreshHistory();
</script>
</body>
</html>"""


class LabApplication:
    def __init__(self, config: LabConfig):
        self.config = config
        self.engine = DirtyPythonLabEngine(config)
        self.tools = WorkspaceTools(config)
        self._run_lock = threading.Lock()
        self.server: ThreadingHTTPServer | None = None

    def make_handler(self) -> type[BaseHTTPRequestHandler]:
        app = self

        class Handler(BaseHTTPRequestHandler):
            server_version = f"DirtyPythonLab/{APP_VERSION}"

            def log_message(self, fmt: str, *args: Any) -> None:
                print(f"[{self.log_date_time_string()}] {fmt % args}")

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _read_json(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 1_000_000:
                    raise ValueError("Invalid request size.")
                raw = self.rfile.read(length)
                value = json.loads(raw.decode("utf-8"))
                if not isinstance(value, dict):
                    raise ValueError("JSON object required.")
                return value

            def do_GET(self) -> None:
                if self.path == "/":
                    body = HTML_PAGE.encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                request_path = self.path.split("?", 1)[0]
                if request_path == "/api/status":
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "app": APP_NAME,
                            "version": APP_VERSION,
                            "workspace": str(app.engine.root),
                            "qwen_endpoint": app.config.qwen_endpoint,
                            "busy": app._run_lock.locked(),
                        },
                    )
                    return
                if request_path == "/api/preflight":
                    force = "force=1" in self.path
                    vscode = app.tools.locate_vscode(force=force)
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "python": {
                                "available": Path(sys.executable).is_file(),
                                "executable": sys.executable,
                                "version": ".".join(map(str, sys.version_info[:3])),
                            },
                            "qwen": app.engine.client.probe(),
                            "vscode": vscode,
                        },
                    )
                    return
                if request_path == "/api/history":
                    self._send_json(
                        HTTPStatus.OK,
                        {"runs": app.engine.list_history()},
                    )
                    return
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

            def do_POST(self) -> None:
                if self.path == "/api/run":
                    if not app._run_lock.acquire(blocking=False):
                        self._send_json(
                            HTTPStatus.CONFLICT,
                            {"error": "The lab is already running another request."},
                        )
                        return
                    try:
                        data = self._read_json()
                        result = app.engine.run(str(data.get("prompt", "")))
                        self._send_json(HTTPStatus.OK, result.to_dict())
                    except ValueError as exc:
                        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    except Exception as exc:
                        self._send_json(
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                            {"error": f"{type(exc).__name__}: {exc}"},
                        )
                    finally:
                        app._run_lock.release()
                    return

                if self.path == "/api/open-workspace":
                    try:
                        open_path(app.engine.root)
                        self._send_json(
                            HTTPStatus.OK,
                            {"message": f"Opened {app.engine.root}"},
                        )
                    except Exception as exc:
                        self._send_json(
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                            {"error": f"Could not open workspace: {exc}"},
                        )
                    return

                if self.path == "/api/vscode/locate":
                    try:
                        data = self._read_json()
                        result = app.tools.locate_vscode(force=bool(data.get("force", True)))
                        status = HTTPStatus.OK if result["found"] else HTTPStatus.NOT_FOUND
                        self._send_json(status, result if result["found"] else {**result, "error": result["message"]})
                    except Exception as exc:
                        self._send_json(
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                            {"error": f"VS Code search failed: {type(exc).__name__}: {exc}"},
                        )
                    return

                if self.path == "/api/open-vscode":
                    try:
                        result = app.tools.open_vscode()
                        status = HTTPStatus.OK if result["found"] else HTTPStatus.NOT_FOUND
                        self._send_json(status, result if result["found"] else {**result, "error": result["message"]})
                    except Exception as exc:
                        self._send_json(
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                            {"error": f"Could not open portable VS Code: {type(exc).__name__}: {exc}"},
                        )
                    return

                if self.path == "/api/open-run":
                    try:
                        data = self._read_json()
                        folder = app.engine.run_folder(str(data.get("run_id", "")))
                        open_path(folder)
                        self._send_json(HTTPStatus.OK, {"message": f"Opened {folder}"})
                    except (ValueError, FileNotFoundError) as exc:
                        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    except Exception as exc:
                        self._send_json(
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                            {"error": f"Could not open run folder: {type(exc).__name__}: {exc}"},
                        )
                    return

                if self.path == "/api/shutdown":
                    self._send_json(HTTPStatus.OK, {"message": "Stopping."})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return

                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

        return Handler

    def serve(self, open_browser: bool = True) -> int:
        url = f"http://{self.config.host}:{self.config.port}/"
        try:
            self.server = ThreadingHTTPServer((self.config.host, self.config.port), self.make_handler())
        except OSError as exc:
            if getattr(exc, "winerror", None) == 10048 or getattr(exc, "errno", None) in {48, 98}:
                try:
                    with urlopen(f"{url}api/status", timeout=2) as response:
                        status = json.loads(response.read().decode("utf-8", errors="replace"))
                    if status.get("app") == APP_NAME:
                        print(f"{APP_NAME} is already running at {url}")
                        if open_browser:
                            webbrowser.open(url)
                        return 0
                except Exception:
                    pass
                print(f"Port {self.config.port} is already being used by another program.")
                print("Dirty Python Lab did not start or change anything.")
                return 1
            raise
        print(f"{APP_NAME} {APP_VERSION}")
        print(f"Workspace: {self.engine.root}")
        print(f"Qwen: {self.config.qwen_endpoint}")
        print(f"Open: {url}")
        if open_browser:
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        try:
            self.server.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            pass
        finally:
            self.server.server_close()
        return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.json")))
    parser.add_argument("--workspace")
    parser.add_argument("--endpoint")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--locate-vscode", action="store_true")
    parser.add_argument("--acceptance-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = LabConfig.load(Path(args.config)).with_overrides(
        workspace_root=args.workspace,
        qwen_endpoint=args.endpoint,
        host=args.host,
        port=args.port,
    )
    if args.locate_vscode:
        result = WorkspaceTools(config).locate_vscode(force=True)
        print(result["message"])
        if result.get("path"):
            print(result["path"])
        return 0 if result["found"] else 1
    if args.acceptance_test:
        engine = DirtyPythonLabEngine(config)
        result = engine.run(
            "Write a Python standard-library script that prints exactly "
            "DIRTY PYTHON LAB LIVE TEST OK and then exits successfully."
        )
        print(f"Run folder: {result.run_folder}")
        print(f"Attempts: {len(result.attempts)}")
        if result.attempts:
            print("Final stdout:")
            print(result.attempts[-1].stdout or "(empty)")
            if result.attempts[-1].stderr:
                print("Final stderr:")
                print(result.attempts[-1].stderr)
        if result.error:
            print(f"Lab error: {result.error}")
        print("LIVE ACCEPTANCE CHECK PASSED." if result.success else "LIVE ACCEPTANCE CHECK FAILED.")
        return 0 if result.success else 1
    app = LabApplication(config)
    return app.serve(open_browser=not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
