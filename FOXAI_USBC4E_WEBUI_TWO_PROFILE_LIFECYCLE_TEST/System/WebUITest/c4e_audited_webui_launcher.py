#!/usr/bin/env python3
"""Audited launcher for the C4E FOXAI WebUI lifecycle test.

Runs the installed WebUI in-process after installing a Python audit hook. The
hook allows only localhost sockets and exact invocations of the installed
ComfyUI lifecycle controller. It denies browser/shell/unknown subprocess starts
and all external socket activity. No WebUI source is modified.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
import runpy
import sys
import threading
from datetime import datetime, timezone
from typing import Any

_guard = threading.local()
_audit_path: Path | None = None
_root: Path | None = None
_webui_python: Path | None = None
_manager_python: Path | None = None
_manager: Path | None = None
_original_popen = subprocess.Popen


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return {"bytes": len(value)}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    return repr(value)


def record(event: str, args: Any, decision: str = "observed") -> None:
    if _audit_path is None or getattr(_guard, "active", False):
        return
    _guard.active = True
    try:
        row = {"utc": utc_now(), "event": event, "decision": decision, "args": jsonable(args)}
        payload = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        fd = os.open(str(_audit_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, payload)
        finally:
            os.close(fd)
    finally:
        _guard.active = False


def host_port(value: Any) -> tuple[str, int | None]:
    if isinstance(value, (tuple, list)) and value:
        host = str(value[0]).strip("[]").casefold()
        port = None
        if len(value) >= 2:
            try:
                port = int(value[1])
            except (TypeError, ValueError):
                port = None
        return host, port
    return str(value).strip("[]").casefold(), None


def normalized_path(value: Any) -> str:
    try:
        return str(Path(str(value)).resolve(strict=False)).replace("/", "\\").casefold()
    except Exception:
        return str(value).replace("/", "\\").casefold()


def command_from_popen_call(
    popenargs: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    if "args" in kwargs:
        return kwargs["args"]
    return popenargs[0] if popenargs else None


def manager_invocation_allowed(
    popenargs: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    """Validate the exact high-level Python Popen request.

    This uses the actual Python call before CPython converts a Windows argv
    sequence into a platform command-line string for the audit event.
    """
    if _root is None or _manager_python is None or _manager is None:
        return False, {"reason": "launcher not initialized"}

    command = command_from_popen_call(popenargs, kwargs)
    if isinstance(command, (list, tuple)):
        argv = [str(item) for item in command]
    else:
        argv = []

    details: dict[str, Any] = {
        "argv": argv,
        "cwd": str(kwargs.get("cwd")),
        "shell": bool(kwargs.get("shell", False)),
        "executable_override": str(kwargs.get("executable")),
        "creationflags": int(kwargs.get("creationflags", 0) or 0),
    }

    if not argv:
        details["reason"] = "command was not an argv sequence"
        return False, details
    if kwargs.get("shell", False):
        details["reason"] = "shell execution is forbidden"
        return False, details

    executable_override = kwargs.get("executable")
    if (
        executable_override is not None
        and normalized_path(executable_override) != normalized_path(_manager_python)
    ):
        details["reason"] = "unexpected executable override"
        return False, details

    cwd = kwargs.get("cwd")
    if cwd is None or normalized_path(cwd) != normalized_path(_root):
        details["reason"] = "unexpected working directory"
        return False, details

    expected_prefix = [
        str(_manager_python),
        "-I",
        "-B",
        "-S",
        str(_manager),
        "--root",
        str(_root),
        "--json",
    ]
    observed_prefix = [item.casefold() for item in argv[: len(expected_prefix)]]
    required_prefix = [item.casefold() for item in expected_prefix]
    if len(argv) < len(expected_prefix) or observed_prefix != required_prefix:
        details["reason"] = "unexpected controller prefix"
        return False, details

    tail = tuple(argv[len(expected_prefix) :])
    allowed_tails = {
        ("status",),
        ("stop",),
        ("spawn", "--source", "webui", "--profile", "safe-normal-cpu"),
        (
            "spawn",
            "--source",
            "webui",
            "--profile",
            "approved-custom-nodes-cpu",
        ),
    }
    details["tail"] = list(tail)
    if tail not in allowed_tails:
        details["reason"] = "unexpected controller action"
        return False, details

    return True, details


def guarded_popen(*popenargs: Any, **kwargs: Any) -> Any:
    allowed, details = manager_invocation_allowed(popenargs, kwargs)
    record(
        "c4e.guard.Popen",
        details,
        "allowed_exact_manager_command" if allowed else "denied",
    )
    if not allowed:
        raise RuntimeError("C4E denied a non-contract subprocess launch")

    previous = getattr(_guard, "authorized_popen", False)
    _guard.authorized_popen = True
    try:
        return _original_popen(*popenargs, **kwargs)
    finally:
        _guard.authorized_popen = previous


def audit_hook(event: str, args: tuple[Any, ...]) -> None:
    if getattr(_guard, "active", False):
        return

    if event == "subprocess.Popen":
        authorized = bool(getattr(_guard, "authorized_popen", False))
        details = {
            "authorized_by_high_level_guard": authorized,
            "raw_audit_args": jsonable(args),
        }
        record(
            event,
            details,
            "allowed_guarded_manager_command" if authorized else "denied",
        )
        if not authorized:
            raise RuntimeError("C4E denied an unguarded subprocess launch")
        return

    if event in {"os.system", "os.startfile", "os.spawn"}:
        record(event, args, "denied")
        raise RuntimeError(f"C4E denied process or shell event: {event}")

    if event == "socket.bind":
        address = args[1] if len(args) > 1 else None
        host, port = host_port(address)
        allowed = host in {"127.0.0.1", "localhost", "::1"} and port in {0, 8765}
        if port == 8765:
            decision = "allowed_webui_listener"
        elif port == 0 and host in {"127.0.0.1", "localhost", "::1"}:
            decision = "allowed_local_ephemeral"
        else:
            decision = "denied"
        record(event, address, decision)
        if not allowed:
            raise RuntimeError(f"C4E denied non-contract WebUI socket bind: {address!r}")
        return

    if event in {"socket.connect", "socket.connect_ex"}:
        address = args[1] if len(args) > 1 else None
        host, port = host_port(address)
        allowed = host in {"127.0.0.1", "localhost", "::1"} and port in {8080, 8188, 8765}
        record(event, address, "allowed_loopback" if allowed else "denied")
        if not allowed:
            raise RuntimeError(f"C4E denied external or unknown socket connection: {address!r}")
        return

    if event == "open" and len(args) >= 2:
        mode = str(args[1])
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            record(event, {"path": str(args[0]), "mode": mode}, "observed_write_open")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve(strict=True)
    audit = Path(args.audit).resolve(strict=False)
    audit.parent.mkdir(parents=True, exist_ok=True)
    webui_python = (root / "env/python/python.exe").resolve(strict=True)
    manager_python = (root / "Runtime/Desktop/python/python.exe").resolve(strict=True)
    manager = (root / "System/PortableRuntime/manage_comfyui_normal.py").resolve(strict=True)
    webui = (root / "core/foxai_web.py").resolve(strict=True)

    if Path(sys.executable).resolve(strict=True) != webui_python:
        raise RuntimeError("C4E WebUI audit wrapper requires the exact USB WebUI Python runtime")

    global _audit_path, _root, _webui_python, _manager_python, _manager
    _audit_path = audit
    _root = root
    _webui_python = webui_python
    _manager_python = manager_python
    _manager = manager

    record("c4e.wrapper.start", {"root": str(root), "webui": str(webui)}, "observed")
    sys.addaudithook(audit_hook)

    # subprocess.run() resolves Popen from the subprocess module at call time.
    # Replacing it here exposes the original structured argv before Windows
    # converts it into the platform audit-event representation.
    subprocess.Popen = guarded_popen  # type: ignore[assignment]

    sys.argv = [str(webui)]
    runpy.run_path(str(webui), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
