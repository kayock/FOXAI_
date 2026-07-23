from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_PREFIX = "foxai.agent_fox.technical_core.v1b1a"
PROJECT_ROOT = Path("Z:\\FOXAI")
HISTORICAL_LOADED_MISSION = "ENG-20260722-051940-8477D9"
HISTORICAL_LOADED_DIR = (
    PROJECT_ROOT
    / "System"
    / "EngineeringWorkshop"
    / "missions"
    / f"{HISTORICAL_LOADED_MISSION}_V1B0_R2_PC_AND_FOXAI_BASELINE"
)
OUTPUT_NAMES = (
    "MINIMAL_LOAD_RESOURCE_SNAPSHOT.json",
    "MINIMAL_LOAD_PROCESS_SUMMARY.json",
    "MINIMAL_LOAD_QUALIFICATION.json",
    "MINIMAL_LOAD_CAPTURE_RECEIPT.json",
)
OUTPUT_CEILING_BYTES = 8 * 1024 * 1024
KNOWN_PORTS = (8080, 8188, 8765)
MAX_PROCESS_ROWS = 500
TOP_PROCESS_COUNT = 15
POWERSHELL_TIMEOUT_SECONDS = 60
KNOWN_GOOD_FILES = {
    "Z:\\FOXAI\\core\\foxai_web.py": "d7bf0a2042d55ef7f0a5869556015e42c7427e7ff88636b28e1795f3adf7b952",
    "Z:\\FOXAI\\ui\\main_window.py": "a9c5bb86878e5f0cd27d221dbb32688b337e6026073a4b66d83339e0aef294a3",
    "Z:\\FOXAI\\System\\AgentFoxTechnicalCore\\self_knowledge_chat_adapter_v1.py": "a80a9047e0eebd9ac87fe4d656c565bc6534563bb3c97e1ad9b59823a36804f7",
    "Z:\\FOXAI\\System\\AgentFoxTechnicalCore\\webui_self_knowledge_integration_v1.py": "765983b563f8495138c9670849de5c4703f4735a0ddc9324efd6580606fc517b",
    "Z:\\FOXAI\\System\\AgentFoxTechnicalCore\\desktop_self_knowledge_integration_v1.py": "e420706136b4902d82d8dbf1fecc64ae70fb8bc639106db41033545f8c196c30",
    "Z:\\FOXAI\\System\\AgentFoxTechnicalCore\\pc_foxai_baseline_v1.py": "8c3af6d6f8d5a21a03fbd5c97eabd58280718a195c65f51a2b9201ff84ec798b",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(kind: str, value: Any) -> str:
    material = canonical_bytes({"kind": kind, "value": value})
    return f"{kind.upper()}-{sha256_bytes(material)[:16].upper()}"


def _profile_context() -> tuple[tuple[str, ...], tuple[str, ...]]:
    roots: set[str] = set()
    for key in ("USERPROFILE", "HOME"):
        value = os.environ.get(key)
        if value:
            normalized = value.rstrip("\\/")
            if len(normalized) >= 3:
                roots.add(normalized)
    names: set[str] = set()
    for key in ("USERNAME", "USER"):
        value = os.environ.get(key)
        if value and len(value) >= 2:
            names.add(value)
    return (
        tuple(sorted(roots, key=len, reverse=True)),
        tuple(sorted(names, key=len, reverse=True)),
    )


PROFILE_ROOTS, PROFILE_USERNAMES = _profile_context()


def _profile_root_variants(root: str) -> tuple[str, ...]:
    variants = {root, root.replace("\\", "/"), root.replace("/", "\\")}
    return tuple(sorted((value for value in variants if value), key=len, reverse=True))


def _profile_process_name_path(path: tuple[Any, ...]) -> bool:
    if not path:
        return False
    return str(path[-1]) in {"name", "process_name", "owning_process_name"}


def _replace_literal_ci(value: str, literal: str, replacement: str) -> str:
    if not literal:
        return value
    return re.sub(re.escape(literal), lambda _match: replacement, value, flags=re.IGNORECASE)


def _sanitize_profile_string(
    value: str,
    path: tuple[Any, ...],
    roots: tuple[str, ...],
    usernames: tuple[str, ...],
) -> str:
    result = value
    for root in roots:
        for variant in _profile_root_variants(root):
            result = _replace_literal_ci(result, variant, "<REDACTED_PROFILE_ROOT>")

    result = re.sub(
        r"(?i)([A-Za-z]:[\\/]+Users[\\/]+)([^\\/\s\"']+)",
        lambda match: match.group(1) + "<REDACTED_PROFILE>",
        result,
    )

    process_name_field = _profile_process_name_path(path)
    for username in usernames:
        if result.casefold() == username.casefold():
            result = "<REDACTED_PROFILE_NAME>"
            continue
        if process_name_field:
            continue
        pattern = rf"(?i)(?<![A-Za-z0-9_]){re.escape(username)}(?![A-Za-z0-9_])"
        result = re.sub(pattern, "<REDACTED_PROFILE_NAME>", result)
    return result


def _sanitize_profile_data(
    value: Any,
    path: tuple[Any, ...] = (),
    *,
    roots: tuple[str, ...] | None = None,
    usernames: tuple[str, ...] | None = None,
) -> Any:
    active_roots = PROFILE_ROOTS if roots is None else roots
    active_usernames = PROFILE_USERNAMES if usernames is None else usernames
    if isinstance(value, dict):
        return {
            key: _sanitize_profile_data(
                item,
                (*path, key),
                roots=active_roots,
                usernames=active_usernames,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _sanitize_profile_data(
                item,
                (*path, index),
                roots=active_roots,
                usernames=active_usernames,
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return tuple(
            _sanitize_profile_data(
                item,
                (*path, index),
                roots=active_roots,
                usernames=active_usernames,
            )
            for index, item in enumerate(value)
        )
    if isinstance(value, str):
        return _sanitize_profile_string(value, path, active_roots, active_usernames)
    return value


def _json_field_path(path: tuple[Any, ...]) -> str:
    result = "$"
    for part in path:
        if isinstance(part, int):
            result += f"[{part}]"
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(part)):
            result += "." + str(part)
        else:
            result += "[" + json.dumps(str(part), ensure_ascii=False) + "]"
    return result


def _iter_string_values(
    value: Any,
    path: tuple[Any, ...] = (),
) -> Iterable[tuple[tuple[Any, ...], str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_string_values(item, (*path, key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _iter_string_values(item, (*path, index))
    elif isinstance(value, str):
        yield path, value


def _profile_violation_category(
    value: str,
    path: tuple[Any, ...],
    roots: tuple[str, ...],
    usernames: tuple[str, ...],
) -> str | None:
    for root in roots:
        for variant in _profile_root_variants(root):
            if variant.casefold() in value.casefold():
                return "profile_root"
    if re.search(
        r"(?i)[A-Za-z]:[\\/]+Users[\\/]+(?!<REDACTED_PROFILE(?:_ROOT|_NAME)?>)[^\\/\s\"']+",
        value,
    ):
        return "windows_profile_path"
    process_name_field = _profile_process_name_path(path)
    for username in usernames:
        if value.casefold() == username.casefold():
            return "exact_profile_name"
        if process_name_field:
            continue
        pattern = rf"(?i)(?<![A-Za-z0-9_]){re.escape(username)}(?![A-Za-z0-9_])"
        if re.search(pattern, value):
            return "profile_name_token"
    return None


def _assert_profile_safe(
    value: Any,
    *,
    roots: tuple[str, ...] | None = None,
    usernames: tuple[str, ...] | None = None,
) -> None:
    active_roots = PROFILE_ROOTS if roots is None else roots
    active_usernames = PROFILE_USERNAMES if usernames is None else usernames
    for path, text in _iter_string_values(value):
        category = _profile_violation_category(
            text,
            path,
            active_roots,
            active_usernames,
        )
        if category:
            raise AssertionError(
                f"profile redaction validation failed at {_json_field_path(path)}: {category}"
            )


def redact_text(value: Any) -> Any:
    return _sanitize_profile_data(value, ("diagnostic",))

def _powershell_executable() -> str | None:
    for candidate in (
        shutil.which("powershell.exe"),
        shutil.which("pwsh.exe"),
        shutil.which("powershell"),
        shutil.which("pwsh"),
    ):
        if candidate:
            return candidate
    return None


def run_powershell_json(script: str) -> tuple[Any | None, str | None, dict[str, Any]]:
    executable = _powershell_executable()
    audit = {
        "method": "bounded_read_only_powershell_collector",
        "executable_name": Path(executable).name if executable else None,
        "script_sha256": sha256_bytes(script.encode("utf-8")),
        "timeout_seconds": POWERSHELL_TIMEOUT_SECONDS,
        "command_line_output_recorded": False,
        "network_connection_initiated": False,
    }
    if not executable:
        return None, "PowerShell collector unavailable", audit
    prefix = (
        "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);"
        "$OutputEncoding=[System.Text.UTF8Encoding]::new($false);"
        "$ProgressPreference='SilentlyContinue';$ErrorActionPreference='Stop';"
    )
    try:
        completed = subprocess.run(
            [
                executable,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                prefix + script,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=POWERSHELL_TIMEOUT_SECONDS,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        return None, f"PowerShell collector failed to start: {type(exc).__name__}", audit
    if completed.returncode != 0:
        tail = (completed.stderr or "").strip().splitlines()[-1:] or ["collector returned nonzero"]
        return None, redact_text(tail[0])[:300], audit
    output = (completed.stdout or "").strip().lstrip("\ufeff")
    if not output:
        return None, "PowerShell collector returned no JSON", audit
    try:
        return json.loads(output), None, audit
    except Exception as exc:
        return None, f"PowerShell JSON parse failed: {type(exc).__name__}", audit


def _windows_snapshot() -> tuple[dict[str, Any] | None, str | None, dict[str, Any]]:
    script = r'''
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$page = @(Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue | Select-Object AllocatedBaseSize,CurrentUsage,PeakUsage)
$perf = $null
try { $perf = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory -ErrorAction Stop } catch { $perf = $null }
$processes = @(Get-CimInstance Win32_Process | Select-Object Name,ProcessId,ParentProcessId,WorkingSetSize,PrivatePageCount,KernelModeTime,UserModeTime,ExecutablePath)
$listeners = @()
try {
  $listeners = @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -in 8080,8188,8765 } | Select-Object LocalAddress,LocalPort,OwningProcess,State)
} catch { $listeners = @() }
[pscustomobject]@{
  os = [pscustomobject]@{
    last_boot_up_time = if ($os.LastBootUpTime) { $os.LastBootUpTime.ToUniversalTime().ToString('o') } else { $null }
    total_visible_memory_kib = $os.TotalVisibleMemorySize
    free_physical_memory_kib = $os.FreePhysicalMemory
    total_virtual_memory_kib = $os.TotalVirtualMemorySize
    free_virtual_memory_kib = $os.FreeVirtualMemory
    architecture = $os.OSArchitecture
  }
  computer_system = [pscustomobject]@{
    total_physical_memory_bytes = $cs.TotalPhysicalMemory
    logical_processor_count = $cs.NumberOfLogicalProcessors
  }
  performance_memory = if ($perf) { [pscustomobject]@{ committed_bytes = $perf.CommittedBytes; commit_limit = $perf.CommitLimit } } else { $null }
  page_files = $page
  process_count = $processes.Count
  processes = $processes
  listeners = $listeners
} | ConvertTo-Json -Depth 6 -Compress
'''
    return run_powershell_json(script)


def _filesystem_for_root(root: str) -> str | None:
    if os.name != "nt":
        return None
    volume_name = ctypes.create_unicode_buffer(261)
    fs_name = ctypes.create_unicode_buffer(261)
    serial = ctypes.c_uint32()
    max_component = ctypes.c_uint32()
    flags = ctypes.c_uint32()
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root),
        volume_name,
        len(volume_name),
        ctypes.byref(serial),
        ctypes.byref(max_component),
        ctypes.byref(flags),
        fs_name,
        len(fs_name),
    )
    return fs_name.value if ok else None


def _drive_rows(collected_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for root in ("C:\\", "Z:\\", "S:\\"):
        try:
            usage = shutil.disk_usage(Path(root))
            rows.append(
                {
                    "drive_id": stable_id("drive", root),
                    "drive_root": root,
                    "availability_status": "available",
                    "collection_method": "shutil.disk_usage and read-only GetVolumeInformationW",
                    "collected_at": collected_at,
                    "filesystem": _filesystem_for_root(root),
                    "total_bytes": int(usage.total),
                    "free_bytes": int(usage.free),
                    "used_bytes": int(usage.used),
                    "free_percent": round((usage.free / usage.total) * 100.0, 2) if usage.total else None,
                    "volume_serial_recorded": False,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "drive_id": stable_id("drive", root),
                    "drive_root": root,
                    "availability_status": "unavailable_with_reason",
                    "collection_method": "shutil.disk_usage and read-only GetVolumeInformationW",
                    "collected_at": collected_at,
                    "unavailable_reason": type(exc).__name__,
                    "volume_serial_recorded": False,
                }
            )
    return rows


def _classify_executable(path: str | None) -> tuple[str, bool, str | None]:
    if not path:
        return "unavailable", False, None
    normalized = path.replace("/", "\\")
    lower = normalized.lower()
    foxai = lower.startswith("z:\\foxai\\")
    hint = None
    if foxai:
        if "\\comfyui\\" in lower or lower.endswith("\\comfyui"):
            hint = "comfyui"
        elif "\\runtime\\desktop\\python\\" in lower:
            hint = "foxai_portable_python"
        elif "\\models\\" in lower or "llama" in Path(lower).name:
            hint = "model_runtime"
        return "foxai_workspace", True, hint
    if lower.startswith("c:\\windows\\"):
        return "windows_system", False, None
    if lower.startswith("c:\\program files") or lower.startswith("c:\\program files (x86)"):
        return "program_files", False, None
    if lower.startswith("c:\\users\\"):
        return "user_profile_redacted", False, None
    return "other_local", False, None


def _normalize_processes(raw_rows: Any, collected_at: str) -> list[dict[str, Any]]:
    if raw_rows is None:
        return []
    if isinstance(raw_rows, dict):
        raw_rows = [raw_rows]
    rows: list[dict[str, Any]] = []
    for item in list(raw_rows)[:MAX_PROCESS_ROWS]:
        if not isinstance(item, dict):
            continue
        try:
            pid = int(item.get("ProcessId") or 0)
            ppid = int(item.get("ParentProcessId") or 0)
        except Exception:
            continue
        name = str(item.get("Name") or "unknown")
        classification, foxai_path, hint = _classify_executable(item.get("ExecutablePath"))
        kernel = int(item.get("KernelModeTime") or 0)
        user = int(item.get("UserModeTime") or 0)
        rows.append(
            {
                "process_id": stable_id("process", {"pid": pid, "name": name.lower()}),
                "name": name,
                "pid": pid,
                "parent_pid": ppid,
                "working_set_bytes": int(item.get("WorkingSetSize") or 0),
                "private_memory_bytes": int(item.get("PrivatePageCount") or 0),
                "cpu_time_seconds": round((kernel + user) / 10_000_000.0, 3),
                "executable_classification": classification,
                "foxai_workspace_executable": foxai_path,
                "foxai_component_hint": hint,
                "full_executable_path_recorded": False,
                "process_arguments_recorded": False,
                "availability_status": "available",
                "collection_method": "Get-CimInstance Win32_Process without CommandLine",
                "collected_at": collected_at,
            }
        )
    return sorted(rows, key=lambda row: (row["pid"], row["name"].lower()))


def _normalize_listeners(
    raw_rows: Any,
    process_by_pid: dict[int, dict[str, Any]],
    collected_at: str,
) -> list[dict[str, Any]]:
    if raw_rows is None:
        return []
    if isinstance(raw_rows, dict):
        raw_rows = [raw_rows]
    rows: list[dict[str, Any]] = []
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        port = int(item.get("LocalPort") or 0)
        if port not in KNOWN_PORTS:
            continue
        pid = int(item.get("OwningProcess") or 0)
        proc = process_by_pid.get(pid, {})
        address = str(item.get("LocalAddress") or "")
        rows.append(
            {
                "listener_id": stable_id("listener", {"port": port, "pid": pid, "address": address}),
                "protocol": "TCP",
                "local_port": port,
                "local_address": address,
                "loopback_only": address in {"127.0.0.1", "::1"},
                "owning_pid": pid,
                "owning_process_name": proc.get("name") or "unknown",
                "owning_process_foxai_workspace": bool(proc.get("foxai_workspace_executable")),
                "availability_status": "available",
                "collection_method": "Get-NetTCPConnection local listener enumeration",
                "collected_at": collected_at,
                "remote_connection_attempted": False,
            }
        )
    return sorted(rows, key=lambda row: (row["local_port"], row["owning_pid"], row["local_address"]))


def _ancestor_pids(current_pid: int, process_by_pid: dict[int, dict[str, Any]]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    pid = current_pid
    for _ in range(12):
        row = process_by_pid.get(pid)
        if not row:
            break
        parent = int(row.get("parent_pid") or 0)
        if parent <= 0 or parent in seen:
            break
        seen.add(parent)
        result.append(parent)
        pid = parent
    return result


def _model_like_name(name: str) -> bool:
    lower = name.lower()
    return (
        lower == "llama-server.exe"
        or "llamafile" in lower
        or lower.startswith("koboldcpp")
        or lower in {"text-generation-webui.exe", "lmstudio.exe"}
    )


def _qualify(
    processes: list[dict[str, Any]],
    listeners: list[dict[str, Any]],
    collected_at: str,
) -> dict[str, Any]:
    process_by_pid = {int(row["pid"]): row for row in processes}
    current_pid = os.getpid()
    ancestors = _ancestor_pids(current_pid, process_by_pid)
    webui_pids = {int(row["owning_pid"]) for row in listeners if int(row["local_port"]) == 8765}
    allowed_pids = {current_pid, *ancestors, *webui_pids}
    blockers: list[dict[str, Any]] = []

    for row in processes:
        name = str(row["name"])
        lower = name.lower()
        pid = int(row["pid"])
        foxai_path = bool(row["foxai_workspace_executable"])
        hint = row.get("foxai_component_hint")
        reason = None
        if _model_like_name(name):
            reason = "model_runtime_active"
        elif lower == "pythonw.exe" and foxai_path:
            reason = "foxai_desktop_gui_active"
        elif hint == "comfyui":
            reason = "comfyui_process_active"
        elif lower in {"python.exe", "pythonw.exe"} and foxai_path and pid not in allowed_pids:
            reason = "additional_foxai_python_workload_active"
        if reason:
            blockers.append(
                {
                    "blocker_id": stable_id("blocker", {"reason": reason, "pid": pid, "name": lower}),
                    "reason": reason,
                    "process_name": name,
                    "pid": pid,
                    "working_set_bytes": row["working_set_bytes"],
                    "executable_classification": row["executable_classification"],
                }
            )

    for listener in listeners:
        if int(listener["local_port"]) == 8188:
            blockers.append(
                {
                    "blocker_id": stable_id(
                        "blocker",
                        {"reason": "comfyui_listener_active", "pid": listener["owning_pid"], "port": 8188},
                    ),
                    "reason": "comfyui_listener_active",
                    "process_name": listener["owning_process_name"],
                    "pid": listener["owning_pid"],
                    "local_port": 8188,
                }
            )

    unique = {row["blocker_id"]: row for row in blockers}
    blockers = sorted(unique.values(), key=lambda row: (row["reason"], int(row.get("pid") or 0)))
    status = "qualified_minimal_load" if not blockers else "minimal_load_precondition_not_met"
    return {
        "qualification_id": stable_id("qualification", {"status": status, "blockers": blockers}),
        "status": status,
        "collected_at": collected_at,
        "collection_method": "bounded process and known-listener evaluation",
        "criteria": {
            "engineering_workshop_allowed": True,
            "webui_command_surface_allowed": True,
            "llama_server_required_absent": True,
            "foxai_desktop_required_absent": True,
            "comfyui_required_absent": True,
            "other_foxai_workload_required_absent": True,
        },
        "current_collector_pid": current_pid,
        "allowed_process_pids": sorted(allowed_pids),
        "webui_listener_pids": sorted(webui_pids),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "automatic_process_changes_performed": False,
    }


def _workspace_hashes(collected_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_path, expected in KNOWN_GOOD_FILES.items():
        path = Path(raw_path)
        if path.is_file():
            actual = sha256_file(path)
            rows.append(
                {
                    "file_id": stable_id("file", raw_path.lower()),
                    "path": raw_path,
                    "availability_status": "available",
                    "collection_method": "bounded SHA-256 file read",
                    "collected_at": collected_at,
                    "size_bytes": path.stat().st_size,
                    "actual_sha256": actual,
                    "expected_known_good_sha256": expected,
                    "sha256_matches_expected": actual == expected,
                }
            )
        else:
            rows.append(
                {
                    "file_id": stable_id("file", raw_path.lower()),
                    "path": raw_path,
                    "availability_status": "unavailable_with_reason",
                    "collection_method": "bounded path existence check",
                    "collected_at": collected_at,
                    "unavailable_reason": "file not present",
                    "expected_known_good_sha256": expected,
                }
            )
    return rows


def _memory_snapshot(raw: dict[str, Any], collected_at: str) -> dict[str, Any]:
    os_row = raw.get("os") or {}
    cs = raw.get("computer_system") or {}
    perf = raw.get("performance_memory") or {}
    page_files = raw.get("page_files") or []
    if isinstance(page_files, dict):
        page_files = [page_files]
    total_kib = int(os_row.get("total_visible_memory_kib") or 0)
    free_kib = int(os_row.get("free_physical_memory_kib") or 0)
    total_bytes = int(cs.get("total_physical_memory_bytes") or (total_kib * 1024))
    available_bytes = free_kib * 1024
    load_percent = round(((total_bytes - available_bytes) / total_bytes) * 100.0, 2) if total_bytes else None
    allocated_mib = sum(int(row.get("AllocatedBaseSize") or 0) for row in page_files if isinstance(row, dict))
    usage_mib = sum(int(row.get("CurrentUsage") or 0) for row in page_files if isinstance(row, dict))
    peak_mib = sum(int(row.get("PeakUsage") or 0) for row in page_files if isinstance(row, dict))
    committed = perf.get("committed_bytes") if isinstance(perf, dict) else None
    limit = perf.get("commit_limit") if isinstance(perf, dict) else None
    return {
        "memory_record_id": stable_id("memory", {"total": total_bytes, "available": available_bytes, "page": allocated_mib}),
        "availability_status": "available" if total_bytes else "collection_incomplete",
        "collection_method": "Win32_OperatingSystem, Win32_ComputerSystem, Win32_PageFileUsage, PerfOS Memory",
        "collected_at": collected_at,
        "total_physical_memory_bytes": total_bytes,
        "available_physical_memory_bytes": available_bytes,
        "physical_memory_in_use_bytes": max(total_bytes - available_bytes, 0),
        "memory_load_percent": load_percent,
        "committed_bytes": int(committed) if committed is not None else None,
        "commit_limit_bytes": int(limit) if limit is not None else None,
        "page_file_allocated_mib": allocated_mib,
        "page_file_current_usage_mib": usage_mib,
        "page_file_peak_usage_mib": peak_mib,
        "page_file_details_recorded_without_paths": True,
    }


def _historical_reference(collected_at: str) -> dict[str, Any]:
    expected = [
        "PC_BASELINE_OBSERVATIONS.json",
        "PC_BASELINE_RECEIPT.json",
        "PROCESS_RESOURCE_BASELINE.json",
        "HOST_AND_WINDOWS_BASELINE.json",
    ]
    existing = [name for name in expected if (HISTORICAL_LOADED_DIR / name).is_file()]
    return {
        "mission_id": HISTORICAL_LOADED_MISSION,
        "evidence_directory": str(HISTORICAL_LOADED_DIR),
        "availability_status": "available" if len(existing) == len(expected) else "partially_available",
        "collection_method": "bounded existence check only",
        "collected_at": collected_at,
        "expected_reference_files": expected,
        "available_reference_files": existing,
        "historical_evidence_modified": False,
        "historical_evidence_reinterpreted": False,
    }


def _privacy_assertions(payloads: Iterable[bytes]) -> None:
    materialized = list(payloads)
    for payload in materialized:
        if b"\r" in payload:
            raise AssertionError("carriage-return byte in canonical evidence")
        document = json.loads(payload.decode("utf-8"))
        _assert_profile_safe(document)

    joined = b"\n".join(materialized)
    lower = joined.lower()
    forbidden = (
        b'"process_arguments"',
        b'"full_process_arguments"',
        b'"environment_values"',
        b'"product_key"',
        b'"mac_address"',
        b'"motherboard_uuid"',
        b'"drive_serial"',
        b'"account_identifier"',
        b'"api_key"',
        b'"token_value"',
    )
    for token in forbidden:
        if token in lower:
            raise AssertionError(f"forbidden evidence token: {token!r}")
    if b"k:\\" in lower or b"k:/" in lower:
        raise AssertionError("rollback drive path leaked into evidence")

def collect(mission_id: str, output_dir: Path) -> dict[str, Any]:
    collected_at = utc_now()
    raw, error, collector_audit = _windows_snapshot()
    if error or not isinstance(raw, dict):
        result = {
            "status": "collection_incomplete",
            "mission_id": mission_id,
            "collected_at": collected_at,
            "reason": error or "Windows snapshot unavailable",
            "comparison_evidence_written": False,
        }
        print(json.dumps(result, sort_keys=True))
        return result

    processes = _normalize_processes(raw.get("processes"), collected_at)
    process_by_pid = {int(row["pid"]): row for row in processes}
    listeners = _normalize_listeners(raw.get("listeners"), process_by_pid, collected_at)
    qualification = _qualify(processes, listeners, collected_at)
    if qualification["status"] != "qualified_minimal_load":
        result = {
            "status": qualification["status"],
            "mission_id": mission_id,
            "collected_at": collected_at,
            "blocker_count": qualification["blocker_count"],
            "blockers": qualification["blockers"],
            "comparison_evidence_written": False,
            "automatic_process_changes_performed": False,
        }
        print(json.dumps(result, sort_keys=True))
        return result

    if output_dir.exists():
        raise FileExistsError(f"output directory already exists: {output_dir}")

    memory = _memory_snapshot(raw, collected_at)
    drives = _drive_rows(collected_at)
    workspace_files = _workspace_hashes(collected_at)
    if memory["availability_status"] != "available" or not processes:
        result = {
            "status": "collection_incomplete",
            "mission_id": mission_id,
            "collected_at": collected_at,
            "reason": "required memory or process evidence unavailable",
            "comparison_evidence_written": False,
        }
        print(json.dumps(result, sort_keys=True))
        return result

    top = sorted(
        processes,
        key=lambda row: (-int(row["working_set_bytes"]), row["name"].lower(), row["pid"]),
    )[:TOP_PROCESS_COUNT]
    foxai_processes = [row for row in processes if row["foxai_workspace_executable"]]
    names = [row["name"].lower() for row in processes]
    listener_by_port = {
        str(port): [row for row in listeners if row["local_port"] == port]
        for port in KNOWN_PORTS
    }

    resource_snapshot = {
        "schema": f"{SCHEMA_PREFIX}.minimal_load_resource_snapshot.v1",
        "mission_id": mission_id,
        "collected_at": collected_at,
        "snapshot_id": stable_id(
            "minimal_snapshot",
            {"mission": mission_id, "boot": (raw.get("os") or {}).get("last_boot_up_time")},
        ),
        "qualification_status": qualification["status"],
        "host": {
            "availability_status": "available",
            "collection_method": "Win32_OperatingSystem and Python platform",
            "collected_at": collected_at,
            "architecture": (raw.get("os") or {}).get("architecture") or platform.machine(),
            "boot_time_utc": (raw.get("os") or {}).get("last_boot_up_time"),
            "uptime_seconds": None,
        },
        "memory": memory,
        "drives": drives,
        "known_local_listeners": listener_by_port,
        "active_workspace": {
            "workspace_id": stable_id("workspace", "Z:\\FOXAI"),
            "root": "Z:\\FOXAI",
            "availability_status": "available" if PROJECT_ROOT.is_dir() else "unavailable_with_reason",
            "collection_method": "bounded path check and SHA-256 verification",
            "collected_at": collected_at,
            "verified_files": workspace_files,
            "full_tree_hash_performed": False,
        },
        "historical_loaded_state_reference": _historical_reference(collected_at),
        "derived_calculations": [
            "memory_load_percent",
            "physical_memory_in_use_bytes",
            "drive_free_percent",
        ],
        "direct_observations_separated_from_derived": True,
    }
    boot_text = resource_snapshot["host"]["boot_time_utc"]
    if boot_text:
        try:
            boot = datetime.fromisoformat(str(boot_text).replace("Z", "+00:00"))
            now = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
            resource_snapshot["host"]["uptime_seconds"] = max(int((now - boot).total_seconds()), 0)
        except Exception:
            resource_snapshot["host"]["uptime_seconds"] = None

    process_summary = {
        "schema": f"{SCHEMA_PREFIX}.minimal_load_process_summary.v1",
        "mission_id": mission_id,
        "collected_at": collected_at,
        "qualification_status": qualification["status"],
        "collection_method": "Get-CimInstance Win32_Process without process arguments",
        "process_count": int(raw.get("process_count") or len(processes)),
        "process_table_count": len(processes),
        "bounded_process_limit": MAX_PROCESS_ROWS,
        "process_table": processes,
        "top_working_set_processes": top,
        "top_working_set_process_count": len(top),
        "foxai_workspace_process_count": len(foxai_processes),
        "foxai_workspace_processes": foxai_processes,
        "workload_presence": {
            "llama_server_present": "llama-server.exe" in names,
            "foxai_desktop_pythonw_present": any(
                row["name"].lower() == "pythonw.exe" and row["foxai_workspace_executable"]
                for row in processes
            ),
            "comfyui_listener_8188_present": bool(listener_by_port["8188"]),
            "model_listener_8080_present": bool(listener_by_port["8080"]),
            "webui_listener_8765_present": bool(listener_by_port["8765"]),
        },
        "process_arguments_recorded": False,
        "full_executable_paths_recorded": False,
    }

    qualification_doc = {
        "schema": f"{SCHEMA_PREFIX}.minimal_load_qualification.v1",
        "mission_id": mission_id,
        **qualification,
        "known_port_evidence": listener_by_port,
        "required_absence_confirmed": {
            "llama_server": not process_summary["workload_presence"]["llama_server_present"],
            "foxai_desktop": not process_summary["workload_presence"]["foxai_desktop_pythonw_present"],
            "comfyui": not process_summary["workload_presence"]["comfyui_listener_8188_present"],
        },
        "comparison_evidence_written_only_after_qualification": True,
    }

    resource_snapshot = _sanitize_profile_data(resource_snapshot)
    process_summary = _sanitize_profile_data(process_summary)
    qualification_doc = _sanitize_profile_data(qualification_doc)
    provisional = [
        canonical_bytes(resource_snapshot),
        canonical_bytes(process_summary),
        canonical_bytes(qualification_doc),
    ]
    _privacy_assertions(provisional)
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, data in zip(OUTPUT_NAMES[:3], provisional):
        (output_dir / name).write_bytes(data)

    output_rows = []
    for name in OUTPUT_NAMES[:3]:
        data = (output_dir / name).read_bytes()
        output_rows.append({"name": name, "size_bytes": len(data), "sha256": sha256_bytes(data)})

    receipt = {
        "schema": f"{SCHEMA_PREFIX}.minimal_load_capture_receipt.v1",
        "mission_id": mission_id,
        "status": "captured_and_verified",
        "qualification_status": qualification["status"],
        "collected_at": collected_at,
        "output_count": 4,
        "outputs_before_receipt": output_rows,
        "deterministic_utf8_lf_serialization": True,
        "privacy_validation_passed": True,
        "profile_redaction_mode": "structured_recursive_field_aware",
        "prior_failure_classification": "profile_marker_raw_substring_false_positive",
        "collector_behavior_changed": False,
        "collection_audit": [collector_audit],
        "read_only_collection": True,
        "automatic_process_changes_performed": False,
        "services_changed": False,
        "startup_items_changed": False,
        "registry_writes": False,
        "network_connections_initiated": False,
        "remote_hosts_probed": False,
        "packet_capture_performed": False,
        "models_loaded": False,
        "comfyui_launched": False,
        "gui_launched": False,
        "live_foxai_modules_imported": False,
        "historical_v1b0_evidence_modified": False,
        "rollback_drive_k_accessed": False,
        "personal_documents_inspected": False,
        "process_arguments_recorded": False,
        "environment_variable_values_recorded": False,
        "persistent_device_identifiers_recorded": False,
    }
    receipt = _sanitize_profile_data(receipt)
    receipt_bytes = canonical_bytes(receipt)
    _privacy_assertions([*provisional, receipt_bytes])
    (output_dir / OUTPUT_NAMES[3]).write_bytes(receipt_bytes)

    files = sorted(output_dir.iterdir(), key=lambda path: path.name)
    if [path.name for path in files] != sorted(OUTPUT_NAMES):
        raise AssertionError("unexpected minimal-load output set")
    payloads = [path.read_bytes() for path in files]
    _privacy_assertions(payloads)
    if sum(len(data) for data in payloads) >= OUTPUT_CEILING_BYTES:
        raise AssertionError("minimal-load evidence exceeds output ceiling")

    result = {
        "status": "qualified_minimal_load_captured",
        "mission_id": mission_id,
        "output_count": 4,
        "process_count": len(processes),
        "memory_load_percent": memory["memory_load_percent"],
        "page_file_current_usage_mib": memory["page_file_current_usage_mib"],
        "output_dir": str(output_dir),
    }
    print(json.dumps(result, sort_keys=True))
    return result


def self_test() -> dict[str, Any]:
    assert len(OUTPUT_NAMES) == 4
    sample = {
        "schema": "self_test",
        "process_table": [
            {
                "name": "python.exe",
                "pid": 100,
                "parent_pid": 10,
                "working_set_bytes": 123,
                "private_memory_bytes": 45,
                "cpu_time_seconds": 1.5,
                "executable_classification": "foxai_workspace",
                "foxai_workspace_executable": True,
                "foxai_component_hint": "foxai_portable_python",
                "full_executable_path_recorded": False,
                "process_arguments_recorded": False,
                "availability_status": "available",
                "collection_method": "fixture",
                "collected_at": "2026-01-01T00:00:00Z",
                "process_id": "PROCESS-TEST",
            }
        ],
        "rollback_drive_k_accessed": False,
    }
    sample = _sanitize_profile_data(sample)
    payload = canonical_bytes(sample)
    _privacy_assertions([payload])
    assert b"\r" not in payload

    fixture_roots = (r"C:\Users\Ann",)
    fixture_names = ("Ann",)
    profile_fixture = {
        "full_root": r"C:\Users\Ann\AppData\Local\FOXAI",
        "slash_path": "C:/Users/Ann/Documents/example.txt",
        "bare_name": "Ann",
        "standalone_token": "owner Ann requested the capture",
        "harmless_alphanumeric": "JoannTools.exe",
        "harmless_identifier": "planner_annex_v1",
        "process_table": [
            {"name": "AnnTool.exe"},
            {"name": "Ann"},
        ],
    }
    sanitized_fixture = _sanitize_profile_data(
        profile_fixture,
        roots=fixture_roots,
        usernames=fixture_names,
    )
    _assert_profile_safe(
        sanitized_fixture,
        roots=fixture_roots,
        usernames=fixture_names,
    )
    assert "Ann" not in sanitized_fixture["full_root"]
    assert "Ann" not in sanitized_fixture["slash_path"]
    assert sanitized_fixture["bare_name"] == "<REDACTED_PROFILE_NAME>"
    assert "<REDACTED_PROFILE_NAME>" in sanitized_fixture["standalone_token"]
    assert sanitized_fixture["harmless_alphanumeric"] == "JoannTools.exe"
    assert sanitized_fixture["harmless_identifier"] == "planner_annex_v1"
    assert sanitized_fixture["process_table"][0]["name"] == "AnnTool.exe"
    assert sanitized_fixture["process_table"][1]["name"] == "<REDACTED_PROFILE_NAME>"

    try:
        _assert_profile_safe(
            {"nested": {"path": r"C:\Users\Ann\secret.txt"}},
            roots=fixture_roots,
            usernames=fixture_names,
        )
    except AssertionError as exc:
        diagnostic = str(exc)
        assert "$.nested.path" in diagnostic
        assert "profile_root" in diagnostic
        assert "Ann" not in diagnostic
    else:
        raise AssertionError("unsanitized profile fixture was not rejected")
    current = {
        "name": "python.exe",
        "pid": os.getpid(),
        "parent_pid": 0,
        "working_set_bytes": 1,
        "private_memory_bytes": 1,
        "cpu_time_seconds": 0.1,
        "executable_classification": "foxai_workspace",
        "foxai_workspace_executable": True,
        "foxai_component_hint": "foxai_portable_python",
    }
    comfy = {
        "name": "python.exe",
        "pid": 200,
        "parent_pid": 0,
        "working_set_bytes": 1,
        "private_memory_bytes": 1,
        "cpu_time_seconds": 0.1,
        "executable_classification": "foxai_workspace",
        "foxai_workspace_executable": True,
        "foxai_component_hint": "comfyui",
    }
    listeners = [
        {
            "local_port": 8188,
            "owning_pid": 200,
            "owning_process_name": "python.exe",
            "local_address": "127.0.0.1",
        }
    ]
    blocked = _qualify([current, comfy], listeners, "2026-01-01T00:00:00Z")
    assert blocked["status"] == "minimal_load_precondition_not_met"
    clean = _qualify([current], [], "2026-01-01T00:00:00Z")
    assert clean["status"] == "qualified_minimal_load"
    assert stable_id("x", {"a": 1}) == stable_id("x", {"a": 1})
    return {
        "status": "ok",
        "output_count": 4,
        "canonical_lf_only": True,
        "privacy_redaction": True,
        "structured_profile_redaction": True,
        "harmless_profile_substring_accepted": True,
        "profile_diagnostic_field_path_only": True,
        "stable_ids": True,
        "precondition_blocking": True,
        "qualified_fixture": True,
        "process_arguments_excluded": True,
        "k_path_excluded": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--mission-id", required=True)
    collect_parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if args.command == "self-test":
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    result = collect(args.mission_id, Path(args.output_dir))
    status = result.get("status")
    if status == "qualified_minimal_load_captured":
        return 0
    if status == "minimal_load_precondition_not_met":
        return 3
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
