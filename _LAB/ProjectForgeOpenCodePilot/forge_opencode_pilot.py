from __future__ import annotations

import hashlib
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / "Runtime"
OPENCODE_EXE = RUNTIME_DIR / "opencode.exe"
CONFIG_DIR = ROOT / "Config"
PROJECTS_DIR = ROOT / "PilotProjects"
RECEIPTS_DIR = ROOT / "Receipts"
LOGS_DIR = ROOT / "Logs"
STATE_DIR = ROOT / "State"
PORTABLE_HOME = ROOT / "PortableHome"
DOWNLOAD_URL = "https://github.com/anomalyco/opencode/releases/latest/download/opencode-windows-x64.zip"
QWEN_API_BASE = "http://127.0.0.1:8080/v1"
QWEN_MODELS_URL = QWEN_API_BASE + "/models"
DEFAULT_HANGER_PYTHON = Path(r"Z:\Hanger Bay\Development\Python\python.exe")
DEFAULT_GIT_CANDIDATES = [
    Path(r"Z:\Hanger Bay\Development\Git\cmd\git.exe"),
    Path(r"Z:\Hanger Bay\Development\Git\bin\git.exe"),
]
HOST_AUDIT_PATHS = [
    Path.home() / ".local" / "share" / "opencode",
    Path.home() / ".cache" / "opencode",
    Path.home() / ".config" / "opencode",
    Path.home() / ".opencode",
]

for folder in (RUNTIME_DIR, CONFIG_DIR, PROJECTS_DIR, RECEIPTS_DIR, LOGS_DIR, STATE_DIR, PORTABLE_HOME):
    folder.mkdir(parents=True, exist_ok=True)

STATE_LOCK = threading.Lock()
STATE: dict[str, Any] = {
    "stage": "Ready",
    "message": "Install the native OpenCode runtime, then run the isolated repair pilot.",
    "busy": False,
    "job": None,
    "error": None,
    "installed": OPENCODE_EXE.is_file(),
    "latest_receipt": None,
    "latest_project": None,
}


class PilotError(RuntimeError):
    pass


def set_state(**updates: Any) -> None:
    with STATE_LOCK:
        STATE.update(updates)


def snapshot_state() -> dict[str, Any]:
    with STATE_LOCK:
        return dict(STATE)


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_command(args: list[str | Path], *, cwd: Path | None = None, env: dict[str, str] | None = None,
                timeout: int = 120, log_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [str(x) for x in args]
    started = time.monotonic()
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        err = exc.stderr if isinstance(exc.stderr, str) else ""
        cp = subprocess.CompletedProcess(cmd, 124, out, err + "\nCOMMAND TIMED OUT")
    except OSError as exc:
        raise PilotError(f"Could not start {cmd[0]}: {exc}") from exc
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            "COMMAND:\n" + " ".join(cmd) +
            f"\n\nEXIT CODE: {cp.returncode}\nELAPSED SECONDS: {time.monotonic()-started:.2f}\n\nSTDOUT:\n{cp.stdout}\n\nSTDERR:\n{cp.stderr}\n",
            encoding="utf-8",
        )
    return cp


def locate_hanger_python() -> Path:
    override = os.environ.get("PROJECT_FORGE_HANGER_PYTHON")
    path = Path(override) if override else DEFAULT_HANGER_PYTHON
    if not path.is_file():
        if os.name != "nt" and Path(sys.executable).is_file():
            return Path(sys.executable)
        raise PilotError(f"Hanger Bay Python was not found at {path}")
    return path


def locate_git() -> Path:
    override = os.environ.get("PROJECT_FORGE_GIT")
    if override and Path(override).is_file():
        return Path(override)
    found = shutil.which("git")
    if found:
        return Path(found)
    for path in DEFAULT_GIT_CANDIDATES:
        if path.is_file():
            return path
    root = Path(r"Z:\Hanger Bay\Development\Git")
    if root.is_dir():
        for path in root.rglob("git.exe"):
            if path.is_file():
                return path
    raise PilotError("Git was not found in Hanger Bay or PATH.")


def locate_git_bash() -> str | None:
    for path in [
        Path(r"Z:\Hanger Bay\Development\Git\bin\bash.exe"),
        Path(r"Z:\Hanger Bay\Development\Git\usr\bin\bash.exe"),
    ]:
        if path.is_file():
            return str(path)
    return None


def opencode_path() -> Path:
    override = os.environ.get("PROJECT_FORGE_OPENCODE_EXE")
    return Path(override) if override else OPENCODE_EXE


def install_opencode() -> dict[str, Any]:
    if os.name != "nt" and not os.environ.get("PROJECT_FORGE_ALLOW_NONWINDOWS_INSTALL"):
        raise PilotError("The official portable runtime installer is for Windows x64.")
    set_state(stage="Downloading OpenCode", message="Downloading the official Windows x64 release from GitHub.")
    archive = RUNTIME_DIR / "opencode-windows-x64.zip.download"
    request = urllib.request.Request(DOWNLOAD_URL, headers={"User-Agent": "ProjectForge-OpenCode-Pilot/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        archive.unlink(missing_ok=True)
        raise PilotError(f"OpenCode download failed: {exc}") from exc
    if archive.stat().st_size < 1_000_000:
        raise PilotError("The downloaded OpenCode archive is unexpectedly small.")

    set_state(stage="Extracting OpenCode", message="Extracting the native Windows executable into Runtime.")
    extract_dir = RUNTIME_DIR / "_extract"
    shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extract_dir)
    except (zipfile.BadZipFile, OSError) as exc:
        raise PilotError(f"The OpenCode archive could not be extracted: {exc}") from exc
    candidates = [p for p in extract_dir.rglob("opencode.exe") if p.is_file()]
    if not candidates:
        raise PilotError("The official archive did not contain opencode.exe.")
    shutil.copy2(max(candidates, key=lambda p: p.stat().st_size), OPENCODE_EXE)
    shutil.rmtree(extract_dir, ignore_errors=True)
    archive.unlink(missing_ok=True)

    signature = "not_checked"
    if os.name == "nt":
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if ps:
            escaped = str(OPENCODE_EXE).replace("'", "''")
            check = run_command(
                [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                 f"(Get-AuthenticodeSignature -LiteralPath '{escaped}').Status"],
                timeout=60,
                log_path=LOGS_DIR / f"OPENCODE_SIGNATURE_{stamp()}.txt",
            )
            signature = check.stdout.strip() or check.stderr.strip() or "unknown"
            if check.returncode != 0 or signature.lower() != "valid":
                OPENCODE_EXE.unlink(missing_ok=True)
                raise PilotError(f"OpenCode signature verification did not return Valid. Result: {signature}")

    version = run_command([OPENCODE_EXE, "--version"], timeout=60,
                          log_path=LOGS_DIR / f"OPENCODE_VERSION_{stamp()}.txt")
    if version.returncode != 0:
        OPENCODE_EXE.unlink(missing_ok=True)
        raise PilotError("opencode.exe was extracted but did not start successfully.")
    receipt = {
        "schema": "project_forge_opencode_install_v1",
        "status": "installed_verified",
        "created_at": datetime.now().astimezone().isoformat(),
        "download_url": DOWNLOAD_URL,
        "opencode_exe": str(OPENCODE_EXE),
        "version": (version.stdout or version.stderr).strip(),
        "authenticode_status": signature,
        "sha256": sha256(OPENCODE_EXE),
    }
    paths = write_receipt("OPENCODE_INSTALL_RECEIPT", receipt)
    set_state(installed=True, latest_receipt=str(paths[1]), stage="OPENCODE READY",
              message=f"Native runtime verified: {receipt['version']}")
    return receipt


def detect_model() -> str:
    request = urllib.request.Request(QWEN_MODELS_URL, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise PilotError("The local model server is not responding at 127.0.0.1:8080. Start Qwen3-Coder first.") from exc
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise PilotError("The local /v1/models response did not contain a model.")
    model_id = str(rows[0].get("id", "")).strip()
    if not model_id:
        raise PilotError("The local server returned an empty model ID.")
    return model_id


def portable_env(config_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "HOME": str(PORTABLE_HOME),
        "XDG_CONFIG_HOME": str(STATE_DIR / "config"),
        "XDG_DATA_HOME": str(STATE_DIR / "data"),
        "XDG_CACHE_HOME": str(STATE_DIR / "cache"),
        "OPENCODE_CONFIG": str(config_path),
        "OPENCODE_CONFIG_DIR": str(CONFIG_DIR),
        "OPENCODE_DISABLE_AUTOUPDATE": "true",
        "OPENCODE_DISABLE_LSP_DOWNLOAD": "true",
        "OPENCODE_DISABLE_DEFAULT_PLUGINS": "true",
        "OPENCODE_DISABLE_MODELS_FETCH": "true",
        "OPENCODE_DISABLE_CLAUDE_CODE": "true",
        "OPENCODE_AUTO_SHARE": "false",
        "OPENCODE_DISABLE_TERMINAL_TITLE": "true",
    })
    bash = locate_git_bash()
    if bash:
        env["OPENCODE_GIT_BASH_PATH"] = bash
    for folder in (STATE_DIR / "config", STATE_DIR / "data", STATE_DIR / "cache"):
        folder.mkdir(parents=True, exist_ok=True)
    return env


def make_config(model_id: str, project: Path) -> Path:
    config = {
        "$schema": "https://opencode.ai/config.json",
        "model": f"localqwen/{model_id}",
        "small_model": f"localqwen/{model_id}",
        "default_agent": "build",
        "autoupdate": False,
        "share": "disabled",
        "enabled_providers": ["localqwen"],
        "instructions": [str(project / "PROJECT_FORGE_RULES.md")],
        "provider": {
            "localqwen": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "FOXAI Local Qwen",
                "options": {"baseURL": QWEN_API_BASE, "apiKey": "local-only"},
                "models": {
                    model_id: {
                        "name": model_id,
                        "limit": {"context": 16384, "output": 4096},
                    }
                },
            }
        },
        "permission": {
            "read": "allow", "edit": "allow", "glob": "allow", "grep": "allow", "list": "allow",
            "task": "deny", "skill": "deny", "lsp": "deny", "webfetch": "deny", "websearch": "deny",
            "external_directory": "deny", "doom_loop": "ask",
            "bash": {
                "*": "allow",
                "git push*": "deny", "git remote*": "deny",
                "curl *": "deny", "wget *": "deny",
                "powershell *": "deny", "pwsh *": "deny",
                "del *": "deny", "erase *": "deny", "rd *": "deny", "rmdir *": "deny", "rm *": "deny",
                "shutdown *": "deny", "taskkill *": "deny", "reg *": "deny", "sc *": "deny",
            },
        },
    }
    path = project / "opencode.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def create_project(project: Path) -> None:
    project.mkdir(parents=True, exist_ok=False)
    (project / "calculator.py").write_text(
        '"""Intentionally broken Project Forge pilot module."""\n\n'
        'def safe_divide(numerator, denominator):\n'
        '    return numerator * denominator  # intentional bug\n\n'
        'def average(values):\n'
        '    return sum(values) / len(values)  # intentional empty-list bug\n', encoding="utf-8")
    (project / "test_calculator.py").write_text(
        'import unittest\n\nfrom calculator import average, safe_divide\n\n'
        'class CalculatorTests(unittest.TestCase):\n'
        '    def test_safe_divide(self):\n        self.assertEqual(safe_divide(12, 3), 4)\n\n'
        '    def test_zero(self):\n        with self.assertRaisesRegex(ValueError, "zero"):\n            safe_divide(12, 0)\n\n'
        '    def test_average(self):\n        self.assertEqual(average([2, 4, 6]), 4.0)\n\n'
        '    def test_empty(self):\n        self.assertEqual(average([]), 0.0)\n\n'
        'if __name__ == "__main__":\n    unittest.main()\n', encoding="utf-8")
    (project / "PROJECT_FORGE_RULES.md").write_text(
        "# Project Forge Pilot Rules\n\n"
        "Work only inside the current disposable project. Do not access external directories. "
        "Do not use networking, installers, package managers, subprocess launching, or endless loops. "
        "Edit calculator.py only. test_calculator.py is protected and must remain byte-for-byte unchanged. "
        "Run the supplied unittest suite after edits. Continue repairing until all tests pass.\n", encoding="utf-8")
    (project / "TASK.txt").write_text(
        "Repair calculator.py so every test in test_calculator.py passes.\n"
        "Do not edit the tests. Use only the Python standard library. Run the tests and keep repairing until they pass.\n", encoding="utf-8")
    (project / ".gitignore").write_text(
        "opencode.json\nPROJECT_FORGE_RULES.md\nTASK.txt\nOPENCODE_COMMAND_LOG.txt\nTEST_*.txt\nCOMPILE_CHECK.txt\nSUCCESS_DIFF.patch\nHOST_WRITE_AUDIT.txt\n__pycache__/\n", encoding="utf-8")


def tree_snapshot(paths: list[Path]) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for base in paths:
        try:
            if base.is_file():
                st = base.stat()
                result[str(base)] = (st.st_size, st.st_mtime_ns)
            elif base.is_dir():
                for path in base.rglob("*"):
                    if path.is_file():
                        try:
                            st = path.stat()
                            result[str(path)] = (st.st_size, st.st_mtime_ns)
                        except OSError:
                            pass
        except OSError:
            pass
    return result


def run_pilot() -> dict[str, Any]:
    exe = opencode_path()
    if not exe.is_file():
        raise PilotError("OpenCode is not installed in Runtime yet. Use INSTALL OPENCODE first.")
    python_exe = locate_hanger_python()
    git = locate_git()
    set_state(stage="Checking local model", message="Reading the exact model ID from 127.0.0.1:8080/v1/models.")
    model_id = detect_model()
    run_id = stamp() + "_" + os.urandom(4).hex().upper()
    project = PROJECTS_DIR / run_id
    create_project(project)
    set_state(latest_project=str(project), stage="Creating broken Git baseline", message=str(project))

    def git_run(*args: str, timeout: int = 60, log: str | None = None) -> subprocess.CompletedProcess[str]:
        return run_command([git, *args], cwd=project, timeout=timeout,
                           log_path=(project / log) if log else None)

    checks = [
        git_run("init", log="GIT_INIT.txt"),
        git_run("config", "user.name", "Project Forge OpenCode Pilot"),
        git_run("config", "user.email", "project-forge@localhost"),
        git_run("add", "calculator.py", "test_calculator.py", ".gitignore"),
        git_run("commit", "-m", "Broken baseline for OpenCode pilot"),
    ]
    if any(x.returncode != 0 for x in checks):
        raise PilotError("Could not create the disposable Git baseline. Open the project logs.")
    baseline = git_run("rev-parse", "HEAD").stdout.strip()
    test_hash_before = sha256(project / "test_calculator.py")
    initial = run_command([python_exe, "-m", "unittest", "discover", "-v"], cwd=project, timeout=120,
                          log_path=project / "TEST_BEFORE_OPENCODE.txt")
    if initial.returncode == 0:
        raise PilotError("The intentionally broken baseline unexpectedly passed.")

    config_path = make_config(model_id, project)
    env = portable_env(config_path)
    host_before = tree_snapshot(HOST_AUDIT_PATHS)
    prompt = (project / "TASK.txt").read_text(encoding="utf-8")
    output_log = project / "OPENCODE_COMMAND_LOG.txt"
    set_state(stage="OpenCode and Qwen3-Coder are repairing", message="This may take several minutes. Live FOXAI remains untouched.")
    result = run_command([
        exe, "run", "--auto", "--model", f"localqwen/{model_id}", "--agent", "build",
        "--dir", project, "--format", "json", prompt,
    ], cwd=project, env=env, timeout=1800, log_path=output_log)

    host_after = tree_snapshot(HOST_AUDIT_PATHS)
    host_changes = sorted(path for path, meta in host_after.items() if host_before.get(path) != meta)
    (project / "HOST_WRITE_AUDIT.txt").write_text(
        "HOST PROFILE WRITES DETECTED:\n" + ("\n".join(host_changes) if host_changes else "NONE DETECTED") + "\n",
        encoding="utf-8")

    set_state(stage="Independent acceptance checks", message="Compiling, testing, checking protected files, and proving rollback.")
    final_test = run_command([python_exe, "-m", "unittest", "discover", "-v"], cwd=project, timeout=120,
                             log_path=project / "TEST_AFTER_OPENCODE.txt")
    compile_check = run_command([python_exe, "-m", "py_compile", project / "calculator.py", project / "test_calculator.py"],
                                cwd=project, timeout=120, log_path=project / "COMPILE_CHECK.txt")
    tests_unchanged = test_hash_before == sha256(project / "test_calculator.py")
    status = git_run("status", "--porcelain")
    if status.stdout.strip():
        git_run("add", "-A")
        commit = git_run("commit", "-m", "Project Forge pilot repaired by OpenCode")
        if commit.returncode != 0:
            raise PilotError("The repaired pilot could not be committed.")
    success_commit = git_run("rev-parse", "HEAD").stdout.strip()
    changed = baseline != success_commit
    diff = git_run("diff", "--binary", baseline, success_commit, timeout=120)
    (project / "SUCCESS_DIFF.patch").write_text(diff.stdout, encoding="utf-8")

    rollback_reset = git_run("reset", "--hard", baseline)
    rollback_test = run_command([python_exe, "-m", "unittest", "discover", "-v"], cwd=project, timeout=120,
                                log_path=project / "TEST_AFTER_ROLLBACK.txt")
    restore_reset = git_run("reset", "--hard", success_commit)
    restore_test = run_command([python_exe, "-m", "unittest", "discover", "-v"], cwd=project, timeout=120,
                               log_path=project / "TEST_AFTER_RESTORE.txt")
    rollback_proven = (
        rollback_reset.returncode == 0 and rollback_test.returncode != 0 and
        restore_reset.returncode == 0 and restore_test.returncode == 0
    )
    functional_pass = (
        result.returncode == 0 and final_test.returncode == 0 and compile_check.returncode == 0 and
        tests_unchanged and changed and rollback_proven
    )
    portability_pass = not host_changes
    status_text = "passed" if functional_pass and portability_pass else (
        "functional_pass_portability_review" if functional_pass else "not_passed"
    )
    receipt = {
        "schema": "project_forge_opencode_pilot_v1",
        "status": status_text,
        "created_at": datetime.now().astimezone().isoformat(),
        "run_id": run_id,
        "project_folder": str(project),
        "scope": "disposable_pilot_project_only",
        "live_foxai_modified": False,
        "model_id": model_id,
        "opencode_exe": str(exe),
        "opencode_exit_code": result.returncode,
        "initial_test_exit_code": initial.returncode,
        "final_test_exit_code": final_test.returncode,
        "compile_exit_code": compile_check.returncode,
        "tests_file_unchanged": tests_unchanged,
        "project_changed": changed,
        "rollback_proven": rollback_proven,
        "host_profile_write_count": len(host_changes),
        "host_profile_writes": host_changes,
        "functional_pass": functional_pass,
        "portable_state_contained": portability_pass,
        "baseline_commit": baseline,
        "success_commit": success_commit,
    }
    receipt_paths = write_receipt("PILOT_" + run_id, receipt)
    set_state(latest_receipt=str(receipt_paths[1]))
    if not functional_pass:
        raise PilotError(f"The OpenCode pilot did not satisfy every functional check. Open {receipt_paths[1]}")
    if not portability_pass:
        set_state(stage="FUNCTIONAL PASS — PORTABILITY REVIEW",
                  message=f"Repair and rollback passed, but {len(host_changes)} host-profile writes were detected.")
    else:
        set_state(stage="PILOT PASSED",
                  message="OpenCode repaired the project, tests passed, rollback worked, and no host-profile writes were detected.")
    return receipt


def start_opencode_web() -> None:
    exe = opencode_path()
    if not exe.is_file():
        raise PilotError("OpenCode is not installed yet.")
    model_id = detect_model()
    project_text = snapshot_state().get("latest_project")
    if project_text and Path(project_text).is_dir():
        project = Path(project_text)
    else:
        project = PROJECTS_DIR / (stamp() + "_WEB_WORKSPACE")
        project.mkdir(parents=True, exist_ok=True)
        (project / "README.txt").write_text("Project Forge OpenCode web workspace.\n", encoding="utf-8")
        (project / "PROJECT_FORGE_RULES.md").write_text(
            "Work only inside this workspace. No web access or external directories.\n", encoding="utf-8")
    config = make_config(model_id, project)
    env = portable_env(config)
    creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    subprocess.Popen(
        [str(exe), "web", "--hostname", "127.0.0.1", "--port", "8791"],
        cwd=str(project), env=env, creationflags=creationflags,
    )
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8791")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_receipt(stem: str, data: dict[str, Any]) -> tuple[Path, Path]:
    json_path = RECEIPTS_DIR / f"{stem}.json"
    txt_path = RECEIPTS_DIR / f"{stem}.txt"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = ["PROJECT FORGE — OPENCODE RECEIPT", "=" * 40]
    for key in (
        "status", "created_at", "run_id", "project_folder", "model_id", "opencode_exit_code",
        "final_test_exit_code", "compile_exit_code", "tests_file_unchanged", "rollback_proven",
        "host_profile_write_count", "live_foxai_modified",
    ):
        if key in data:
            lines.append(f"{key}: {data[key]}")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, txt_path


def open_path(path: Path) -> None:
    if path.suffix == "":
        path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


def worker(name: str, func) -> None:
    try:
        set_state(busy=True, job=name, error=None)
        func()
    except Exception as exc:
        set_state(stage="NOT FIXED YET", message="The pilot stopped safely.",
                  error=f"{type(exc).__name__}: {exc}")
    finally:
        set_state(busy=False, job=None, installed=opencode_path().is_file())


HTML = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Forge — OpenCode Pilot</title><style>
:root{color-scheme:dark;--bg:#0e1015;--panel:#1b1d28;--line:#5b4979;--purple:#9b72e8;--green:#56e39a;--red:#ff8585;--text:#f7f2ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Segoe UI,Arial,sans-serif;font-size:21px}
main{max-width:1180px;margin:32px auto;padding:0 24px 50px}h1{font-size:46px;margin:0 0 8px}h2{font-size:30px;margin:0 0 18px}.sub{color:#d7c5ff}.panel{background:var(--panel);border:2px solid var(--line);border-radius:18px;padding:26px;margin:20px 0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
button{min-height:78px;border:0;border-radius:14px;padding:14px 20px;font-size:23px;font-weight:850;cursor:pointer;background:var(--purple);color:#111}button.secondary{background:#d7c8f4}button.stop{background:#dc8b8b}button:disabled{opacity:.45;cursor:not-allowed}.status{background:#0c0e13;border-radius:13px;padding:18px;font-weight:800;font-size:23px}.small{font-size:17px;color:#c9bfdc}.error{border-left:10px solid var(--red)}.success{border-left:10px solid var(--green)}pre{white-space:pre-wrap;word-break:break-word;background:#0b0c11;padding:18px;border-radius:12px;font:17px Consolas,monospace}@media(max-width:760px){.grid{grid-template-columns:1fr}h1{font-size:36px}}
</style></head><body><main><h1>Project Forge — OpenCode Pilot</h1><p class="sub">Native Windows coding agent + local Qwen3-Coder. No pip, no venv, and no live FOXAI edits.</p>
<div class="panel"><h2>One-click pilot</h2><div class="grid">
<button id="install" onclick="post('/api/install')">1. INSTALL NATIVE OPENCODE</button><button id="run" onclick="post('/api/run')">2. RUN REPAIR &amp; ROLLBACK PILOT</button>
<button class="secondary" onclick="post('/api/web')">OPEN OPENCODE WEB</button><button class="secondary" onclick="post('/api/open-workspace')">OPEN PILOT WORKSPACE</button>
<button class="secondary" onclick="post('/api/open-receipt')">OPEN LATEST RECEIPT</button><button class="stop" onclick="post('/api/stop')">STOP PILOT CONTROL PANEL</button></div></div>
<div class="panel" id="statePanel"><h2 id="stage">Ready</h2><div class="status" id="message">Loading status…</div><p class="small" id="details"></p><pre id="error" hidden></pre></div>
<div class="panel"><h2>What this proves</h2><p>OpenCode edits only a disposable Git project, uses the model currently served on port 8080, runs real tests, repairs failures, proves rollback, and records whether it wrote state outside the Project Forge folder.</p><p><strong>Live FOXAI is never selected or modified.</strong></p></div>
<script>async function post(u){try{let r=await fetch(u,{method:'POST'}),d=await r.json();if(!r.ok)throw new Error(d.error||('HTTP '+r.status))}catch(e){let x=document.getElementById('error');x.hidden=false;x.textContent=String(e)}await refresh()}
async function refresh(){try{let r=await fetch('/api/status',{cache:'no-store'}),s=await r.json();stage.textContent=s.stage;message.textContent=s.message;details.textContent='OpenCode installed: '+(s.installed?'YES':'NO')+(s.job?' • Active job: '+s.job:'');error.hidden=!s.error;error.textContent=s.error||'';install.disabled=s.busy;run.disabled=s.busy||!s.installed;statePanel.classList.toggle('error',!!s.error);statePanel.classList.toggle('success',s.stage==='PILOT PASSED')}catch(e){error.hidden=false;error.textContent='Control panel lost contact with its local server: '+e}}refresh();setInterval(refresh,1500)</script></main></body></html>'''


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            self.send_json(snapshot_state())
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/install":
            if snapshot_state()["busy"]:
                return self.send_json({"error": "A job is already running"}, 409)
            threading.Thread(target=worker, args=("install", install_opencode), daemon=True).start()
            return self.send_json({"started": True})
        if self.path == "/api/run":
            if snapshot_state()["busy"]:
                return self.send_json({"error": "A job is already running"}, 409)
            threading.Thread(target=worker, args=("pilot", run_pilot), daemon=True).start()
            return self.send_json({"started": True})
        if self.path == "/api/web":
            try:
                start_opencode_web()
                return self.send_json({"started": True})
            except Exception as exc:
                return self.send_json({"error": str(exc)}, 400)
        if self.path == "/api/open-workspace":
            try:
                latest = snapshot_state().get("latest_project")
                open_path(Path(latest) if latest else PROJECTS_DIR)
                return self.send_json({"opened": True})
            except Exception as exc:
                return self.send_json({"error": str(exc)}, 400)
        if self.path == "/api/open-receipt":
            try:
                latest = snapshot_state().get("latest_receipt")
                open_path(Path(latest) if latest else RECEIPTS_DIR)
                return self.send_json({"opened": True})
            except Exception as exc:
                return self.send_json({"error": str(exc)}, 400)
        if self.path == "/api/stop":
            self.send_json({"stopping": True})
            threading.Thread(target=lambda: (time.sleep(0.2), os._exit(0)), daemon=True).start()
            return
        self.send_json({"error": "not found"}, 404)


def main() -> int:
    host, port = "127.0.0.1", 8792
    try:
        server = http.server.ThreadingHTTPServer((host, port), Handler)
    except OSError as exc:
        print(f"Project Forge OpenCode Pilot could not start on {host}:{port}: {exc}")
        return 1
    threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}/")).start()
    print(f"Project Forge OpenCode Pilot: http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
