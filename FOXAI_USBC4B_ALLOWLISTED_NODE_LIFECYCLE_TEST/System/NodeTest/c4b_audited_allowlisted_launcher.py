#!/usr/bin/env python3
"""Audited C4B wrapper around the sealed isolated ComfyUI activator.

Allows only loopback socket activity and the reviewed ComfyUI listener. Denies
subprocess/shell/OS-start activity inside the launched process. Records custom
node execution and write-oriented file opens for review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_guard = threading.local()
_audit_path: Path | None = None
_root: Path | None = None


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return {"bytes": len(value)}
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return repr(value)


def _record(event: str, args: Any, decision: str = "observed") -> None:
    global _audit_path
    if _audit_path is None or getattr(_guard, "active", False):
        return
    _guard.active = True
    try:
        row = {
            "utc": _utc(),
            "event": event,
            "decision": decision,
            "args": _jsonable(args),
        }
        data = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        fd = os.open(str(_audit_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
    finally:
        _guard.active = False


def _host(value: Any) -> str:
    if isinstance(value, (tuple, list)) and value:
        return str(value[0]).strip("[]").casefold()
    return str(value).strip("[]").casefold()


def _port(value: Any) -> int | None:
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        try:
            return int(value[1])
        except (TypeError, ValueError):
            return None
    return None


def audit_hook(event: str, args: tuple[Any, ...]) -> None:
    if getattr(_guard, "active", False):
        return

    if event in {"subprocess.Popen", "os.system", "os.startfile", "os.spawn"}:
        _record(event, args, "denied")
        raise RuntimeError(f"C4B denied process-launch audit event: {event}")

    if event == "socket.bind":
        address = args[1] if len(args) > 1 else None
        host, port = _host(address), _port(address)
        listener_allowed = host in {"127.0.0.1", "localhost"} and port == 8188
        event_loop_self_pipe = host in {"127.0.0.1", "localhost", "::1"} and port == 0
        allowed = listener_allowed or event_loop_self_pipe
        if listener_allowed:
            decision = "allowed_contract_listener"
        elif event_loop_self_pipe:
            decision = "allowed_event_loop_self_pipe"
        else:
            decision = "denied"
        _record(event, address, decision)
        if not allowed:
            raise RuntimeError(f"C4B denied non-contract socket bind: {address!r}")
        return

    if event in {"socket.connect", "socket.connect_ex"}:
        address = args[1] if len(args) > 1 else None
        host = _host(address)
        allowed = host in {"127.0.0.1", "localhost", "::1"}
        _record(event, address, "allowed" if allowed else "denied")
        if not allowed:
            raise RuntimeError(f"C4B denied external socket connection: {address!r}")
        return

    if event == "exec" and args:
        code = args[0]
        filename = getattr(code, "co_filename", "")
        if "custom_nodes" in str(filename).replace("\\", "/").casefold():
            _record(event, {"filename": filename}, "observed_custom_node_execution")
        return

    if event == "open" and len(args) >= 2:
        path, mode = args[0], args[1]
        mode_text = str(mode)
        if any(flag in mode_text for flag in ("w", "a", "x", "+")):
            _record(event, {"path": str(path), "mode": mode_text}, "observed_write_open")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("remainder", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    root = Path(args.root).resolve(strict=True)
    audit = Path(args.audit).resolve(strict=False)
    audit.parent.mkdir(parents=True, exist_ok=True)

    global _audit_path, _root
    _audit_path = audit
    _root = root
    _record("c4b.wrapper.start", {"root": str(root)}, "observed")
    sys.addaudithook(audit_hook)

    remainder = list(args.remainder)
    if remainder and remainder[0] == "--":
        remainder = remainder[1:]

    expected = [
        "--cpu",
        "--disable-all-custom-nodes",
        "--whitelist-custom-nodes",
        "websocket_image_save.py",
        "--listen",
        "127.0.0.1",
        "--port",
        "8188",
    ]
    if remainder != expected:
        _record("c4b.wrapper.arguments", {"received": remainder}, "denied")
        raise RuntimeError("C4B launch arguments do not match the exact approved contract")

    node = root / "ComfyUI" / "custom_nodes" / "websocket_image_save.py"
    if not node.is_file() or node.is_symlink():
        raise RuntimeError("C4B approved node is missing or unsafe")
    expected_node_hash = "0b66b69eb7dab007d55bf63c5bd0f1343dcfbc2f5a350983f906ba2cd3dd5d23"
    actual_node_hash = hashlib.sha256(node.read_bytes()).hexdigest()
    if actual_node_hash != expected_node_hash:
        _record("c4b.wrapper.node_hash", {"actual": actual_node_hash}, "denied")
        raise RuntimeError("C4B approved node hash changed before import")

    activator = root / "System" / "PortableRuntime" / "launch_comfyui_isolated.py"
    if not activator.is_file() or activator.is_symlink():
        raise RuntimeError("C4B isolated activator is missing or unsafe")

    sys.argv = [str(activator), "--root", str(root), "--", *remainder]
    _record("c4b.wrapper.contract", {"arguments": remainder, "node": str(node)}, "allowed")
    runpy.run_path(str(activator), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
