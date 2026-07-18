#!/usr/bin/env python3
"""USB C4E controlled FOXAI WebUI two-profile lifecycle test.

Binds to the exact accepted C4D apply evidence, verifies the sealed isolated
runtime, launches the installed FOXAI WebUI locally under an audit wrapper,
proves legacy Safe Normal CPU behavior, then proves the explicit hash-locked
Approved Custom Nodes CPU profile and profile-switch refusal. It leaves both
FOXAI WebUI and ComfyUI stopped and re-verifies all protected boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import signal
import site
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from typing import Any

SUCCESS = "C4E_WEBUI_TWO_PROFILE_LIFECYCLE_VERIFIED_STOPPED_READY_FOR_C4F_BASELINE_SEAL_REVIEW"
BLOCKED = "C4E_BLOCKED_FAIL_CLOSED_STOPPED"
C4D_CLASSIFICATION = "C4D_WEBUI_PROFILE_APPLIED_VERIFIED_NO_LAUNCH_READY_FOR_C4E_APPROVAL"
DEFAULT_PROFILE = "safe-normal-cpu"
APPROVED_PROFILE = "approved-custom-nodes-cpu"
APPROVED_NODE_REL = "ComfyUI/custom_nodes/websocket_image_save.py"
APPROVED_NODE_SIZE = 1348
APPROVED_NODE_SHA256 = "0b66b69eb7dab007d55bf63c5bd0f1343dcfbc2f5a350983f906ba2cd3dd5d23"
APPROVED_NODE_CLASS = "SaveImageWebsocket"
APPROVED_NODE_DISPLAY = "Save Image (Websocket)"
WEBUI_PORT = 8765
COMFY_PORT = 8188
WEBUI_URL = "http://127.0.0.1:8765"
COMFY_URL = "http://127.0.0.1:8188"
START_TIMEOUT = 360.0
WEBUI_START_TIMEOUT = 150.0
STOP_TIMEOUT = 35.0
TARGET_COUNT = 39046
TARGET_BYTES = 1520221467
TARGET_TREE = "e689af293a34f34f59da8f76f0bbb682d2de2df712467cde0134d8c510e99b62"
SOURCE_EXCLUDES = {".git", ".venv", "venv", "models", "user", "temp", "input", "output"}


class GateError(RuntimeError):
    def __init__(self, message: str, code: int = 20):
        super().__init__(message)
        self.code = code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path, block: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(block), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8", newline="\n")


def verify_exact_file(path: Path, size: int, digest: str, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"{label} missing or unsafe: {path}", 21)
    actual_size = path.stat().st_size
    actual_hash = sha256_file(path)
    if actual_size != int(size) or actual_hash.lower() != str(digest).lower():
        raise GateError(
            f"{label} changed: {path} size={actual_size}/{size} sha256={actual_hash}/{digest}",
            21,
        )
    return {"path": str(path), "size_bytes": actual_size, "sha256": actual_hash, "verified": True}


def clean_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(key, None)
    env.update({
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "DO_NOT_TRACK": "1",
        "NO_PROXY": "127.0.0.1,localhost,::1",
        "no_proxy": "127.0.0.1,localhost,::1",
    })
    return env


def verify_package(package: Path, output: Path) -> dict[str, Any]:
    manifest = load_json(package / "PACKAGE_INTEGRITY.json")
    rows = []
    for record in manifest.get("files") or []:
        rows.append(verify_exact_file(
            package / PurePosixPath(str(record["path"])),
            int(record["size_bytes"]),
            str(record["sha256"]),
            f"C4E package {record['path']}",
        ))
    if not rows:
        raise GateError("C4E package manifest is empty", 21)
    result = {"verified": True, "file_count": len(rows), "files": rows}
    write_json(output / "package_verification.json", result)
    return result


def verify_c4d(root: Path, package: Path, output: Path) -> dict[str, Any]:
    binding = load_json(package / "EXPECTED_C4D_BINDING.json")
    base = (root / PurePosixPath(binding["c4d_relative_output"])).resolve(strict=True)
    integrity_path = base / "evidence_integrity.json"
    if sha256_file(integrity_path) != binding["evidence_integrity_sha256"]:
        raise GateError("Exact C4D evidence-integrity hash changed", 21)
    integrity = load_json(integrity_path)
    rows = []
    for record in integrity.get("files") or []:
        rows.append(verify_exact_file(
            base / PurePosixPath(str(record["file"])),
            int(record["size_bytes"]),
            str(record["sha256"]),
            f"C4D evidence {record['file']}",
        ))
    if len(rows) != int(binding["evidence_file_count"]):
        raise GateError("C4D evidence file count changed", 21)
    for name, expected in binding["exact_evidence_hashes"].items():
        if sha256_file(base / PurePosixPath(name)) != expected:
            raise GateError(f"Exact C4D evidence changed: {name}", 21)
    classification = load_json(base / "classification.json")
    receipt = load_json(base / "receipt.json")
    contract = load_json(base / "C4E_TEST_CONTRACT.json")
    applied = load_json(base / "applied_file_verification.json")
    if classification.get("verified") is not True or classification.get("mode") != C4D_CLASSIFICATION:
        raise GateError("C4D classification is not accepted", 21)
    if (
        receipt.get("verified") is not True
        or receipt.get("comfyui_launched")
        or receipt.get("webui_launched")
        or receipt.get("network_access")
        or receipt.get("default_profile_id") != DEFAULT_PROFILE
    ):
        raise GateError("C4D receipt does not preserve the accepted no-launch state", 21)
    expected_sequence = [
        "legacy GET starts Safe Normal CPU",
        "stop",
        "POST starts Approved Custom Nodes CPU",
        "verify SaveImageWebsocket and node hash state",
        "refuse profile switch while healthy",
        "stop",
        "final status STOPPED",
    ]
    if contract.get("verified") is not True or contract.get("test_sequence") != expected_sequence:
        raise GateError("C4D C4E lifecycle contract changed", 21)
    actual_applied = {
        Path(str(row["path"])).name.casefold(): (int(row["size_bytes"]), str(row["sha256"]))
        for row in applied.get("files") or []
    }
    if applied.get("verified") is not True or len(actual_applied) != 4:
        raise GateError("C4D applied-file verification changed", 21)
    result = {
        "verified": True,
        "base": str(base),
        "evidence_file_count": len(rows),
        "classification": classification.get("mode"),
        "contract": contract,
        "applied_files": applied.get("files"),
    }
    write_json(output / "c4d_input_verification.json", result)
    return binding


def verify_boundaries(root: Path, binding: dict[str, Any], output: Path, phase: str) -> dict[str, Any]:
    integrated = []
    protected = []
    for record in binding["integrated_files"]:
        integrated.append(verify_exact_file(
            root / PurePosixPath(record["relative_path"]),
            int(record["size_bytes"]),
            record["sha256"],
            f"C4D integrated file {record['relative_path']}",
        ))
    for record in binding["protected_files"]:
        protected.append(verify_exact_file(
            root / PurePosixPath(record["path"]),
            int(record["size_bytes"]),
            record["sha256"],
            f"protected file {record['path']}",
        ))
    result = {
        "verified": True,
        "phase": phase,
        "integrated_file_count": len(integrated),
        "protected_file_count": len(protected),
        "integrated_files": integrated,
        "protected_files": protected,
    }
    write_json(output / f"live_boundaries_{phase}.json", result)
    return result


def verify_target(root: Path, binding: dict[str, Any], output: Path, phase: str) -> dict[str, Any]:
    inv_bind = binding["c3e_inventory"]
    inventory_path = root / PurePosixPath(inv_bind["relative_path"])
    verify_exact_file(inventory_path, int(inv_bind["size_bytes"]), inv_bind["sha256"], "sealed C3E inventory")
    inventory = load_json(inventory_path)
    target = root / "Runtime/ComfyUI/site-packages"
    if not target.is_dir() or target.is_symlink():
        raise GateError("Committed isolated target is missing or unsafe", 21)
    rows = inventory.get("files") or []
    if len(rows) != TARGET_COUNT:
        raise GateError("C3E inventory file count changed", 21)
    expected: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    missing: list[str] = []
    mismatches: list[dict[str, Any]] = []
    symlinks: list[str] = []
    aggregate = hashlib.sha256()
    total = 0
    print(f"[VERIFY] {phase}: rehashing {len(rows):,} isolated runtime files...", flush=True)
    for index, row in enumerate(rows, 1):
        rel = str(row["path"])
        key = rel.casefold()
        if key in expected:
            duplicates.append(rel)
        expected[key] = row
        path = target / PurePosixPath(rel)
        if not path.exists():
            missing.append(rel)
            continue
        if path.is_symlink():
            symlinks.append(rel)
            continue
        if not path.is_file():
            mismatches.append({"path": rel, "issue": "not_regular_file"})
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        total += size
        if size != int(row["size_bytes"]) or digest != str(row["sha256"]):
            mismatches.append({"path": rel, "size_bytes": size, "sha256": digest})
        aggregate.update(rel.casefold().encode("utf-8", errors="surrogatepass"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
        if index % 5000 == 0 or index == len(rows):
            print(f"[VERIFY] {phase}: {index:,}/{len(rows):,}", flush=True)
    actual_files: dict[str, str] = {}
    unexpected: list[str] = []
    for path in target.rglob("*"):
        if path.is_symlink():
            rel = path.relative_to(target).as_posix()
            if rel not in symlinks:
                symlinks.append(rel)
        elif path.is_file():
            rel = path.relative_to(target).as_posix()
            actual_files[rel.casefold()] = rel
            if rel.casefold() not in expected:
                unexpected.append(rel)
    result = {
        "verified": (
            not duplicates and not missing and not mismatches and not symlinks and not unexpected
            and len(actual_files) == TARGET_COUNT and total == TARGET_BYTES
            and aggregate.hexdigest() == TARGET_TREE
        ),
        "phase": phase,
        "file_count": len(actual_files),
        "total_bytes": total,
        "tree_sha256": aggregate.hexdigest(),
        "duplicates": duplicates[:100],
        "missing": missing[:100],
        "unexpected": unexpected[:100],
        "mismatches": mismatches[:100],
        "symlinks": symlinks[:100],
    }
    write_json(output / f"isolated_target_{phase}.json", result)
    if not result["verified"]:
        raise GateError(f"Isolated runtime failed {phase} verification", 27 if phase == "after" else 21)
    return result


def source_snapshot(comfy: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in comfy.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        parts = path.relative_to(comfy).parts
        if parts and parts[0].casefold() in SOURCE_EXCLUDES:
            continue
        rel = path.relative_to(comfy).as_posix()
        result[rel.casefold()] = {"path": rel, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return result


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    added = [after[key] for key in sorted(after.keys() - before.keys())]
    removed = [before[key] for key in sorted(before.keys() - after.keys())]
    changed = []
    for key in sorted(before.keys() & after.keys()):
        if before[key] != after[key]:
            changed.append({"before": before[key], "after": after[key]})
    return {"verified": not (added or removed or changed), "added": added, "removed": removed, "changed": changed}


def selected_operational_snapshot(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    targets = [
        root / "Runtime/ComfyUI/state",
        root / "Runtime/ComfyUI/logs/normal",
        root / "Logs/web_gui.log",
    ]
    for base in targets:
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else [base, *base.rglob("*")]
        for path in candidates:
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if path.is_symlink():
                result[rel.casefold()] = {"path": rel, "kind": "symlink"}
            elif path.is_dir():
                result[rel.casefold()] = {"path": rel, "kind": "directory"}
            elif path.is_file():
                result[rel.casefold()] = {"path": rel, "kind": "file", "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return result


def operational_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    comparison = compare_snapshots(before, after)
    allowed = True
    invalid: list[dict[str, Any]] = []
    for item in comparison["added"]:
        path = item["path"].replace("\\", "/").casefold()
        if not (path.startswith("runtime/comfyui/state/") or path.startswith("runtime/comfyui/logs/normal/") or path == "runtime/comfyui/state" or path == "runtime/comfyui/logs/normal" or path == "logs/web_gui.log"):
            allowed = False
            invalid.append({"kind": "added", "item": item})
    for item in comparison["removed"]:
        allowed = False
        invalid.append({"kind": "removed", "item": item})
    for item in comparison["changed"]:
        path = item["after"]["path"].replace("\\", "/").casefold()
        if not (path == "runtime/comfyui/state/normal_instance.json" or path == "logs/web_gui.log"):
            allowed = False
            invalid.append({"kind": "changed", "item": item})
    comparison["allowed_expected_lifecycle_changes_only"] = allowed
    comparison["invalid_changes"] = invalid
    return comparison


def activate_psutil(root: Path):
    site.addsitedir(str(root / "Runtime/ComfyUI/site-packages"))
    import psutil  # type: ignore
    return psutil


def listeners(psutil, port: int) -> list[dict[str, Any]]:
    rows = []
    for conn in psutil.net_connections(kind="tcp"):
        if conn.status != psutil.CONN_LISTEN or not conn.laddr:
            continue
        if int(conn.laddr.port) != port:
            continue
        rows.append({"ip": str(conn.laddr.ip), "port": int(conn.laddr.port), "pid": conn.pid, "status": conn.status})
    return rows


def matching_processes(psutil, root: Path) -> list[dict[str, Any]]:
    markers = ("foxai_web.py", "c4e_audited_webui_launcher.py", "manage_comfyui_normal.py", "launch_comfyui_isolated.py", "comfyui\\main.py", "comfyui/main.py")
    root_folded = str(root).casefold()
    rows = []
    for process in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"]):
        try:
            cmdline = " ".join(str(item) for item in (process.info.get("cmdline") or []))
            folded = cmdline.casefold()
            if root_folded in folded and any(marker in folded for marker in markers):
                rows.append({
                    "pid": process.info.get("pid"),
                    "name": process.info.get("name"),
                    "exe": process.info.get("exe"),
                    "cmdline": cmdline,
                    "create_time": process.info.get("create_time"),
                })
        except Exception:
            continue
    return rows


def network_snapshot(psutil, root: Path, label: str) -> dict[str, Any]:
    processes = matching_processes(psutil, root)
    pids = {int(row["pid"]) for row in processes if row.get("pid") is not None}
    connections = []
    violations = []
    for conn in psutil.net_connections(kind="tcp"):
        if conn.pid not in pids:
            continue
        local = None if not conn.laddr else {"ip": str(conn.laddr.ip), "port": int(conn.laddr.port)}
        remote = None if not conn.raddr else {"ip": str(conn.raddr.ip), "port": int(conn.raddr.port)}
        row = {"pid": conn.pid, "status": conn.status, "local": local, "remote": remote}
        connections.append(row)
        local_ip = (local or {}).get("ip")
        remote_ip = (remote or {}).get("ip")
        loopback = {"127.0.0.1", "::1", "0.0.0.0", "::"}
        if conn.status == psutil.CONN_LISTEN:
            if local_ip not in {"127.0.0.1", "::1"}:
                violations.append(row)
        elif remote_ip and remote_ip not in loopback:
            violations.append(row)
    return {"verified": not violations, "label": label, "processes": processes, "connections": connections, "violations": violations}


def port_open(port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_port_closed(port: int, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    checks = []
    while time.monotonic() < deadline:
        opened = port_open(port)
        checks.append({"utc": utc_now(), "open": opened})
        if not opened:
            return {"verified": True, "closed": True, "port": port, "checks": checks}
        time.sleep(0.5)
    return {"verified": False, "closed": False, "port": port, "checks": checks}


def http_request(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 30.0, text_limit: int = 200000) -> dict[str, Any]:
    body = None
    headers = {"Cache-Control": "no-cache"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
            parsed = None
            if "json" in content_type or raw.lstrip().startswith((b"{", b"[")):
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except Exception:
                    parsed = None
            return {
                "ok": 200 <= response.status < 300,
                "status": response.status,
                "url": url,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "content_type": content_type,
                "body_size_bytes": len(raw),
                "text": raw.decode("utf-8", errors="replace")[:max(0, int(text_limit))],
                "text_truncated": len(raw) > max(0, int(text_limit)),
                "json": parsed,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return {"ok": False, "status": exc.code, "url": url, "elapsed_seconds": round(time.monotonic() - started, 3), "text": raw.decode("utf-8", errors="replace")[:200000], "json": None}
    except Exception as exc:
        return {"ok": False, "status": None, "url": url, "elapsed_seconds": round(time.monotonic() - started, 3), "error": f"{type(exc).__name__}: {exc}", "json": None}


def wait_webui(proc: subprocess.Popen[bytes], timeout: float) -> dict[str, Any]:
    """Wait for the lightweight page first, then perform one full status check.

    The full /api/status route intentionally inventories several local FOXAI
    services and can take more than three seconds on a portable USB runtime.
    C4E-R1 therefore avoids aborting repeated status responses while they are
    still being generated.
    """
    deadline = time.monotonic() + timeout
    checks = []
    root_ready = False
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return {"verified": False, "reason": f"WebUI exited with code {proc.returncode}", "checks": checks}
        probe = http_request("GET", WEBUI_URL + "/", timeout=8)
        checks.append({"utc": utc_now(), "phase": "lightweight_root", "probe": probe})
        if probe.get("ok"):
            root_ready = True
            break
        time.sleep(1)
    if not root_ready:
        return {"verified": False, "reason": "WebUI listener did not serve the root page", "checks": checks}

    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return {"verified": False, "reason": f"WebUI exited with code {proc.returncode}", "checks": checks}
        probe = http_request("GET", WEBUI_URL + "/api/status", timeout=20)
        checks.append({"utc": utc_now(), "phase": "full_status", "probe": probe})
        if probe.get("ok") and isinstance(probe.get("json"), dict):
            return {"verified": True, "checks": checks, "status": probe["json"]}
        time.sleep(1)
    return {"verified": False, "reason": "WebUI root responded but full status did not complete", "checks": checks}


def verify_webui_html() -> dict[str, Any]:
    probe = http_request("GET", WEBUI_URL + "/", timeout=20, text_limit=2_000_000)
    text = probe.get("text") or ""
    checks = {
        "http_200": probe.get("ok") is True,
        "complete_body_captured": probe.get("text_truncated") is False,
        "selector_present": "id=comfyProfile" in text or 'id="comfyProfile"' in text,
        "safe_profile_present": "Safe Normal CPU" in text,
        "approved_profile_present": "Approved Custom Nodes CPU" in text,
        "profile_post_function_present": "startComfyProfile" in text and "/api/launch/comfy/profile" in text,
    }
    result = {"verified": all(checks.values()), "checks": checks, "probe": {k: v for k, v in probe.items() if k != "text"}}
    if not result["verified"]:
        raise GateError("WebUI HTML did not expose the exact two-profile selector", 23)
    return result


def unwrap_controller(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("controller")
    return value if isinstance(value, dict) else payload


def verify_profile_response(response: dict[str, Any], profile_id: str, approved: bool) -> dict[str, Any]:
    payload = response.get("json")
    if not response.get("ok") or not isinstance(payload, dict) or payload.get("ok") is not True:
        raise GateError(f"WebUI failed to start profile {profile_id}: {payload or response.get('error') or response.get('text')}", 24)
    controller = unwrap_controller(payload)
    status = controller.get("status") if isinstance(controller.get("status"), dict) else controller
    active_id = controller.get("active_profile_id") or status.get("active_profile_id")
    hash_state = controller.get("approved_node_hash_state") or status.get("approved_node_hash_state")
    if controller.get("state") != "HEALTHY" or active_id != profile_id:
        raise GateError(f"Profile {profile_id} did not reach exact HEALTHY state", 24)
    if approved and hash_state != "VERIFIED":
        raise GateError("Approved custom-node profile did not report VERIFIED node hash", 24)
    if not approved and hash_state not in {"NOT_APPLICABLE", "NOT_RUNNING"}:
        raise GateError("Safe profile reported an unexpected approved-node hash state", 24)
    return {"verified": True, "profile_id": profile_id, "approved": approved, "payload": payload}


def verify_status_profile(response: dict[str, Any], profile_id: str, approved: bool) -> dict[str, Any]:
    payload = response.get("json")
    if not response.get("ok") or not isinstance(payload, dict):
        raise GateError("WebUI status route did not return JSON", 24)
    if payload.get("state") != "HEALTHY" or payload.get("active_profile_id") != profile_id:
        raise GateError(f"WebUI status did not prove active profile {profile_id}", 24)
    if payload.get("default_profile_id") != DEFAULT_PROFILE:
        raise GateError("Safe Normal CPU is no longer the default", 24)
    if approved and payload.get("approved_node_hash_state") != "VERIFIED":
        raise GateError("Approved profile status did not preserve VERIFIED node hash", 24)
    state = payload.get("recorded_state") or {}
    command = [str(item) for item in state.get("command") or []]
    if state.get("profile_id") != profile_id or state.get("source") != "webui":
        raise GateError("Controller state did not bind the active WebUI profile", 24)
    if approved:
        exact_tail = ["--cpu", "--disable-all-custom-nodes", "--whitelist-custom-nodes", "websocket_image_save.py", "--listen", "127.0.0.1", "--port", "8188"]
        if command[-len(exact_tail):] != exact_tail:
            raise GateError("Approved profile command escaped the exact allowlisted contract", 24)
    else:
        if "--whitelist-custom-nodes" in command:
            raise GateError("Safe profile unexpectedly enabled a custom node", 24)
        exact_tail = ["--cpu", "--disable-all-custom-nodes", "--listen", "127.0.0.1", "--port", "8188"]
        if command[-len(exact_tail):] != exact_tail:
            raise GateError("Safe profile command escaped the exact safe contract", 24)
    return {"verified": True, "profile_id": profile_id, "payload": payload}


def verify_node_registration() -> dict[str, Any]:
    probe = http_request("GET", COMFY_URL + "/object_info/SaveImageWebsocket", timeout=15)
    data = probe.get("json")
    entry = None
    if isinstance(data, dict):
        if APPROVED_NODE_CLASS in data and isinstance(data[APPROVED_NODE_CLASS], dict):
            entry = data[APPROVED_NODE_CLASS]
        elif data.get("name") == APPROVED_NODE_CLASS:
            entry = data
    display = entry.get("display_name") if isinstance(entry, dict) else None
    verified = bool(probe.get("ok") and entry is not None and display in {None, "", APPROVED_NODE_DISPLAY})
    result = {"verified": verified, "class_key": APPROVED_NODE_CLASS, "expected_display_name": APPROVED_NODE_DISPLAY, "reported_display_name": display, "entry": entry, "probe": {k: v for k, v in probe.items() if k != "text"}}
    if not verified:
        raise GateError("SaveImageWebsocket was not registered through the live ComfyUI API", 24)
    return result


def verify_conflict(response: dict[str, Any]) -> dict[str, Any]:
    payload = response.get("json")
    controller = payload.get("controller") if isinstance(payload, dict) else None
    controller = controller if isinstance(controller, dict) else payload
    verified = bool(
        response.get("ok")
        and isinstance(payload, dict)
        and payload.get("ok") is False
        and isinstance(controller, dict)
        and controller.get("state") == "PROFILE_CONFLICT"
        and "Stop ComfyUI" in str(controller.get("message") or payload.get("message") or "")
    )
    result = {"verified": verified, "payload": payload}
    if not verified:
        raise GateError("WebUI did not refuse a profile switch while the approved profile was healthy", 24)
    return result


def stop_via_webui(label: str) -> dict[str, Any]:
    response = http_request("GET", WEBUI_URL + "/api/stop/comfy", timeout=60)
    payload = response.get("json")
    if not response.get("ok") or not isinstance(payload, dict) or payload.get("ok") is not True or payload.get("state") != "STOPPED":
        raise GateError(f"WebUI stop failed during {label}", 25)
    close = wait_port_closed(COMFY_PORT, STOP_TIMEOUT)
    if not close["closed"]:
        raise GateError(f"ComfyUI port remained open after {label}", 25)
    final_status = http_request("GET", WEBUI_URL + "/api/status/comfy", timeout=30)
    status_payload = final_status.get("json")
    if not final_status.get("ok") or not isinstance(status_payload, dict) or status_payload.get("state") != "STOPPED":
        raise GateError(f"Controller did not finish STOPPED after {label}", 25)
    return {"verified": True, "stop_response": payload, "port_close": close, "final_status": status_payload}


def stop_webui(proc: subprocess.Popen[bytes], output: Path) -> dict[str, Any]:
    result = {"pid": proc.pid, "requested": True, "method": None, "forced": False, "returncode": proc.poll(), "started": utc_now()}
    if proc.poll() is None:
        try:
            if os.name == "nt" and hasattr(signal, "CTRL_BREAK_EVENT"):
                proc.send_signal(signal.CTRL_BREAK_EVENT)
                result["method"] = "CTRL_BREAK_EVENT"
            else:
                proc.terminate()
                result["method"] = "terminate"
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            result["forced"] = True
            result["method"] = f"{result['method']}_then_terminate"
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                result["method"] = f"{result['method']}_then_kill"
                proc.kill()
                proc.wait(timeout=10)
    result["returncode"] = proc.poll()
    result["completed"] = utc_now()
    result["port_close"] = wait_port_closed(WEBUI_PORT, 20)
    write_json(output / "webui_stop_receipt.json", result)
    return result


def parse_audit(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise GateError("C4E WebUI audit log is missing", 26)

    events = []
    errors = []
    for number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(),
        1,
    ):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append({"line": number, "error": str(exc)})

    denied = [row for row in events if row.get("decision") == "denied"]
    listener_binds = [
        row
        for row in events
        if row.get("event") == "socket.bind"
        and row.get("decision") == "allowed_webui_listener"
    ]
    external_socket_events = [
        row
        for row in events
        if row.get("event") in {"socket.connect", "socket.connect_ex"}
        and row.get("decision") == "denied"
    ]

    # R3 validates the original structured Python Popen request first, then
    # authorizes the lower-level platform audit event. Both records are
    # required and must pair one-for-one.
    guarded_manager_events = [
        row
        for row in events
        if row.get("event") == "c4e.guard.Popen"
        and row.get("decision") == "allowed_exact_manager_command"
    ]
    platform_popen_events = [
        row
        for row in events
        if row.get("event") == "subprocess.Popen"
    ]
    authorized_platform_events = [
        row
        for row in platform_popen_events
        if row.get("decision") == "allowed_guarded_manager_command"
        and bool((row.get("args") or {}).get("authorized_by_high_level_guard"))
    ]

    allowed_tails = {
        ("status",),
        ("stop",),
        (
            "spawn",
            "--source",
            "webui",
            "--profile",
            "safe-normal-cpu",
        ),
        (
            "spawn",
            "--source",
            "webui",
            "--profile",
            "approved-custom-nodes-cpu",
        ),
    }
    observed_tails = [
        tuple((row.get("args") or {}).get("tail") or [])
        for row in guarded_manager_events
    ]
    unexpected_tails = [
        list(tail) for tail in observed_tails if tail not in allowed_tails
    ]
    tail_counts = {
        "status": observed_tails.count(("status",)),
        "stop": observed_tails.count(("stop",)),
        "safe_spawn": observed_tails.count(
            (
                "spawn",
                "--source",
                "webui",
                "--profile",
                "safe-normal-cpu",
            )
        ),
        "approved_spawn": observed_tails.count(
            (
                "spawn",
                "--source",
                "webui",
                "--profile",
                "approved-custom-nodes-cpu",
            )
        ),
    }

    manager_contract_ok = (
        len(guarded_manager_events) >= 8
        and len(platform_popen_events) == len(guarded_manager_events)
        and len(authorized_platform_events) == len(guarded_manager_events)
        and not unexpected_tails
        and tail_counts["status"] >= 2
        and tail_counts["stop"] >= 2
        and tail_counts["safe_spawn"] >= 2
        and tail_counts["approved_spawn"] >= 1
    )

    result = {
        "verified": (
            not errors
            and not denied
            and not external_socket_events
            and len(listener_binds) >= 1
            and manager_contract_ok
        ),
        "event_count": len(events),
        "parse_errors": errors,
        "denied_events": denied,
        "webui_listener_bind_count": len(listener_binds),
        "guarded_manager_command_count": len(guarded_manager_events),
        "platform_popen_event_count": len(platform_popen_events),
        "authorized_platform_popen_count": len(authorized_platform_events),
        "manager_event_pairing_verified": (
            len(platform_popen_events)
            == len(guarded_manager_events)
            == len(authorized_platform_events)
        ),
        "manager_tail_counts": tail_counts,
        "unexpected_manager_tails": unexpected_tails,
        "guarded_manager_events": guarded_manager_events,
        "platform_popen_events": platform_popen_events,
        "external_socket_events": external_socket_events,
        "write_open_count": sum(
            1
            for row in events
            if row.get("decision") == "observed_write_open"
        ),
    }
    if not result["verified"]:
        raise GateError(
            "C4E WebUI audit evidence did not satisfy the exact contract",
            26,
        )
    return result


def direct_manager_stop(root: Path, output: Path, label: str) -> dict[str, Any]:
    portable = root / "Runtime/Desktop/python/python.exe"
    manager = root / "System/PortableRuntime/manage_comfyui_normal.py"
    command = [str(portable), "-I", "-B", "-S", str(manager), "--root", str(root), "--json", "stop"]
    try:
        completed = subprocess.run(command, cwd=str(root), env=clean_env(), capture_output=True, text=True, timeout=45, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        result = {"label": label, "command": command, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}
    except Exception as exc:
        result = {"label": label, "command": command, "error": f"{type(exc).__name__}: {exc}"}
    write_json(output / f"emergency_manager_stop_{label}.json", result)
    return result


def tail_text(path: Path, max_bytes: int = 65536) -> str:
    if not path.exists():
        return ""
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > max_bytes:
            handle.seek(size - max_bytes)
        return handle.read().decode("utf-8", errors="replace")


def create_evidence_integrity(output: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name in {"evidence_integrity.json", "UPLOAD_THIS_C4E_REVIEW.zip"}:
            continue
        rows.append({"file": path.relative_to(output).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    result = {"verified": True, "file_count": len(rows), "files": rows}
    write_json(output / "evidence_integrity.json", result)
    return result


def create_review_zip(output: Path) -> Path:
    archive = output / "UPLOAD_THIS_C4E_REVIEW.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(output.rglob("*")):
            if path.is_file() and path != archive:
                bundle.write(path, path.relative_to(output).as_posix())
    return archive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--package", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve(strict=True)
    package = Path(args.package).resolve(strict=True)
    output_base = package / "TEST_OUTPUT"
    output_base.mkdir(parents=True, exist_ok=True)
    output = output_base / run_id()
    counter = 1
    while output.exists():
        output = output_base / f"{run_id()}_{counter}"
        counter += 1
    output.mkdir(parents=True)

    started = utc_now()
    webui_proc: subprocess.Popen[bytes] | None = None
    stdout_handle = None
    stderr_handle = None
    source_before: dict[str, Any] = {}
    operational_before: dict[str, Any] = {}
    exit_code = 20
    classification: dict[str, Any] = {"mode": BLOCKED, "verified": False, "blocking_findings": []}
    lifecycle: dict[str, Any] = {}

    try:
        print("[C4E] Verifying package and exact accepted C4D evidence...", flush=True)
        verify_package(package, output)
        approval = load_json(package / "OPERATOR_APPROVAL.json")
        if approval.get("approved") is not True or approval.get("leave_running"):
            raise GateError("C4E operator approval is missing or requests leaving a process running", 21)
        write_json(output / "operator_approval.json", approval)
        binding = verify_c4d(root, package, output)
        verify_boundaries(root, binding, output, "before")
        verify_target(root, binding, output, "before")
        node_before = verify_exact_file(root / APPROVED_NODE_REL, APPROVED_NODE_SIZE, APPROVED_NODE_SHA256, "approved custom node")
        write_json(output / "approved_node_before.json", node_before)

        psutil = activate_psutil(root)
        initial_processes = matching_processes(psutil, root)
        initial_listeners = {"webui": listeners(psutil, WEBUI_PORT), "comfyui": listeners(psutil, COMFY_PORT)}
        write_json(output / "initial_process_safety.json", {"verified": not initial_processes and not initial_listeners["webui"] and not initial_listeners["comfyui"], "matching_processes": initial_processes, "listeners": initial_listeners})
        if initial_processes or initial_listeners["webui"] or initial_listeners["comfyui"]:
            raise GateError("FOXAI WebUI or ComfyUI is already active; C4E did not launch", 22)

        source_before = source_snapshot(root / "ComfyUI")
        operational_before = selected_operational_snapshot(root)
        write_json(output / "source_boundary_before.json", {"file_count": len(source_before), "total_bytes": sum(row["size_bytes"] for row in source_before.values())})
        write_json(output / "operational_storage_before.json", {"rows": list(operational_before.values())})

        webui_python = (root / "env/python/python.exe").resolve(strict=True)
        manager_python = (root / "Runtime/Desktop/python/python.exe").resolve(strict=True)
        webui = (root / "core/foxai_web.py").resolve(strict=True)
        wrapper = (package / "System/WebUITest/c4e_audited_webui_launcher.py").resolve(strict=True)
        audit = output / "webui_audit.jsonl"
        stdout_path = output / "webui_stdout.log"
        stderr_path = output / "webui_stderr.log"
        stdout_handle = stdout_path.open("wb")
        stderr_handle = stderr_path.open("wb")
        command = [str(webui_python), "-B", "-s", str(wrapper), "--root", str(root), "--audit", str(audit)]
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        print("[C4E] Starting FOXAI WebUI locally at 127.0.0.1:8765; no browser will open...", flush=True)
        webui_proc = subprocess.Popen(command, cwd=str(root), env=clean_env(), stdin=subprocess.DEVNULL, stdout=stdout_handle, stderr=stderr_handle, creationflags=creationflags)
        write_json(output / "webui_launch_receipt.json", {"started": utc_now(), "pid": webui_proc.pid, "command": command, "cwd": str(root), "webui_python": str(webui_python), "webui_python_sha256": sha256_file(webui_python), "manager_python": str(manager_python), "manager_python_sha256": sha256_file(manager_python), "webui_sha256": sha256_file(webui), "wrapper_sha256": sha256_file(wrapper), "listen": "127.0.0.1", "port": WEBUI_PORT, "browser_open": False, "external_network_permitted": False})

        web_health = wait_webui(webui_proc, WEBUI_START_TIMEOUT)
        write_json(output / "webui_health.json", web_health)
        if not web_health.get("verified"):
            raise GateError(str(web_health.get("reason") or "FOXAI WebUI did not become healthy"), 23)
        html = verify_webui_html()
        write_json(output / "webui_profile_selector_verification.json", html)
        network0 = network_snapshot(psutil, root, "webui_only")
        write_json(output / "network_webui_only.json", network0)
        if not network0["verified"]:
            raise GateError("WebUI opened an external TCP endpoint", 26)
        web_listeners = listeners(psutil, WEBUI_PORT)
        if len(web_listeners) != 1 or web_listeners[0]["ip"] not in {"127.0.0.1", "::1"} or int(web_listeners[0].get("pid") or 0) != webui_proc.pid:
            raise GateError("Exact WebUI listener ownership at 127.0.0.1:8765 was not proved", 26)

        print("[C4E] Phase 1: legacy WebUI start must select Safe Normal CPU...", flush=True)
        safe_start_http = http_request("GET", WEBUI_URL + "/api/launch/comfy", timeout=START_TIMEOUT)
        safe_start = verify_profile_response(safe_start_http, DEFAULT_PROFILE, approved=False)
        write_json(output / "safe_legacy_start.json", safe_start)
        safe_status_http = http_request("GET", WEBUI_URL + "/api/status/comfy", timeout=30)
        safe_status = verify_status_profile(safe_status_http, DEFAULT_PROFILE, approved=False)
        write_json(output / "safe_profile_status.json", safe_status)
        network_safe = network_snapshot(psutil, root, "safe_profile_healthy")
        write_json(output / "network_safe_profile.json", network_safe)
        if not network_safe["verified"]:
            raise GateError("Safe profile opened an external TCP endpoint", 26)
        comfy_listeners = listeners(psutil, COMFY_PORT)
        safe_child_pid = int((safe_status["payload"].get("recorded_state") or {}).get("child_pid") or 0)
        if len(comfy_listeners) != 1 or comfy_listeners[0]["ip"] not in {"127.0.0.1", "::1"} or int(comfy_listeners[0].get("pid") or 0) != safe_child_pid:
            raise GateError("Safe profile listener ownership at 127.0.0.1:8188 was not proved", 26)
        safe_stop = stop_via_webui("safe profile stop")
        write_json(output / "safe_profile_stop.json", safe_stop)

        print("[C4E] Phase 2: explicit Approved Custom Nodes CPU start...", flush=True)
        approved_start_http = http_request("POST", WEBUI_URL + "/api/launch/comfy/profile", {"profile_id": APPROVED_PROFILE}, timeout=START_TIMEOUT)
        approved_start = verify_profile_response(approved_start_http, APPROVED_PROFILE, approved=True)
        write_json(output / "approved_profile_start.json", approved_start)
        approved_status_http = http_request("GET", WEBUI_URL + "/api/status/comfy", timeout=30)
        approved_status = verify_status_profile(approved_status_http, APPROVED_PROFILE, approved=True)
        write_json(output / "approved_profile_status.json", approved_status)
        registration = verify_node_registration()
        write_json(output / "approved_node_registration.json", registration)
        network_approved = network_snapshot(psutil, root, "approved_profile_healthy")
        write_json(output / "network_approved_profile.json", network_approved)
        if not network_approved["verified"]:
            raise GateError("Approved profile opened an external TCP endpoint", 26)
        approved_listeners = listeners(psutil, COMFY_PORT)
        approved_child_pid = int((approved_status["payload"].get("recorded_state") or {}).get("child_pid") or 0)
        if len(approved_listeners) != 1 or approved_listeners[0]["ip"] not in {"127.0.0.1", "::1"} or int(approved_listeners[0].get("pid") or 0) != approved_child_pid:
            raise GateError("Approved profile listener ownership at 127.0.0.1:8188 was not proved", 26)

        print("[C4E] Proving profile switching is refused while approved profile is healthy...", flush=True)
        conflict_http = http_request("GET", WEBUI_URL + "/api/launch/comfy", timeout=60)
        conflict = verify_conflict(conflict_http)
        write_json(output / "profile_switch_refusal.json", conflict)
        approved_still_http = http_request("GET", WEBUI_URL + "/api/status/comfy", timeout=30)
        approved_still = verify_status_profile(approved_still_http, APPROVED_PROFILE, approved=True)
        write_json(output / "approved_profile_after_refusal.json", approved_still)

        approved_stop = stop_via_webui("approved profile stop")
        write_json(output / "approved_profile_stop.json", approved_stop)
        final_comfy_status_http = http_request("GET", WEBUI_URL + "/api/status/comfy", timeout=30)
        final_comfy_status = final_comfy_status_http.get("json")
        if not final_comfy_status_http.get("ok") or not isinstance(final_comfy_status, dict) or final_comfy_status.get("state") != "STOPPED":
            raise GateError("Final WebUI ComfyUI status is not STOPPED", 25)
        write_json(output / "final_comfyui_status.json", final_comfy_status)

        lifecycle = {
            "verified": True,
            "sequence": [
                "WEBUI_HEALTHY",
                "LEGACY_GET_SAFE_NORMAL_CPU_HEALTHY",
                "SAFE_STOPPED",
                "EXPLICIT_APPROVED_CUSTOM_NODES_CPU_HEALTHY",
                "SAVE_IMAGE_WEBSOCKET_REGISTERED",
                "SAFE_PROFILE_SWITCH_REFUSED_WHILE_APPROVED_HEALTHY",
                "APPROVED_STOPPED",
                "COMFYUI_FINAL_STOPPED",
            ],
            "safe_default_preserved": True,
            "approved_node_hash_verified": True,
            "profile_switch_refused": True,
            "browser_open": False,
            "external_network_access": False,
        }
        write_json(output / "lifecycle_summary.json", lifecycle)

        print("[C4E] Stopping FOXAI WebUI and verifying final closed ports...", flush=True)
        web_stop = stop_webui(webui_proc, output)
        if web_stop.get("forced") or not web_stop.get("port_close", {}).get("closed"):
            raise GateError("FOXAI WebUI did not stop cleanly", 25)
        webui_proc = None

        audit_result = parse_audit(audit)
        write_json(output / "webui_audit_summary.json", audit_result)
        if stdout_handle:
            stdout_handle.flush()
        if stderr_handle:
            stderr_handle.flush()
        write_json(output / "webui_log_summary.json", {"stdout_size_bytes": stdout_path.stat().st_size, "stderr_size_bytes": stderr_path.stat().st_size, "stdout_tail": tail_text(stdout_path), "stderr_tail": tail_text(stderr_path)})

        verify_boundaries(root, binding, output, "after")
        verify_target(root, binding, output, "after")
        node_after = verify_exact_file(root / APPROVED_NODE_REL, APPROVED_NODE_SIZE, APPROVED_NODE_SHA256, "approved custom node")
        write_json(output / "approved_node_after.json", node_after)
        source_after = source_snapshot(root / "ComfyUI")
        source_comparison = compare_snapshots(source_before, source_after)
        write_json(output / "source_boundary_comparison.json", source_comparison)
        if not source_comparison["verified"]:
            raise GateError("ComfyUI source changed during C4E", 27)
        operational_after = selected_operational_snapshot(root)
        op_diff = operational_diff(operational_before, operational_after)
        write_json(output / "operational_storage_changes.json", op_diff)
        if not op_diff["allowed_expected_lifecycle_changes_only"]:
            raise GateError("Unexpected operational storage changed during C4E", 27)

        final_processes = matching_processes(psutil, root)
        final_listeners = {"webui": listeners(psutil, WEBUI_PORT), "comfyui": listeners(psutil, COMFY_PORT)}
        final_safety = {"verified": not final_processes and not final_listeners["webui"] and not final_listeners["comfyui"], "matching_processes": final_processes, "listeners": final_listeners}
        write_json(output / "final_process_safety.json", final_safety)
        if not final_safety["verified"]:
            raise GateError("C4E left FOXAI WebUI or ComfyUI running", 25)

        classification = {
            "mode": SUCCESS,
            "verified": True,
            "blocking_findings": [],
            "safe_default_verified": True,
            "approved_profile_verified": True,
            "approved_node_registration_verified": True,
            "profile_switch_refusal_verified": True,
            "external_network_access": False,
            "browser_open": False,
            "webui_left_running": False,
            "comfyui_left_running": False,
            "next_gate": "C4F dual-profile known-good baseline update and closure requires fresh explicit approval",
        }
        exit_code = 0
    except GateError as exc:
        exit_code = exc.code
        classification = {"mode": BLOCKED, "verified": False, "blocking_findings": [str(exc)], "exit_code": exit_code}
        write_json(output / "error.json", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
    except Exception as exc:
        exit_code = 29
        classification = {"mode": BLOCKED, "verified": False, "blocking_findings": [f"{type(exc).__name__}: {exc}"], "exit_code": exit_code}
        write_json(output / "error.json", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
    finally:
        if webui_proc is not None:
            try:
                direct_manager_stop(root, output, "failure_cleanup")
            except Exception:
                pass
            try:
                stop_webui(webui_proc, output)
            except Exception as exc:
                write_json(output / "webui_cleanup_error.json", {"error": f"{type(exc).__name__}: {exc}"})
        else:
            if port_open(COMFY_PORT):
                try:
                    direct_manager_stop(root, output, "final_cleanup")
                except Exception:
                    pass
        if stdout_handle:
            try:
                stdout_handle.close()
            except Exception:
                pass
        if stderr_handle:
            try:
                stderr_handle.close()
            except Exception:
                pass

        completed = utc_now()
        write_json(output / "classification.json", classification)
        receipt = {
            "action": "foxai_usbc4e_webui_two_profile_lifecycle_test",
            "state": "verified_stopped" if exit_code == 0 else "blocked_fail_closed_cleanup_attempted",
            "started": started,
            "completed": completed,
            "root": str(root),
            "output": str(output),
            "verified": exit_code == 0,
            "classification": classification.get("mode"),
            "safe_default_profile": DEFAULT_PROFILE,
            "approved_profile": APPROVED_PROFILE,
            "approved_node_sha256": APPROVED_NODE_SHA256,
            "browser_open": False,
            "external_network_access": False,
            "package_install": False,
            "package_uninstall": False,
            "source_modified": False,
            "runtime_target_modified": False,
            "webui_left_running": port_open(WEBUI_PORT),
            "comfyui_left_running": port_open(COMFY_PORT),
            "exit_code": exit_code,
        }
        write_json(output / "receipt.json", receipt)
        report_lines = [
            "# FOXAI USB C4E WebUI Two-Profile Lifecycle Test",
            "",
            f"- Classification: `{classification.get('mode')}`",
            f"- Verified: `{classification.get('verified')}`",
            f"- Safe default: `{DEFAULT_PROFILE}`",
            f"- Approved profile: `{APPROVED_PROFILE}`",
            f"- WebUI left running: `{receipt['webui_left_running']}`",
            f"- ComfyUI left running: `{receipt['comfyui_left_running']}`",
            f"- Browser opened: `False`",
            f"- External network access: `False`",
        ]
        if classification.get("blocking_findings"):
            report_lines += ["", "## Blocking findings", *[f"- {item}" for item in classification["blocking_findings"]]]
        (output / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8", newline="\n")
        create_evidence_integrity(output)
        archive = create_review_zip(output)
        print("", flush=True)
        print(f"[C4E] Classification: {classification.get('mode')}", flush=True)
        print(f"[C4E] Review ZIP: {archive}", flush=True)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
