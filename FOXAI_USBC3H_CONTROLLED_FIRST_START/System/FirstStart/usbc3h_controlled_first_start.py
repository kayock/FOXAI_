#!/usr/bin/env python3
"""USB C3H controlled first ComfyUI start, health verification, and stop.

Stdlib only. This is the first approved live-start gate. It binds to the exact
accepted C3G evidence and launch contract, starts ComfyUI only through the
integrated isolated launcher on localhost CPU mode with custom nodes disabled,
verifies health and process/network state, then stops it before returning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

SUCCESS_CLASSIFICATION = "C3H_FIRST_START_VERIFIED_STOPPED_READY_FOR_C3I_REVIEW"
BLOCKED_CLASSIFICATION = "C3H_BLOCKED_FAIL_CLOSED"
STARTUP_TIMEOUT = 300.0
HEALTH_STABILITY_SECONDS = 10.0
GRACEFUL_STOP_TIMEOUT = 25.0
PORT_CLOSE_TIMEOUT = 20.0
ALLOWED_OPERATIONAL_TOP_LEVEL = {"user", "temp", "output", "input"}
SOURCE_SCAN_EXCLUDED_TOP_LEVEL = {
    ".git", ".venv", "venv", "models", "user", "temp", "output", "input"
}


class GateError(RuntimeError):
    def __init__(self, message: str, code: int = 20) -> None:
        super().__init__(message)
        self.code = code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_exact_file(path: Path, size: int, expected_hash: str, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"{label} missing or unsafe: {path}", 21)
    actual_size = path.stat().st_size
    actual_hash = sha256_file(path)
    if actual_size != size or actual_hash.lower() != expected_hash.lower():
        raise GateError(
            f"{label} changed: {path} (size {actual_size}, sha256 {actual_hash})",
            21,
        )
    return {
        "path": str(path),
        "size_bytes": actual_size,
        "sha256": actual_hash,
        "verified": True,
    }


def verify_package(package_root: Path, output: Path) -> dict[str, Any]:
    manifest_path = package_root / "PACKAGE_INTEGRITY.json"
    if not manifest_path.is_file():
        raise GateError("PACKAGE_INTEGRITY.json is missing", 21)
    manifest = load_json(manifest_path)
    rows = []
    for record in manifest.get("files", []):
        path = package_root / Path(record["path"])
        rows.append(
            verify_exact_file(
                path,
                int(record["size_bytes"]),
                record["sha256"],
                f"C3H package file {record['path']}",
            )
        )
    result = {"verified": True, "file_count": len(rows), "files": rows}
    write_json(output / "package_verification.json", result)
    return result


def verify_c3g_evidence(root: Path, package_root: Path, output: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = load_json(package_root / "EXPECTED_C3G_BINDING.json")
    base = (root / Path(binding["c3g_relative_output"])).resolve(strict=True)
    evidence_path = base / "evidence_integrity.json"
    if sha256_file(evidence_path) != binding["evidence_integrity_sha256"]:
        raise GateError("Exact C3G evidence-integrity manifest hash changed", 21)
    evidence = load_json(evidence_path)
    verified_rows = []
    for row in evidence.get("files", []):
        path = base / Path(row["file"])
        verified_rows.append(
            verify_exact_file(
                path,
                int(row["size_bytes"]),
                row["sha256"],
                f"C3G evidence {row['file']}",
            )
        )
    for name, hash_key in (
        ("classification.json", "classification_sha256"),
        ("receipt.json", "receipt_sha256"),
        ("C3H_FIRST_START_CONTRACT.json", "contract_sha256"),
    ):
        if sha256_file(base / name) != binding[hash_key]:
            raise GateError(f"Exact C3G {name} hash changed", 21)
    classification = load_json(base / "classification.json")
    if not classification.get("verified") or classification.get("mode") != binding["expected_classification"]:
        raise GateError("C3G success classification is not exact", 21)
    receipt = load_json(base / "receipt.json")
    if not receipt.get("verified") or receipt.get("comfyui_launched"):
        raise GateError("C3G receipt does not preserve the reviewed no-launch state", 21)
    contract = load_json(base / "C3H_FIRST_START_CONTRACT.json")
    if not contract.get("verified") or not contract.get("requires_fresh_explicit_operator_approval"):
        raise GateError("C3G C3H contract is not valid", 21)
    result = {
        "verified": True,
        "base": str(base),
        "evidence_file_count": len(verified_rows),
        "classification": classification.get("mode"),
        "contract": contract,
    }
    write_json(output / "c3g_input_verification.json", result)
    return binding, result


def verify_live_files(root: Path, binding: dict[str, Any], output: Path, phase: str) -> dict[str, Any]:
    rows = []
    for row in binding["integrated_files"]:
        rows.append(
            verify_exact_file(
                root / Path(row["relative_path"]),
                int(row["size_bytes"]),
                row["sha256"],
                f"integrated live file {row['relative_path']}",
            )
        )
    for row in binding["protected_files"]:
        rows.append(
            verify_exact_file(
                root / Path(row["path"]),
                int(row["size_bytes"]),
                row["sha256"],
                f"protected file {row['path']}",
            )
        )
    result = {"verified": True, "phase": phase, "file_count": len(rows), "files": rows}
    write_json(output / f"live_and_protected_{phase}.json", result)
    return result


def verify_target(root: Path, binding: dict[str, Any], output: Path, phase: str) -> dict[str, Any]:
    inventory_binding = binding["c3e_inventory"]
    inventory_path = root / Path(inventory_binding["relative_path"])
    verify_exact_file(
        inventory_path,
        int(inventory_binding["size_bytes"]),
        inventory_binding["sha256"],
        "sealed C3E installed inventory",
    )
    inventory = load_json(inventory_path)
    target = root / Path(binding["isolated_target"]["relative_path"])
    if not target.is_dir() or target.is_symlink():
        raise GateError("Committed isolated target is missing or unsafe", 21)

    rows = inventory.get("files", [])
    expected_by_key: dict[str, dict[str, Any]] = {}
    duplicate_keys = []
    missing = []
    mismatches = []
    symlinks = []
    aggregate = hashlib.sha256()
    actual_bytes = 0

    for row in rows:
        rel = str(row["path"])
        key = rel.casefold()
        if key in expected_by_key:
            duplicate_keys.append(rel)
        expected_by_key[key] = row
        path = target / Path(rel)
        aggregate.update(rel.casefold().encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(int(row["size_bytes"])).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(str(row["sha256"]).encode("ascii"))
        aggregate.update(b"\n")
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
        actual_hash = sha256_file(path)
        actual_bytes += size
        if size != int(row["size_bytes"]) or actual_hash != row["sha256"]:
            mismatches.append(
                {
                    "path": rel,
                    "expected_size": int(row["size_bytes"]),
                    "actual_size": size,
                    "expected_sha256": row["sha256"],
                    "actual_sha256": actual_hash,
                }
            )

    unexpected = []
    actual_count = 0
    for path in target.rglob("*"):
        if path.is_symlink():
            rel = path.relative_to(target).as_posix()
            if rel not in symlinks:
                symlinks.append(rel)
            continue
        if path.is_file():
            actual_count += 1
            rel = path.relative_to(target).as_posix()
            if rel.casefold() not in expected_by_key:
                unexpected.append(rel)

    expected = binding["isolated_target"]
    actual_tree = aggregate.hexdigest()
    verified = not (duplicate_keys or missing or mismatches or unexpected or symlinks)
    verified = verified and actual_count == int(expected["file_count"])
    verified = verified and actual_bytes == int(expected["total_bytes"])
    verified = verified and actual_tree == expected["tree_sha256"]
    result = {
        "verified": verified,
        "phase": phase,
        "target": str(target),
        "expected_file_count": int(expected["file_count"]),
        "actual_file_count": actual_count,
        "expected_bytes": int(expected["total_bytes"]),
        "actual_bytes": actual_bytes,
        "expected_tree_sha256": expected["tree_sha256"],
        "actual_tree_sha256": actual_tree,
        "duplicate_casefold_paths": duplicate_keys,
        "missing": missing,
        "unexpected": unexpected,
        "mismatches": mismatches,
        "symlinks": symlinks,
    }
    write_json(output / f"isolated_target_{phase}.json", result)
    if not verified:
        raise GateError(f"Isolated target failed exact {phase} verification", 21 if phase == "before" else 26)
    return result


def source_snapshot(comfy_root: Path) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for path in comfy_root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        rel_parts = path.relative_to(comfy_root).parts
        if rel_parts and rel_parts[0].casefold() in SOURCE_SCAN_EXCLUDED_TOP_LEVEL:
            continue
        rel = path.relative_to(comfy_root).as_posix()
        snapshot[rel.casefold()] = {
            "path": rel,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    return snapshot


def compare_snapshots(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> dict[str, Any]:
    added = [after[k] for k in sorted(after.keys() - before.keys())]
    removed = [before[k] for k in sorted(before.keys() - after.keys())]
    changed = []
    for key in sorted(before.keys() & after.keys()):
        if before[key]["size_bytes"] != after[key]["size_bytes"] or before[key]["sha256"] != after[key]["sha256"]:
            changed.append({"before": before[key], "after": after[key]})
    return {"verified": not (added or removed or changed), "added": added, "removed": removed, "changed": changed}


def operational_snapshot(comfy_root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for top in sorted(ALLOWED_OPERATIONAL_TOP_LEVEL):
        base = comfy_root / top
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            rel = path.relative_to(comfy_root).as_posix()
            stat = path.stat()
            row: dict[str, Any] = {
                "path": rel,
                "size_bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
            if stat.st_size <= 32 * 1024 * 1024:
                row["sha256"] = sha256_file(path)
            result[rel.casefold()] = row
    return result


def operational_changes(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> dict[str, Any]:
    added = [after[k] for k in sorted(after.keys() - before.keys())]
    removed = [before[k] for k in sorted(before.keys() - after.keys())]
    modified = []
    for key in sorted(before.keys() & after.keys()):
        if before[key] != after[key]:
            modified.append({"before": before[key], "after": after[key]})
    return {"allowed": True, "added": added, "removed": removed, "modified": modified}


def port_open(host: str = "127.0.0.1", port: int = 8188, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def http_probe(url: str, timeout: float = 2.0) -> dict[str, Any]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, headers={"User-Agent": "FOXAI-C3H/1.0"})
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(1024 * 1024)
            return {
                "ok": int(response.status) == 200,
                "status": int(response.status),
                "url": url,
                "content_type": response.headers.get("Content-Type", ""),
                "body_size": len(body),
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "json": _try_json(body),
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "url": url,
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }


def _try_json(body: bytes) -> Any:
    try:
        value = json.loads(body.decode("utf-8"))
        if isinstance(value, dict):
            return value
    except Exception:
        return None
    return None


def process_tcp_rows(pid: int) -> list[dict[str, str]]:
    if os.name != "nt":
        return []
    completed = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    rows = []
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        try:
            row_pid = int(parts[-1])
        except ValueError:
            continue
        if row_pid != pid:
            continue
        rows.append(
            {
                "protocol": parts[0],
                "local": parts[1],
                "remote": parts[2],
                "state": parts[3],
                "pid": str(row_pid),
            }
        )
    return rows


def endpoint_host(endpoint: str) -> str:
    value = endpoint.strip()
    if value.startswith("["):
        return value[1:].split("]", 1)[0]
    if ":" in value:
        return value.rsplit(":", 1)[0]
    return value


def network_violations(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    violations = []
    for row in rows:
        local_host = endpoint_host(row["local"]).casefold()
        remote_host = endpoint_host(row["remote"]).casefold()
        state = row["state"].upper()
        allowed_local = local_host in {"127.0.0.1", "::1"}
        if state == "LISTENING":
            if not allowed_local or not row["local"].endswith(":8188"):
                violations.append(row)
            continue
        if remote_host not in {"127.0.0.1", "::1", "0.0.0.0", "*"}:
            violations.append(row)
    return violations


def tail_text(path: Path, max_bytes: int = 65536) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as handle:
        size = path.stat().st_size
        if size > max_bytes:
            handle.seek(size - max_bytes)
        return handle.read().decode("utf-8", errors="replace")


def stop_process(proc: subprocess.Popen[bytes], output: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "requested": True,
        "pid": proc.pid,
        "method": None,
        "returncode": proc.poll(),
        "graceful": False,
        "forced": False,
    }
    if proc.poll() is not None:
        result.update({"method": "already_exited", "returncode": proc.returncode, "graceful": True})
        write_json(output / "stop_receipt.json", result)
        return result
    try:
        if os.name == "nt" and hasattr(signal, "CTRL_BREAK_EVENT"):
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            result["method"] = "CTRL_BREAK_EVENT"
        else:
            proc.terminate()
            result["method"] = "terminate"
        proc.wait(timeout=GRACEFUL_STOP_TIMEOUT)
        result["returncode"] = proc.returncode
        result["graceful"] = result["method"] == "CTRL_BREAK_EVENT"
    except subprocess.TimeoutExpired:
        result["forced"] = True
        result["method"] = f"{result.get('method')}_then_terminate"
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            result["method"] += "_then_kill"
            proc.kill()
            proc.wait(timeout=10)
        result["returncode"] = proc.returncode
    except Exception as exc:
        result["signal_error"] = f"{type(exc).__name__}: {exc}"
        result["forced"] = True
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=10)
            except Exception as kill_exc:
                result["kill_error"] = f"{type(kill_exc).__name__}: {kill_exc}"
        result["returncode"] = proc.poll()
    write_json(output / "stop_receipt.json", result)
    return result


def wait_port_closed(timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        if not port_open(timeout=0.25):
            return {"closed": True, "elapsed_seconds": round(time.monotonic() - started, 3)}
        time.sleep(0.5)
    return {"closed": False, "elapsed_seconds": round(time.monotonic() - started, 3)}


def create_review_zip(output: Path) -> Path:
    review = output / "UPLOAD_THIS_C3H_REVIEW.zip"
    if review.exists():
        review.unlink()
    with zipfile.ZipFile(review, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file() and path != review:
                archive.write(path, path.relative_to(output).as_posix())
    return review


def write_evidence_integrity(output: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name in {"evidence_integrity.json", "UPLOAD_THIS_C3H_REVIEW.zip"}:
            continue
        rows.append(
            {
                "file": path.relative_to(output).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    result = {"verified": True, "file_count": len(rows), "files": rows}
    write_json(output / "evidence_integrity.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--package-root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve(strict=True)
    package_root = Path(args.package_root).resolve(strict=True)
    output = package_root / "START_OUTPUT" / run_id()
    output.mkdir(parents=True, exist_ok=False)
    started_utc = utc_now()
    started_clock = time.monotonic()
    proc: subprocess.Popen[bytes] | None = None
    stdout_handle = None
    stderr_handle = None
    exit_code = 20
    blocking: list[str] = []
    health: dict[str, Any] = {}
    network_samples: list[dict[str, Any]] = []
    stop_result: dict[str, Any] | None = None
    source_before: dict[str, dict[str, Any]] = {}
    operational_before: dict[str, dict[str, Any]] = {}
    binding: dict[str, Any] | None = None
    comfy_root: Path | None = None

    try:
        print(f"[C3H] Evidence folder: {output}", flush=True)
        verify_package(package_root, output)
        approval = load_json(package_root / "OPERATOR_APPROVAL.json")
        if not approval.get("approved") or approval.get("leave_running"):
            raise GateError("C3H operator approval is absent or requests leaving the process running", 21)
        write_json(output / "operator_approval.json", approval)
        binding, _ = verify_c3g_evidence(root, package_root, output)
        verify_live_files(root, binding, output, "before")
        verify_target(root, binding, output, "before")

        comfy_root = root / "ComfyUI"
        source_before = source_snapshot(comfy_root)
        operational_before = operational_snapshot(comfy_root)
        write_json(
            output / "source_boundary_before.json",
            {
                "file_count": len(source_before),
                "total_bytes": sum(row["size_bytes"] for row in source_before.values()),
            },
        )

        if port_open():
            raise GateError("Port 127.0.0.1:8188 is already in use; C3H did not launch", 22)

        launch = binding["launch"]
        portable = (root / Path(launch["portable_python"])).resolve(strict=True)
        activator = (root / Path(launch["activator"])).resolve(strict=True)
        main_py = (root / Path(launch["main_py"])).resolve(strict=True)
        command = [
            str(portable), "-I", "-B", "-S", str(activator),
            "--root", str(root), "--", *launch["arguments"],
        ]
        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        env.update(
            {
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1",
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "DO_NOT_TRACK": "1",
                "SETUPTOOLS_USE_DISTUTILS": "local",
                "NO_PROXY": "127.0.0.1,localhost,::1",
                "no_proxy": "127.0.0.1,localhost,::1",
            }
        )
        stdout_path = output / "comfyui_stdout.log"
        stderr_path = output / "comfyui_stderr.log"
        stdout_handle = stdout_path.open("wb")
        stderr_handle = stderr_path.open("wb")
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        print("[C3H] Starting isolated ComfyUI on 127.0.0.1:8188...", flush=True)
        proc = subprocess.Popen(
            command,
            cwd=str(main_py.parent),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=creationflags,
        )
        write_json(
            output / "launch_receipt.json",
            {
                "started_utc": utc_now(),
                "pid": proc.pid,
                "command": command,
                "cwd": str(main_py.parent),
                "portable_python_sha256": sha256_file(portable),
                "activator_sha256": sha256_file(activator),
                "main_py_sha256": sha256_file(main_py),
                "cpu": True,
                "custom_nodes_disabled": True,
                "listen": "127.0.0.1",
                "port": 8188,
                "external_network_permitted": False,
            },
        )

        deadline = time.monotonic() + STARTUP_TIMEOUT
        health_successes: list[dict[str, Any]] = []
        last_notice = 0.0
        while time.monotonic() < deadline:
            returncode = proc.poll()
            now = time.monotonic()
            if returncode is not None:
                raise GateError(f"ComfyUI exited before health verification with code {returncode}", 23)
            if now - last_notice >= 5:
                print(
                    f"[WAIT] ComfyUI PID {proc.pid}; stdout {stdout_path.stat().st_size} bytes; stderr {stderr_path.stat().st_size} bytes",
                    flush=True,
                )
                rows = process_tcp_rows(proc.pid)
                violations = network_violations(rows)
                network_samples.append({"utc": utc_now(), "rows": rows, "violations": violations})
                if violations:
                    raise GateError("ComfyUI opened a non-loopback or unexpected TCP endpoint", 24)
                last_notice = now

            root_probe = http_probe(launch["health_url"])
            if root_probe.get("ok"):
                stats_probe = http_probe(launch["system_stats_url"])
                health_successes.append(
                    {"utc": utc_now(), "root": root_probe, "system_stats": stats_probe}
                )
                if len(health_successes) == 1:
                    print("[HEALTH] Local ComfyUI endpoint returned HTTP 200.", flush=True)
                if len(health_successes) >= 3:
                    first = datetime.fromisoformat(health_successes[0]["utc"])
                    last = datetime.fromisoformat(health_successes[-1]["utc"])
                    if (last - first).total_seconds() >= HEALTH_STABILITY_SECONDS:
                        health = {
                            "verified": True,
                            "success_count": len(health_successes),
                            "stability_seconds": (last - first).total_seconds(),
                            "checks": health_successes,
                        }
                        break
            time.sleep(2)
        else:
            raise GateError("ComfyUI did not become healthy before the 300-second timeout", 23)

        if not health:
            raise GateError("ComfyUI health did not remain stable", 23)
        write_json(output / "health_verification.json", health)
        write_json(
            output / "network_observation.json",
            {
                "loopback_only_required": True,
                "sample_count": len(network_samples),
                "violations": [v for sample in network_samples for v in sample["violations"]],
                "samples": network_samples,
            },
        )

        final_rows = process_tcp_rows(proc.pid)
        final_violations = network_violations(final_rows)
        if final_violations:
            raise GateError("ComfyUI opened a non-loopback or unexpected TCP endpoint", 24)
        if os.name == "nt" and not any(
            row["state"].upper() == "LISTENING"
            and endpoint_host(row["local"]).casefold() == "127.0.0.1"
            and row["local"].endswith(":8188")
            for row in final_rows
        ):
            raise GateError("ComfyUI health responded but exact localhost listener ownership was not verified", 24)
        network_samples.append({"utc": utc_now(), "rows": final_rows, "violations": final_violations, "final": True})

        if proc.poll() is not None:
            raise GateError(f"ComfyUI exited unexpectedly after health verification with code {proc.returncode}", 23)
        print("[C3H] Health gate passed. Stopping ComfyUI now...", flush=True)
        stop_result = stop_process(proc, output)
        if stop_result.get("forced") or not stop_result.get("graceful"):
            raise GateError("ComfyUI required a forced or non-graceful stop", 25)
        port_result = wait_port_closed(PORT_CLOSE_TIMEOUT)
        write_json(output / "port_close_verification.json", port_result)
        if not port_result["closed"]:
            raise GateError("Port 8188 remained open after the controlled stop", 25)

        if stdout_handle:
            stdout_handle.flush()
        if stderr_handle:
            stderr_handle.flush()
        write_json(
            output / "log_summary.json",
            {
                "stdout_size_bytes": stdout_path.stat().st_size,
                "stderr_size_bytes": stderr_path.stat().st_size,
                "stdout_tail": tail_text(stdout_path),
                "stderr_tail": tail_text(stderr_path),
            },
        )

        verify_live_files(root, binding, output, "after")
        verify_target(root, binding, output, "after")
        source_after = source_snapshot(comfy_root)
        source_comparison = compare_snapshots(source_before, source_after)
        write_json(output / "source_boundary_comparison.json", source_comparison)
        if not source_comparison["verified"]:
            raise GateError("ComfyUI changed files outside approved operational directories", 26)
        operational_after = operational_snapshot(comfy_root)
        write_json(
            output / "operational_runtime_changes.json",
            operational_changes(operational_before, operational_after),
        )

        exit_code = 0
        classification = {
            "mode": SUCCESS_CLASSIFICATION,
            "verified": True,
            "blocking_findings": [],
            "comfyui_started": True,
            "health_verified": True,
            "comfyui_stopped": True,
            "left_running": False,
            "listen": "127.0.0.1:8188",
            "custom_nodes_disabled": True,
            "external_network_observed": False,
            "launcher_change": False,
            "runtime_target_change": False,
            "next_gate": "C3I normal-enable and retention review requires fresh approval",
        }
    except GateError as exc:
        exit_code = exc.code
        blocking.append(str(exc))
        classification = {
            "mode": BLOCKED_CLASSIFICATION,
            "verified": False,
            "exit_code": exit_code,
            "blocking_findings": blocking,
            "comfyui_started": proc is not None,
            "health_verified": bool(health),
            "comfyui_stopped": proc is None or proc.poll() is not None,
            "left_running": proc is not None and proc.poll() is None,
            "launcher_change": False,
            "runtime_target_change": False,
        }
    except Exception as exc:
        exit_code = 29
        blocking.append(f"{type(exc).__name__}: {exc}")
        (output / "unexpected_traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
        classification = {
            "mode": BLOCKED_CLASSIFICATION,
            "verified": False,
            "exit_code": exit_code,
            "blocking_findings": blocking,
            "comfyui_started": proc is not None,
            "health_verified": bool(health),
            "comfyui_stopped": proc is None or proc.poll() is not None,
            "left_running": proc is not None and proc.poll() is None,
            "launcher_change": False,
            "runtime_target_change": False,
        }
    finally:
        if proc is not None and proc.poll() is None:
            emergency = stop_process(proc, output)
            stop_result = emergency
            classification["comfyui_stopped"] = proc.poll() is not None
            classification["left_running"] = proc.poll() is None
            if proc.poll() is None:
                classification["verified"] = False
                classification["mode"] = BLOCKED_CLASSIFICATION
                blocking.append("Emergency cleanup could not stop the ComfyUI process")
                exit_code = 30
        if stdout_handle:
            stdout_handle.close()
        if stderr_handle:
            stderr_handle.close()
        if output.exists():
            if network_samples and not (output / "network_observation.json").exists():
                try:
                    write_json(
                        output / "network_observation.json",
                        {
                            "loopback_only_required": True,
                            "sample_count": len(network_samples),
                            "violations": [v for sample in network_samples for v in sample.get("violations", [])],
                            "samples": network_samples,
                        },
                    )
                except Exception:
                    pass
            if proc is not None and proc.poll() is not None and binding is not None:
                postcheck_issues: list[str] = []
                try:
                    if not (output / "live_and_protected_after.json").exists():
                        verify_live_files(root, binding, output, "after")
                except Exception as exc:
                    postcheck_issues.append(f"live/protected: {type(exc).__name__}: {exc}")
                try:
                    if not (output / "isolated_target_after.json").exists():
                        verify_target(root, binding, output, "after")
                except Exception as exc:
                    postcheck_issues.append(f"isolated target: {type(exc).__name__}: {exc}")
                try:
                    if comfy_root is not None and source_before and not (output / "source_boundary_comparison.json").exists():
                        source_after = source_snapshot(comfy_root)
                        comparison = compare_snapshots(source_before, source_after)
                        write_json(output / "source_boundary_comparison.json", comparison)
                        if not comparison["verified"]:
                            postcheck_issues.append("source boundary changed outside approved operational directories")
                    if comfy_root is not None and operational_before and not (output / "operational_runtime_changes.json").exists():
                        write_json(
                            output / "operational_runtime_changes.json",
                            operational_changes(operational_before, operational_snapshot(comfy_root)),
                        )
                except Exception as exc:
                    postcheck_issues.append(f"source/operational: {type(exc).__name__}: {exc}")
                if postcheck_issues:
                    write_json(output / "emergency_postcheck.json", {"verified": False, "issues": postcheck_issues})
                    blocking.extend(postcheck_issues)
                    classification["verified"] = False
                    classification["mode"] = BLOCKED_CLASSIFICATION
                    if exit_code == 0:
                        exit_code = 26
            try:
                port_result_final = wait_port_closed(2.0)
                if not (output / "port_close_verification.json").exists():
                    write_json(output / "port_close_verification.json", port_result_final)
                if not port_result_final["closed"]:
                    blocking.append("Port 8188 remained open at final evidence sealing")
                    classification["verified"] = False
                    classification["mode"] = BLOCKED_CLASSIFICATION
                    classification["left_running"] = True
                    if exit_code == 0:
                        exit_code = 30
            except Exception:
                pass
            try:
                if (output / "comfyui_stdout.log").exists() and not (output / "log_summary.json").exists():
                    write_json(
                        output / "log_summary.json",
                        {
                            "stdout_size_bytes": (output / "comfyui_stdout.log").stat().st_size,
                            "stderr_size_bytes": (output / "comfyui_stderr.log").stat().st_size if (output / "comfyui_stderr.log").exists() else 0,
                            "stdout_tail": tail_text(output / "comfyui_stdout.log"),
                            "stderr_tail": tail_text(output / "comfyui_stderr.log"),
                        },
                    )
            except Exception:
                pass
            classification["blocking_findings"] = blocking
            write_json(output / "classification.json", classification)
            receipt = {
                "action": "foxai_usbc3h_controlled_first_start",
                "state": "verified_stopped" if exit_code == 0 else "blocked_fail_closed",
                "started": started_utc,
                "completed": utc_now(),
                "elapsed_seconds": round(time.monotonic() - started_clock, 3),
                "verified": exit_code == 0,
                "classification": classification["mode"],
                "exit_code": exit_code,
                "root": str(root),
                "output": str(output),
                "pid": proc.pid if proc else None,
                "process_returncode": proc.poll() if proc else None,
                "health_verified": bool(health),
                "stop_receipt": stop_result,
                "left_running": proc is not None and proc.poll() is None,
                "launcher_change": False,
                "package_install": False,
                "package_uninstall": False,
                "external_network_access": False,
                "loopback_health_access": bool(health),
            }
            write_json(output / "receipt.json", receipt)
            report = [
                "# FOXAI USB C3H — Controlled First Start",
                "",
                f"- Classification: `{classification['mode']}`",
                f"- Verified: `{exit_code == 0}`",
                f"- ComfyUI started: `{classification.get('comfyui_started')}`",
                f"- Health verified: `{classification.get('health_verified')}`",
                f"- ComfyUI stopped: `{classification.get('comfyui_stopped')}`",
                f"- Left running: `{classification.get('left_running')}`",
                f"- Exit code: `{exit_code}`",
                "",
                "## Blocking findings",
                "",
                *([f"- {item}" for item in blocking] or ["None"]),
            ]
            (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
            write_evidence_integrity(output)
            review = create_review_zip(output)
            print(f"[C3H] Review package: {review}", flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
