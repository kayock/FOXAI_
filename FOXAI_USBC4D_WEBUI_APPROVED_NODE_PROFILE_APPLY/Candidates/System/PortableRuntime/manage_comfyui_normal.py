#!/usr/bin/env python3
"""FOXAI ComfyUI dual-profile CPU lifecycle controller.

Safe Normal CPU remains the default. Approved Custom Nodes CPU is explicit-only
and hash-locks every approved node before process creation and after health.
Both profiles use portable Python, the isolated runtime, and localhost port 8188.
Unknown profiles, changed approved nodes, mixed-profile starts, and unknown port
owners fail closed. No automatic force-kill or log deletion is permitted.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import site
import subprocess
import sys
import time
from typing import Any
import urllib.error
import urllib.request
import webbrowser

POLICY_ID = "FOXAI_COMFYUI_DUAL_CPU_PROFILE_V1"
DEFAULT_PROFILE_ID = "safe-normal-cpu"
APPROVED_PROFILE_ID = "approved-custom-nodes-cpu"
MANAGER_VERSION = "1.1.0"
HEALTH_URLS = (
    "http://127.0.0.1:8188/",
    "http://127.0.0.1:8188/system_stats",
)


class LifecycleError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def utc_run_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    temporary.write_bytes(json_bytes(value))
    os.replace(temporary, path)


def resolve_root(raw: str) -> Path:
    root = Path(raw).resolve(strict=True)
    if not root.is_dir():
        raise LifecycleError("FOXAI root is not a directory")
    return root


def runtime_paths(root: Path) -> dict[str, Path]:
    return {
        "python": root / "Runtime/Desktop/python/python.exe",
        "target": root / "Runtime/ComfyUI/site-packages",
        "activator": root / "System/PortableRuntime/launch_comfyui_isolated.py",
        "manager": root / "System/PortableRuntime/manage_comfyui_normal.py",
        "policy": root / "System/PortableRuntime/COMFYUI_NORMAL_POLICY.json",
        "comfy": root / "ComfyUI",
        "main": root / "ComfyUI/main.py",
        "approved_node": root / "ComfyUI/custom_nodes/websocket_image_save.py",
        "state_dir": root / "Runtime/ComfyUI/state",
        "state": root / "Runtime/ComfyUI/state/normal_instance.json",
        "history": root / "Runtime/ComfyUI/state/history",
        "logs": root / "Runtime/ComfyUI/logs/normal",
    }


def verify_runtime(root: Path) -> dict[str, Path]:
    paths = runtime_paths(root)
    required_files = ("python", "activator", "manager", "policy", "main")
    for key in required_files:
        path = paths[key]
        if not path.is_file() or path.is_symlink():
            raise LifecycleError(f"Required normal lifecycle file is missing or unsafe: {path}")
    if not paths["target"].is_dir() or paths["target"].is_symlink():
        raise LifecycleError("Committed isolated ComfyUI target is missing or unsafe")
    if not (paths["target"] / "torch/__init__.py").is_file():
        raise LifecycleError("Committed isolated target does not contain torch")
    if Path(sys.executable).resolve(strict=True) != paths["python"].resolve(strict=True):
        raise LifecycleError("Normal controller requires the USB-owned portable Python")
    policy = read_json(paths["policy"])
    if not policy or policy.get("policy_id") != POLICY_ID:
        raise LifecycleError("Normal lifecycle policy is missing or has an unexpected identity")
    if policy.get("default_profile_id") != DEFAULT_PROFILE_ID:
        raise LifecycleError("Normal lifecycle policy changed the safe default profile")
    profiles = policy.get("profiles")
    if not isinstance(profiles, list) or {str(item.get("id")) for item in profiles if isinstance(item, dict)} != {DEFAULT_PROFILE_ID, APPROVED_PROFILE_ID}:
        raise LifecycleError("Normal lifecycle policy does not contain the exact two approved profiles")
    return paths


def profile_definition(paths: dict[str, Path], profile_id: str | None) -> dict[str, Any]:
    selected = str(profile_id or DEFAULT_PROFILE_ID).strip()
    policy = read_json(paths["policy"])
    if not policy or policy.get("policy_id") != POLICY_ID:
        raise LifecycleError("Normal lifecycle policy is missing or changed")
    profiles = policy.get("profiles")
    if not isinstance(profiles, list):
        raise LifecycleError("Normal lifecycle policy profiles are invalid")
    matches = [item for item in profiles if isinstance(item, dict) and str(item.get("id")) == selected]
    if len(matches) != 1:
        raise LifecycleError(f"Unknown ComfyUI profile: {selected}")
    profile = dict(matches[0])
    arguments = profile.get("arguments")
    if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments):
        raise LifecycleError(f"ComfyUI profile arguments are invalid: {selected}")
    required_tail = ["--listen", "127.0.0.1", "--port", "8188"]
    if arguments[-4:] != required_tail or "--cpu" not in arguments or "--disable-all-custom-nodes" not in arguments:
        raise LifecycleError(f"ComfyUI profile escaped the approved CPU/localhost contract: {selected}")
    if selected == DEFAULT_PROFILE_ID and "--whitelist-custom-nodes" in arguments:
        raise LifecycleError("Safe Normal CPU unexpectedly enables a custom node")
    if selected == APPROVED_PROFILE_ID:
        expected = ["--cpu", "--disable-all-custom-nodes", "--whitelist-custom-nodes", "websocket_image_save.py", "--listen", "127.0.0.1", "--port", "8188"]
        if arguments != expected:
            raise LifecycleError("Approved Custom Nodes CPU arguments changed")
    return profile


def verify_profile_nodes(root: Path, paths: dict[str, Path], profile: dict[str, Any]) -> dict[str, Any]:
    profile_id = str(profile.get("id") or "")
    approved = profile.get("approved_nodes") or []
    if profile_id == DEFAULT_PROFILE_ID:
        if approved:
            raise LifecycleError("Safe Normal CPU contains an unexpected approved-node list")
        return {"verified": True, "state": "NOT_APPLICABLE", "nodes": []}
    if profile_id != APPROVED_PROFILE_ID or not isinstance(approved, list) or len(approved) != 1:
        raise LifecycleError("Approved custom-node profile definition changed")
    record = approved[0]
    expected_relative = "ComfyUI/custom_nodes/websocket_image_save.py"
    expected_digest = "0b66b69eb7dab007d55bf63c5bd0f1343dcfbc2f5a350983f906ba2cd3dd5d23"
    if not isinstance(record, dict) or str(record.get("relative_path")) != expected_relative or str(record.get("sha256")) != expected_digest:
        raise LifecycleError("Approved custom-node identity changed")
    node = root / Path(expected_relative)
    if not node.is_file() or node.is_symlink():
        raise LifecycleError("Approved custom node is missing or unsafe")
    actual_size = node.stat().st_size
    actual_digest = hashlib.sha256(node.read_bytes()).hexdigest()
    if actual_size != 1348 or actual_digest != expected_digest:
        raise LifecycleError("Approved custom node changed; startup refused")
    return {
        "verified": True,
        "state": "VERIFIED",
        "nodes": [{
            "relative_path": expected_relative,
            "filename": "websocket_image_save.py",
            "display_name": "Save Image (Websocket)",
            "class_key": "SaveImageWebsocket",
            "size_bytes": actual_size,
            "sha256": actual_digest,
        }],
    }


def activate_psutil(paths: dict[str, Path]):
    for key in ("PYTHONHOME", "PYTHONPATH"):
        os.environ.pop(key, None)
    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    site.addsitedir(str(paths["target"]))
    import psutil  # type: ignore
    return psutil


def process_record(psutil, pid: int) -> dict[str, Any] | None:
    try:
        proc = psutil.Process(int(pid))
        return {
            "pid": proc.pid,
            "create_time": float(proc.create_time()),
            "exe": str(Path(proc.exe()).resolve(strict=False)),
            "cmdline": [str(item) for item in proc.cmdline()],
            "status": proc.status(),
            "running": proc.is_running(),
        }
    except Exception:
        return None


def same_creation(actual: float | None, expected: Any) -> bool:
    try:
        return abs(float(actual) - float(expected)) < 0.01
    except (TypeError, ValueError):
        return False


def command_fingerprint(root: Path, command: list[str], profile_id: str, node_verification: dict[str, Any]) -> str:
    payload = {
        "policy_id": POLICY_ID,
        "profile_id": profile_id,
        "root": str(root.resolve(strict=False)).casefold(),
        "command": [str(item).casefold() for item in command],
        "approved_nodes": [
            {"relative_path": item.get("relative_path"), "sha256": item.get("sha256")}
            for item in node_verification.get("nodes", [])
        ],
    }
    return sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))


def expected_child_command(root: Path, paths: dict[str, Path], profile_id: str = DEFAULT_PROFILE_ID) -> list[str]:
    profile = profile_definition(paths, profile_id)
    return [
        str(paths["python"]),
        "-I", "-B", "-S",
        str(paths["activator"]),
        "--root", str(root),
        "--",
        *[str(item) for item in profile["arguments"]],
    ]


def health_request(url: str, timeout: float = 2.0) -> dict[str, Any]:
    started = time.monotonic()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "FOXAI-C3J-Normal/1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(4096)
            return {
                "ok": int(response.status) == 200,
                "status": int(response.status),
                "bytes": len(body),
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "error": None,
            }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "bytes": 0,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }


def health_snapshot() -> dict[str, Any]:
    rows = [{"url": url, **health_request(url)} for url in HEALTH_URLS]
    return {"ok": all(row["ok"] for row in rows), "checks": rows, "observed": utc_now()}


def listeners_on_8188(psutil) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        connections = psutil.net_connections(kind="tcp")
    except Exception as exc:
        return [{"error": f"{type(exc).__name__}: {exc}"}]
    for item in connections:
        local = getattr(item, "laddr", None)
        if not local:
            continue
        port = getattr(local, "port", local[1] if len(local) > 1 else None)
        if int(port or 0) != 8188:
            continue
        ip = getattr(local, "ip", local[0] if len(local) > 0 else "")
        status = str(getattr(item, "status", ""))
        if status.upper() != "LISTEN":
            continue
        rows.append({"ip": str(ip), "port": 8188, "pid": getattr(item, "pid", None), "status": status})
    return rows


def load_state(paths: dict[str, Path]) -> dict[str, Any] | None:
    return read_json(paths["state"])


def archive_state(paths: dict[str, Path], state: dict[str, Any], reason: str) -> Path:
    paths["history"].mkdir(parents=True, exist_ok=True)
    run_id = str(state.get("run_id") or utc_run_id())
    destination = paths["history"] / f"normal_instance_{run_id}_{reason}.json"
    counter = 1
    while destination.exists():
        destination = paths["history"] / f"normal_instance_{run_id}_{reason}_{counter}.json"
        counter += 1
    atomic_json(destination, state)
    with contextlib.suppress(FileNotFoundError):
        paths["state"].unlink()
    return destination


def verify_owned_state(root: Path, paths: dict[str, Path], psutil, state: dict[str, Any]) -> dict[str, Any]:
    profile_id = str(state.get("profile_id") or DEFAULT_PROFILE_ID)
    profile = profile_definition(paths, profile_id)
    fingerprint_nodes = {"nodes": state.get("approved_nodes") or []}
    try:
        node_verification = verify_profile_nodes(root, paths, profile)
    except LifecycleError as exc:
        node_verification = {
            "verified": False,
            "state": "MISMATCH",
            "nodes": state.get("approved_nodes") or [],
            "error": str(exc),
        }
    command = expected_child_command(root, paths, profile_id)
    expected_fingerprint = command_fingerprint(root, command, profile_id, fingerprint_nodes)
    child = process_record(psutil, int(state.get("child_pid") or 0))
    supervisor = process_record(psutil, int(state.get("supervisor_pid") or 0))
    listeners = listeners_on_8188(psutil)
    listener_pids = {int(row["pid"]) for row in listeners if row.get("pid") is not None}
    portable = str(paths["python"].resolve(strict=False)).casefold()
    child_owned = bool(
        child
        and child.get("running")
        and same_creation(child.get("create_time"), state.get("child_create_time"))
        and str(child.get("exe") or "").casefold() == portable
        and state.get("command_fingerprint") == expected_fingerprint
        and int(child.get("pid") or 0) in listener_pids
    )
    supervisor_owned = bool(
        supervisor
        and supervisor.get("running")
        and same_creation(supervisor.get("create_time"), state.get("supervisor_create_time"))
        and str(supervisor.get("exe") or "").casefold() == portable
    )
    loopback_only = bool(listeners) and all(row.get("ip") in {"127.0.0.1", "::1"} for row in listeners if "ip" in row)
    health = health_snapshot() if listeners else {"ok": False, "checks": [], "observed": utc_now()}
    return {
        "child": child,
        "supervisor": supervisor,
        "listeners": listeners,
        "child_owned": child_owned,
        "supervisor_owned": supervisor_owned,
        "loopback_only": loopback_only,
        "health": health,
        "profile_id": profile_id,
        "profile_name": str(profile.get("display_name") or profile_id),
        "approved_node_hash_state": node_verification.get("state"),
        "approved_nodes": node_verification.get("nodes", []),
        "expected_command_fingerprint": expected_fingerprint,
        "owned_healthy": child_owned and supervisor_owned and loopback_only and health.get("ok") is True and node_verification.get("verified") is True,
    }


def status_result(root: Path, paths: dict[str, Path], psutil) -> dict[str, Any]:
    state = load_state(paths)
    listeners = listeners_on_8188(psutil)
    if state is None:
        return {
            "ok": not listeners,
            "state": "STOPPED" if not listeners else "CONFLICT",
            "message": "No controller state exists." if not listeners else "Port 8188 is owned by an unknown process.",
            "managed": False,
            "listeners": listeners,
            "health": health_snapshot() if listeners else {"ok": False, "checks": []},
            "active_profile_id": None,
            "active_profile_name": None,
            "default_profile_id": DEFAULT_PROFILE_ID,
            "approved_node_hash_state": "NOT_RUNNING",
        }
    verification = verify_owned_state(root, paths, psutil, state)
    recorded = str(state.get("status") or "UNKNOWN").upper()
    if verification["owned_healthy"]:
        effective = "HEALTHY"
        message = "Verified controller-owned ComfyUI instance is healthy."
        ok = True
    elif (
        verification["child_owned"] and verification["supervisor_owned"]
        and verification["loopback_only"] and verification["health"].get("ok") is True
        and verification.get("approved_node_hash_state") == "MISMATCH"
    ):
        effective = "NODE_HASH_MISMATCH"
        message = "The controller-owned instance is healthy, but the approved node file changed after launch. Stop remains available; new starts are refused."
        ok = False
    elif verification["child"] or verification["supervisor"] or verification["listeners"]:
        if verification["child_owned"] or verification["supervisor_owned"]:
            effective = recorded if recorded in {"STARTING", "STOPPING"} else "CONFLICT"
            message = "A partially matching controller instance exists but ownership, profile, node hash, and health checks do not all agree."
        else:
            effective = "CONFLICT"
            message = "Recorded state conflicts with the live process or port owner."
        ok = False
    else:
        effective = "STOPPED" if recorded == "STOPPED" else "STALE"
        message = "The recorded controller instance is not running."
        ok = effective == "STOPPED"
    return {
        "ok": ok,
        "state": effective,
        "message": message,
        "managed": bool(verification["child_owned"] or verification["supervisor_owned"]),
        "active_profile_id": verification.get("profile_id"),
        "active_profile_name": verification.get("profile_name"),
        "default_profile_id": DEFAULT_PROFILE_ID,
        "approved_node_hash_state": verification.get("approved_node_hash_state"),
        "approved_nodes": verification.get("approved_nodes", []),
        "recorded_state": state,
        "verification": verification,
    }


def retention_observation(paths: dict[str, Path]) -> dict[str, Any]:
    base = paths["logs"]
    run_count = 0
    total_bytes = 0
    if base.is_dir():
        for entry in base.iterdir():
            if entry.is_dir() and not entry.is_symlink():
                run_count += 1
        for file in base.rglob("*"):
            if file.is_file() and not file.is_symlink():
                with contextlib.suppress(OSError):
                    total_bytes += file.stat().st_size
    return {
        "run_count": run_count,
        "total_bytes": total_bytes,
        "warning": run_count >= 100 or total_bytes >= 1073741824,
        "automatic_deletion": False,
    }


def child_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(key, None)
    env.update({
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "SETUPTOOLS_USE_DISTUTILS": "local",
    })
    return env


def request_graceful_stop(child: subprocess.Popen[Any], log_dir: Path, reason: str) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "requested": utc_now(),
        "reason": reason,
        "pid": child.pid,
        "method": "CTRL_BREAK_EVENT",
        "force_kill": False,
    }
    try:
        if os.name == "nt":
            os.kill(child.pid, signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        else:
            child.send_signal(signal.SIGINT)
        receipt["signal_sent"] = True
    except Exception as exc:
        receipt["signal_sent"] = False
        receipt["signal_error"] = f"{type(exc).__name__}: {exc}"
        atomic_json(log_dir / "stop_receipt.json", receipt)
        return receipt
    try:
        receipt["returncode"] = child.wait(timeout=15)
        receipt["stopped"] = True
    except subprocess.TimeoutExpired:
        receipt["stopped"] = False
        receipt["timeout_seconds"] = 15
        receipt["message"] = "Graceful stop timed out. Force-kill was not performed."
    atomic_json(log_dir / "stop_receipt.json", receipt)
    return receipt


def run_supervisor(root: Path, paths: dict[str, Path], psutil, open_browser: bool, source: str, profile_id: str) -> int:
    profile = profile_definition(paths, profile_id)
    node_verification = verify_profile_nodes(root, paths, profile)
    current = status_result(root, paths, psutil)
    if current["state"] == "HEALTHY":
        if current.get("active_profile_id") == profile_id:
            print(json.dumps({"ok": True, "state": "HEALTHY", "message": "ComfyUI is already running with the requested profile.", "active_profile_id": profile_id, "active_profile_name": profile.get("display_name")}))
            return 0
        raise LifecycleError(f"Profile switch refused while {current.get('active_profile_name') or current.get('active_profile_id')} is healthy. Stop ComfyUI first.")
    if current["state"] in {"CONFLICT", "STARTING", "STOPPING", "STALE", "NODE_HASH_MISMATCH"}:
        raise LifecycleError(f"Normal start refused: {current['state']} - {current['message']}")
    old_state = load_state(paths)
    if old_state:
        archive_state(paths, old_state, "completed")

    run_id = utc_run_id()
    log_dir = paths["logs"] / run_id
    log_dir.mkdir(parents=True, exist_ok=False)
    paths["state_dir"].mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    command = expected_child_command(root, paths, profile_id)
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    started = utc_now()
    with stdout_path.open("ab", buffering=0) as stdout_handle, stderr_path.open("ab", buffering=0) as stderr_handle:
        child = subprocess.Popen(
            command,
            cwd=str(paths["comfy"]),
            env=child_environment(),
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        child_info = None
        for _ in range(50):
            child_info = process_record(psutil, child.pid)
            if child_info:
                break
            time.sleep(0.1)
        supervisor_info = process_record(psutil, os.getpid())
        state = {
            "schema": 1,
            "policy_id": POLICY_ID,
            "manager_version": MANAGER_VERSION,
            "profile_id": profile_id,
            "profile_name": str(profile.get("display_name") or profile_id),
            "approved_node_hash_state": node_verification.get("state"),
            "approved_nodes": node_verification.get("nodes", []),
            "run_id": run_id,
            "status": "STARTING",
            "source": source,
            "root": str(root),
            "portable_python": str(paths["python"]),
            "supervisor_pid": os.getpid(),
            "supervisor_create_time": (supervisor_info or {}).get("create_time"),
            "child_pid": child.pid,
            "child_create_time": (child_info or {}).get("create_time"),
            "command": command,
            "command_fingerprint": command_fingerprint(root, command, profile_id, node_verification),
            "listen": "127.0.0.1",
            "port": 8188,
            "custom_nodes_disabled": True,
            "started": started,
            "log_dir": str(log_dir),
            "stop_request": str(log_dir / "stop.request.json"),
            "retention": retention_observation(paths),
        }
        atomic_json(paths["state"], state)
        atomic_json(log_dir / "start_receipt.json", state)

        deadline = time.monotonic() + 300
        consecutive = 0
        health_rows: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            returncode = child.poll()
            if returncode is not None:
                state.update({"status": "FAILED", "returncode": returncode, "completed": utc_now()})
                atomic_json(paths["state"], state)
                raise LifecycleError(f"ComfyUI exited during startup with code {returncode}")
            snapshot = verify_owned_state(root, paths, psutil, state)
            health_rows.append({"observed": utc_now(), "owned_healthy": snapshot["owned_healthy"], "health": snapshot["health"], "approved_node_hash_state": snapshot.get("approved_node_hash_state")})
            if snapshot.get("approved_node_hash_state") == "MISMATCH":
                stop_receipt = request_graceful_stop(child, log_dir, "approved_node_changed_during_startup")
                state.update({"status": "FAILED_NODE_HASH_CHANGED", "completed": utc_now(), "stop_receipt": stop_receipt})
                atomic_json(paths["state"], state)
                atomic_json(log_dir / "health_receipt.json", {"verified": False, "checks": health_rows})
                raise LifecycleError("Approved custom node changed during startup; process was stopped")
            if snapshot["owned_healthy"]:
                consecutive += 1
                if consecutive >= 3:
                    break
            else:
                consecutive = 0
            time.sleep(1)
        if consecutive < 3:
            stop_receipt = request_graceful_stop(child, log_dir, "startup_timeout")
            state.update({"status": "FAILED_STARTUP_TIMEOUT", "completed": utc_now(), "stop_receipt": stop_receipt})
            atomic_json(paths["state"], state)
            atomic_json(log_dir / "health_receipt.json", {"verified": False, "checks": health_rows})
            raise LifecycleError("ComfyUI did not become a verified owned localhost service within 300 seconds")

        try:
            post_health_nodes = verify_profile_nodes(root, paths, profile)
        except LifecycleError as exc:
            stop_receipt = request_graceful_stop(child, log_dir, "approved_node_changed_after_health")
            state.update({"status": "FAILED_NODE_HASH_CHANGED", "completed": utc_now(), "stop_receipt": stop_receipt})
            atomic_json(paths["state"], state)
            raise LifecycleError(f"Approved custom node changed after health; process was stopped: {exc}")
        if post_health_nodes != node_verification:
            stop_receipt = request_graceful_stop(child, log_dir, "approved_node_changed_after_health")
            state.update({"status": "FAILED_NODE_HASH_CHANGED", "completed": utc_now(), "stop_receipt": stop_receipt})
            atomic_json(paths["state"], state)
            raise LifecycleError("Approved custom node changed during startup; process was stopped")
        state.update({"status": "HEALTHY", "healthy": utc_now(), "approved_node_hash_state": post_health_nodes.get("state"), "approved_nodes": post_health_nodes.get("nodes", [])})
        atomic_json(paths["state"], state)
        atomic_json(log_dir / "health_receipt.json", {"verified": True, "consecutive": consecutive, "checks": health_rows})
        print("[HEALTHY] ComfyUI is verified at http://127.0.0.1:8188")
        if open_browser:
            webbrowser.open("http://127.0.0.1:8188", new=2)

        stop_request = Path(state["stop_request"])
        try:
            while child.poll() is None:
                if stop_request.is_file():
                    request = read_json(stop_request) or {}
                    state.update({"status": "STOPPING", "stop_requested": utc_now(), "stop_request_details": request})
                    atomic_json(paths["state"], state)
                    receipt = request_graceful_stop(child, log_dir, str(request.get("reason") or "controller_stop"))
                    if receipt.get("stopped"):
                        break
                    state.update({"status": "STOPPING_TIMEOUT", "stop_receipt": receipt})
                    atomic_json(paths["state"], state)
                    print("[STOPPING TIMEOUT] ComfyUI remains running; no force-kill was performed.")
                    return 12
                time.sleep(0.5)
        except KeyboardInterrupt:
            receipt = request_graceful_stop(child, log_dir, "controller_keyboard_interrupt")
            if not receipt.get("stopped"):
                state.update({"status": "STOPPING_TIMEOUT", "stop_receipt": receipt})
                atomic_json(paths["state"], state)
                return 12

        returncode = child.poll()
        if returncode is None:
            returncode = child.wait()
        state.update({"status": "STOPPED", "returncode": returncode, "completed": utc_now()})
        atomic_json(paths["state"], state)
        if not (log_dir / "stop_receipt.json").exists():
            atomic_json(log_dir / "stop_receipt.json", {
                "stopped": True,
                "reason": "process_exit",
                "returncode": returncode,
                "completed": utc_now(),
                "force_kill": False,
            })
        print(f"[STOPPED] ComfyUI exited with code {returncode}.")
        return 0


def spawn_supervisor(root: Path, paths: dict[str, Path], psutil, source: str, profile_id: str) -> dict[str, Any]:
    profile = profile_definition(paths, profile_id)
    verify_profile_nodes(root, paths, profile)
    current = status_result(root, paths, psutil)
    if current["state"] == "HEALTHY":
        if current.get("active_profile_id") == profile_id:
            return {"ok": True, "state": "HEALTHY", "message": "ComfyUI is already running with the requested profile.", "status": current}
        return {"ok": False, "state": "PROFILE_CONFLICT", "message": f"{current.get('active_profile_name') or current.get('active_profile_id')} is already healthy. Stop ComfyUI before switching profiles.", "status": current}
    if current["state"] in {"CONFLICT", "STARTING", "STOPPING", "STALE", "NODE_HASH_MISMATCH"}:
        return {"ok": False, "state": current["state"], "message": current["message"], "status": current}
    command = [
        str(paths["python"]), "-I", "-B", "-S", str(paths["manager"]),
        "--root", str(root), "start", "--no-browser", "--source", source, "--profile", profile_id,
    ]
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
    supervisor = subprocess.Popen(command, cwd=str(root), env=child_environment(), creationflags=creationflags)
    deadline = time.monotonic() + 300
    last = current
    while time.monotonic() < deadline:
        time.sleep(1)
        last = status_result(root, paths, psutil)
        if last["state"] == "HEALTHY" and last.get("active_profile_id") == profile_id:
            return {
                "ok": True,
                "state": "HEALTHY",
                "message": "ComfyUI started and passed controller ownership, profile, node-hash, and health checks.",
                "supervisor_pid": supervisor.pid,
                "active_profile_id": profile_id,
                "active_profile_name": profile.get("display_name"),
                "approved_node_hash_state": last.get("approved_node_hash_state"),
                "status": last,
            }
        if supervisor.poll() is not None and last["state"] != "HEALTHY":
            return {
                "ok": False,
                "state": last["state"],
                "message": f"Normal supervisor exited before health verification with code {supervisor.returncode}.",
                "status": last,
            }
    return {"ok": False, "state": "STARTUP_TIMEOUT", "message": "Timed out waiting for normal controller health.", "status": last}


def stop_managed(root: Path, paths: dict[str, Path], psutil) -> dict[str, Any]:
    status = status_result(root, paths, psutil)
    if status["state"] == "STOPPED":
        return {"ok": True, "state": "STOPPED", "message": "ComfyUI is already stopped.", "status": status}
    if status["state"] == "STALE":
        state = load_state(paths)
        if state:
            archived = archive_state(paths, state, "stale_cleared_by_stop")
            return {"ok": True, "state": "STOPPED", "message": "Stale state was preserved and cleared.", "archived_state": str(archived)}
        return {"ok": True, "state": "STOPPED", "message": "No active state remains."}
    if status["state"] == "CONFLICT" or not status.get("managed"):
        return {"ok": False, "state": "CONFLICT", "message": "Stop refused because ownership could not be proved.", "status": status}
    state = load_state(paths)
    if not state:
        return {"ok": False, "state": "CONFLICT", "message": "Managed state disappeared before stop request."}
    request_path = Path(str(state.get("stop_request") or ""))
    if not request_path:
        return {"ok": False, "state": "CONFLICT", "message": "Managed state does not contain a stop-request path."}
    try:
        request_path.resolve(strict=False).relative_to(paths["logs"].resolve(strict=False))
    except ValueError:
        return {"ok": False, "state": "CONFLICT", "message": "Stop-request path escaped the normal log boundary."}
    atomic_json(request_path, {"requested": utc_now(), "reason": "operator_stop", "requester_pid": os.getpid()})
    deadline = time.monotonic() + 20
    last = status
    while time.monotonic() < deadline:
        time.sleep(0.5)
        last = status_result(root, paths, psutil)
        if last["state"] in {"STOPPED", "STALE"} and not listeners_on_8188(psutil):
            return {"ok": True, "state": "STOPPED", "message": "Controller-owned ComfyUI stopped.", "status": last}
    return {"ok": False, "state": "STOPPING_TIMEOUT", "message": "Graceful stop did not complete. No force-kill was performed.", "status": last}


def emit(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, separators=(",", ":"), default=str))
    else:
        print(f"[{value.get('state', 'INFO')}] {value.get('message', '')}")
        if value.get("status"):
            print(json.dumps(value["status"], indent=2, default=str))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FOXAI ComfyUI normal lifecycle controller")
    parser.add_argument("--root", required=True)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="action", required=True)
    start = sub.add_parser("start")
    start.add_argument("--no-browser", action="store_true")
    start.add_argument("--source", default="direct", choices=("direct", "workshop", "webui", "test"))
    start.add_argument("--profile", default=DEFAULT_PROFILE_ID)
    spawn = sub.add_parser("spawn")
    spawn.add_argument("--source", default="webui", choices=("direct", "workshop", "webui", "test"))
    spawn.add_argument("--profile", default=DEFAULT_PROFILE_ID)
    sub.add_parser("status")
    sub.add_parser("stop")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        root = resolve_root(args.root)
        paths = verify_runtime(root)
        psutil = activate_psutil(paths)
        if args.action == "status":
            result = status_result(root, paths, psutil)
            emit(result, args.json)
            return 0 if result["state"] in {"HEALTHY", "STOPPED"} else 10
        if args.action == "stop":
            result = stop_managed(root, paths, psutil)
            emit(result, args.json)
            return 0 if result.get("ok") else 11
        if args.action == "spawn":
            result = spawn_supervisor(root, paths, psutil, args.source, args.profile)
            emit(result, args.json)
            return 0 if result.get("ok") else 12
        return run_supervisor(root, paths, psutil, not args.no_browser, args.source, args.profile)
    except LifecycleError as exc:
        emit({"ok": False, "state": "BLOCKED", "message": str(exc)}, getattr(args, "json", False))
        return 19
    except Exception as exc:
        emit({"ok": False, "state": "ERROR", "message": f"{type(exc).__name__}: {exc}"}, getattr(args, "json", False))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
