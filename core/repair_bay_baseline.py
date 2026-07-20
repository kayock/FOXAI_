from __future__ import annotations

import base64
import ctypes
import hashlib
import html
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

BASELINE_VERSION = "3.0"
DATA_RELATIVE = Path("Reports") / "RepairBay" / "SystemBaseline"
SNAPSHOT_DIR_NAME = "Snapshots"
COMPARISON_DIR_NAME = "Comparisons"
EXPORT_DIR_NAME = "Exports"
STATE_FILE_NAME = "state.json"
SESSIONS_FILE_NAME = "sessions.json"

SENSITIVE_KEY_RE = re.compile(
    r"(?i)(password|passwd|secret|token|cookie|authorization|clipboard|environment|command[_ -]?line|arguments?)"
)
RUNTIME_NOISE_NAMES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe",
    "runtimebroker.exe", "conhost.exe", "dllhost.exe", "searchhost.exe",
    "widgetservice.exe", "webviewhost.exe", "msedgewebview2.exe",
}
READ_ONLY_POWERSHELL_MARKERS = (
    "get-ciminstance", "get-process", "get-nettcpconnection", "get-netudpendpoint",
    "get-itemproperty", "get-childitem", "get-scheduledtask", "get-authenticodesignature",
    "get-windowsoptionalfeature", "get-command", "get-item", "get-counter",
)
MUTATION_MARKERS = (
    "set-", "new-", "remove-", "enable-", "disable-", "start-", "stop-",
    "restart-", "install-", "uninstall-", "register-", "unregister-",
    "clear-", "rename-", "move-", "copy-", "invoke-webrequest", "curl ", "wget ",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(value: str, default: str = "snapshot") -> str:
    text = re.sub(r"[^A-Za-z0-9._ -]+", "", str(value or "")).strip()
    text = re.sub(r"\s+", "_", text)[:80]
    return text or default


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _atomic_json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _data_paths(root: Path) -> dict[str, Path]:
    base = Path(root) / DATA_RELATIVE
    return {
        "base": base,
        "snapshots": base / SNAPSHOT_DIR_NAME,
        "comparisons": base / COMPARISON_DIR_NAME,
        "exports": base / EXPORT_DIR_NAME,
        "state": base / STATE_FILE_NAME,
        "sessions": base / SESSIONS_FILE_NAME,
    }


def _ensure_data_dirs(root: Path) -> dict[str, Path]:
    paths = _data_paths(root)
    for key in ("base", "snapshots", "comparisons", "exports"):
        paths[key].mkdir(parents=True, exist_ok=True)
    if not paths["state"].exists():
        _atomic_json_write(paths["state"], {"schema": "foxai.repair_baseline.state.v1", "known_good_snapshot_id": ""})
    if not paths["sessions"].exists():
        _atomic_json_write(paths["sessions"], {"schema": "foxai.repair_baseline.sessions.v1", "sessions": []})
    return paths


def _safe_text(value: Any, limit: int = 1000) -> str:
    text = str(value or "").replace("\x00", "").strip()
    return text[:limit]


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _sanitize_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _safe_text(key, 160)
            if SENSITIVE_KEY_RE.search(key_text):
                continue
            clean[key_text] = _sanitize_mapping(item)
        return clean
    if isinstance(value, list):
        return [_sanitize_mapping(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_mapping(item) for item in value]
    if isinstance(value, str):
        return _safe_text(value, 4000)
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return _safe_text(value, 1000)


def _run_read_only_powershell(script: str, timeout: int = 90) -> tuple[Any, dict[str, Any]]:
    lower = script.casefold()
    mutation_hits = sorted({marker for marker in MUTATION_MARKERS if marker in lower})
    if mutation_hits:
        raise ValueError("PowerShell collector contains prohibited mutation marker(s): " + ", ".join(mutation_hits))
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    command = [
        "powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded,
    ]
    receipt = {
        "tool": "powershell.exe",
        "read_only": True,
        "network_used": False,
        "timeout_seconds": timeout,
        "allowed_markers_present": sorted({m for m in READ_ONLY_POWERSHELL_MARKERS if m in lower}),
        "mutation_markers": [],
    }
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
    except FileNotFoundError:
        receipt.update({"ok": False, "returncode": None, "message": "PowerShell was not found."})
        return None, receipt
    except subprocess.TimeoutExpired:
        receipt.update({"ok": False, "returncode": None, "message": "Read-only PowerShell collector timed out."})
        return None, receipt
    stdout = (completed.stdout or "").strip().lstrip("\ufeff")
    stderr = (completed.stderr or "").strip()
    receipt.update({
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stderr": _safe_text(stderr, 1200),
    })
    if completed.returncode != 0 or not stdout:
        return None, receipt
    try:
        return json.loads(stdout), receipt
    except Exception as exc:
        receipt.update({"ok": False, "message": f"Collector JSON could not be parsed: {type(exc).__name__}"})
        return None, receipt


def _memory_fallback() -> dict[str, Any]:
    result = {"total_bytes": 0, "available_bytes": 0, "cached_bytes": None, "committed_bytes": None}
    if os.name != "nt":
        return result
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            result.update({
                "total_bytes": int(status.ullTotalPhys),
                "available_bytes": int(status.ullAvailPhys),
                "committed_bytes": int(status.ullTotalPageFile - status.ullAvailPageFile),
            })
    except Exception:
        pass
    return result


def _uptime_seconds() -> int:
    if os.name == "nt":
        try:
            return int(ctypes.windll.kernel32.GetTickCount64() // 1000)
        except Exception:
            return 0
    try:
        return int(float(Path("/proc/uptime").read_text().split()[0]))
    except Exception:
        return 0


def _disk_inventory() -> list[dict[str, Any]]:
    disks: list[dict[str, Any]] = []
    if os.name == "nt":
        try:
            mask = int(ctypes.windll.kernel32.GetLogicalDrives())
            get_type = ctypes.windll.kernel32.GetDriveTypeW
            type_names = {2: "removable", 3: "fixed", 4: "network", 5: "optical", 6: "ramdisk"}
            for index in range(26):
                if not (mask & (1 << index)):
                    continue
                root = f"{chr(65 + index)}:\\"
                drive_type = type_names.get(int(get_type(root)), "unknown")
                if drive_type not in {"fixed", "removable"}:
                    continue
                try:
                    usage = shutil.disk_usage(root)
                    disks.append({
                        "mount": root,
                        "type": drive_type,
                        "capacity_bytes": int(usage.total),
                        "free_bytes": int(usage.free),
                    })
                except Exception as exc:
                    disks.append({"mount": root, "type": drive_type, "capacity_bytes": 0, "free_bytes": 0, "error": type(exc).__name__})
        except Exception:
            pass
    else:
        try:
            usage = shutil.disk_usage("/")
            disks.append({"mount": "/", "type": "fixed", "capacity_bytes": usage.total, "free_bytes": usage.free})
        except Exception:
            pass
    return disks


def _windows_inventory_script() -> str:
    # Read-only registry, CIM, process, networking, task, feature, and version inspection.
    return r'''
$ErrorActionPreference = 'SilentlyContinue'
function Arr($x) { if ($null -eq $x) { return @() }; return @($x) }
$services = Get-CimInstance Win32_Service | ForEach-Object {
  [pscustomobject]@{
    name=$_.Name; display_name=$_.DisplayName; state=$_.State; start_type=$_.StartMode;
    executable_path=$_.PathName; service_account=$_.StartName; process_id=[int]$_.ProcessId
  }
}
$serviceByPid = @{}
foreach($s in $services){ if($s.process_id -gt 0){ if(-not $serviceByPid.ContainsKey($s.process_id)){ $serviceByPid[$s.process_id]=@() }; $serviceByPid[$s.process_id]+=$s.name } }
$processes = Get-CimInstance Win32_Process | Sort-Object {[double]$_.WorkingSetSize} -Descending | Select-Object -First 60 | ForEach-Object {
  $sigStatus=''; $publisher=''
  if($_.ExecutablePath){
    $sig = Get-AuthenticodeSignature -FilePath $_.ExecutablePath
    if($sig){ $sigStatus=[string]$sig.Status; if($sig.SignerCertificate){$publisher=[string]$sig.SignerCertificate.Subject} }
  }
  [pscustomobject]@{
    name=$_.Name; process_id=[int]$_.ProcessId; executable_path=$_.ExecutablePath;
    working_set_bytes=[int64]$_.WorkingSetSize; private_bytes=[int64]$_.PrivatePageCount;
    cpu_time_100ns=[int64]($_.KernelModeTime + $_.UserModeTime); start_time=[string]$_.CreationDate;
    services=Arr($serviceByPid[[int]$_.ProcessId]); signature_status=$sigStatus; publisher=$publisher
  }
}
$startup=@()
$runLocations=@(
  @{Scope='CurrentUser';Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'},
  @{Scope='LocalMachine';Path='HKLM:\Software\Microsoft\Windows\CurrentVersion\Run'},
  @{Scope='LocalMachine32';Path='HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run'}
)
foreach($loc in $runLocations){
  $item=Get-ItemProperty -Path $loc.Path
  if($item){ foreach($prop in $item.PSObject.Properties){ if($prop.Name -notmatch '^PS'){ $startup += [pscustomobject]@{source='registry_run';scope=$loc.Scope;name=$prop.Name;target=[string]$prop.Value;enabled=$true} } } }
}
$startupFolders=@(
  @{Scope='CurrentUser';Path=[Environment]::GetFolderPath('Startup')},
  @{Scope='AllUsers';Path=[Environment]::GetFolderPath('CommonStartup')}
)
foreach($folder in $startupFolders){ if(Test-Path $folder.Path){ Get-ChildItem -LiteralPath $folder.Path -File | ForEach-Object { $startup += [pscustomobject]@{source='startup_folder';scope=$folder.Scope;name=$_.Name;target=$_.FullName;enabled=$true} } } }
$tasks=Get-ScheduledTask | ForEach-Object { [pscustomobject]@{path=($_.TaskPath + $_.TaskName);state=[string]$_.State;enabled=([string]$_.State -ne 'Disabled')} }
$tcp=Get-NetTCPConnection -State Listen | ForEach-Object { [pscustomobject]@{protocol='TCP';local_address=$_.LocalAddress;local_port=[int]$_.LocalPort;process_id=[int]$_.OwningProcess} }
$udp=Get-NetUDPEndpoint | ForEach-Object { [pscustomobject]@{protocol='UDP';local_address=$_.LocalAddress;local_port=[int]$_.LocalPort;process_id=[int]$_.OwningProcess} }
$uninstall=@(
  'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
$apps=Get-ItemProperty $uninstall | Where-Object {$_.DisplayName} | ForEach-Object { [pscustomobject]@{name=$_.DisplayName;version=$_.DisplayVersion;publisher=$_.Publisher;install_location=$_.InstallLocation} } | Sort-Object name,version -Unique
$features=Get-WindowsOptionalFeature -Online | Where-Object {$_.State -eq 'Enabled'} | ForEach-Object { [pscustomobject]@{name=$_.FeatureName;state=[string]$_.State} }
$commands=Get-Command python,python3,py,java,javac -All | ForEach-Object { $version=''; try {$version=$_.FileVersionInfo.FileVersion}catch{}; [pscustomobject]@{name=$_.Name;path=$_.Source;version=$version} } | Sort-Object path -Unique
$browsers=@()
foreach($path in @(
  'C:\Program Files\Google\Chrome\Application\chrome.exe',
  'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
  'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
  'C:\Program Files\Mozilla Firefox\firefox.exe'
)){ if(Test-Path $path){ $item=Get-Item -LiteralPath $path; $browsers += [pscustomobject]@{name=$item.VersionInfo.ProductName;path=$path;version=$item.VersionInfo.ProductVersion} } }
$gpu=Get-CimInstance Win32_VideoController | ForEach-Object { [pscustomobject]@{name=$_.Name;driver_version=$_.DriverVersion;status=$_.Status} }
$audio=Get-CimInstance Win32_SoundDevice | ForEach-Object { [pscustomobject]@{name=$_.Name;manufacturer=$_.Manufacturer;status=$_.Status} }
$osInfo=Get-CimInstance Win32_OperatingSystem
$cpuUsage=$null; $cacheBytes=$null
try{$cpuUsage=[math]::Round((Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples.CookedValue,1)}catch{}
try{$cacheBytes=[int64](Get-Counter '\Memory\Cache Bytes').CounterSamples.CookedValue}catch{}
$cpuInfo=Get-CimInstance Win32_Processor | Select-Object -First 1
$computer=Get-CimInstance Win32_ComputerSystem
$result=[pscustomobject]@{
  machine=[pscustomobject]@{computer_name=$env:COMPUTERNAME;os_caption=$osInfo.Caption;os_version=$osInfo.Version;architecture=$osInfo.OSArchitecture;cpu_model=$cpuInfo.Name;logical_processors=[int]$computer.NumberOfLogicalProcessors;last_boot_time=[string]$osInfo.LastBootUpTime}
  memory=[pscustomobject]@{total_bytes=[int64]$osInfo.TotalVisibleMemorySize*1024;available_bytes=[int64]$osInfo.FreePhysicalMemory*1024;cached_bytes=$cacheBytes;committed_bytes=([int64]$osInfo.TotalVirtualMemorySize-[int64]$osInfo.FreeVirtualMemory)*1024}
  cpu=[pscustomobject]@{utilization_percent=$cpuUsage}
  processes=Arr($processes);services=Arr($services);startup_entries=Arr($startup);scheduled_tasks=Arr($tasks);listeners=Arr($tcp)+Arr($udp);applications=Arr($apps);optional_features=Arr($features);runtimes=Arr($commands);browsers=Arr($browsers);gpu_drivers=Arr($gpu);audio_drivers=Arr($audio)
}
$result | ConvertTo-Json -Depth 8 -Compress
'''


def _listener_scope(address: str) -> str:
    address = str(address or "").strip().lower()
    if address in {"127.0.0.1", "::1"}:
        return "localhost"
    if address in {"0.0.0.0", "::", "*"}:
        return "all_interfaces"
    return "local_network_or_specific_interface"


def _normalize_windows_data(raw: Any) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    processes = []
    for item in raw.get("processes") or []:
        if not isinstance(item, dict):
            continue
        processes.append({
            "name": _safe_text(item.get("name"), 260),
            "process_id": _safe_int(item.get("process_id")),
            "executable_path": _safe_text(item.get("executable_path"), 1000),
            "publisher": _safe_text(item.get("publisher"), 500),
            "signature_status": _safe_text(item.get("signature_status"), 80),
            "working_set_bytes": _safe_int(item.get("working_set_bytes")),
            "private_bytes": _safe_int(item.get("private_bytes")),
            "cpu_time_seconds": round(_safe_number(item.get("cpu_time_100ns")) / 10_000_000, 3),
            "start_time": _safe_text(item.get("start_time"), 120),
            "services": sorted({_safe_text(x, 260) for x in (item.get("services") or []) if _safe_text(x)}),
        })
    services = []
    for item in raw.get("services") or []:
        if not isinstance(item, dict):
            continue
        account = _safe_text(item.get("service_account"), 300)
        account_category = "system" if account.casefold() in {"localsystem", "nt authority\\system", "localservice", "networkservice", "nt authority\\localservice", "nt authority\\networkservice"} else ("managed_or_user" if account else "unknown")
        services.append({
            "name": _safe_text(item.get("name"), 260),
            "display_name": _safe_text(item.get("display_name"), 500),
            "state": _safe_text(item.get("state"), 80),
            "start_type": _safe_text(item.get("start_type"), 80),
            "executable_path": _safe_text(item.get("executable_path"), 1000),
            "service_account_category": account_category,
            "process_id": _safe_int(item.get("process_id")),
        })
    listeners = []
    process_by_pid = {p["process_id"]: p["name"] for p in processes if p["process_id"]}
    for item in raw.get("listeners") or []:
        if not isinstance(item, dict):
            continue
        pid = _safe_int(item.get("process_id"))
        address = _safe_text(item.get("local_address"), 100)
        listeners.append({
            "protocol": _safe_text(item.get("protocol"), 10).upper(),
            "local_address": address,
            "local_port": _safe_int(item.get("local_port")),
            "process_id": pid,
            "process_name": process_by_pid.get(pid, ""),
            "scope": _listener_scope(address),
        })
    return {
        "machine": _sanitize_mapping(raw.get("machine") or {}),
        "memory": _sanitize_mapping(raw.get("memory") or {}),
        "cpu": _sanitize_mapping(raw.get("cpu") or {}),
        "processes": processes,
        "services": services,
        "startup_entries": _sanitize_mapping(raw.get("startup_entries") or []),
        "scheduled_tasks": _sanitize_mapping(raw.get("scheduled_tasks") or []),
        "listeners": listeners,
        "applications": _sanitize_mapping(raw.get("applications") or []),
        "optional_features": _sanitize_mapping(raw.get("optional_features") or []),
        "runtimes": _sanitize_mapping(raw.get("runtimes") or []),
        "browsers": _sanitize_mapping(raw.get("browsers") or []),
        "gpu_drivers": _sanitize_mapping(raw.get("gpu_drivers") or []),
        "audio_drivers": _sanitize_mapping(raw.get("audio_drivers") or []),
    }


def collect_system_snapshot(*, collector: Callable[[], dict[str, Any]] | None = None) -> dict[str, Any]:
    if collector is not None:
        supplied = _sanitize_mapping(collector())
        supplied.setdefault("collector", {})
        supplied["collector"].update({"fixture": True, "read_only": True, "network_used": False, "mutation_commands": 0})
        return supplied

    receipts: list[dict[str, Any]] = []
    warnings: list[str] = []
    windows = {}
    if os.name == "nt":
        raw, receipt = _run_read_only_powershell(_windows_inventory_script(), timeout=120)
        receipts.append(receipt)
        if raw is not None:
            windows = _normalize_windows_data(raw)
        else:
            warnings.append(receipt.get("message") or receipt.get("stderr") or "Some Windows inventory fields were unavailable.")
    memory = windows.get("memory") or _memory_fallback()
    machine = windows.get("machine") or {
        "computer_name": socket.gethostname(),
        "os_caption": platform.platform(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "cpu_model": platform.processor(),
        "logical_processors": os.cpu_count() or 0,
    }
    machine["uptime_seconds"] = _uptime_seconds()
    machine["python_platform"] = platform.platform()
    result = {
        "schema": "foxai.repair_baseline.snapshot_payload.v1",
        "version": BASELINE_VERSION,
        "captured_at": _utc_now(),
        "machine": machine,
        "resources": {
            "memory": memory,
            "cpu": {
                "model": machine.get("cpu_model") or platform.processor(),
                "logical_processors": _safe_int(machine.get("logical_processors"), os.cpu_count() or 0),
                "utilization_percent": (windows.get("cpu") or {}).get("utilization_percent"),
            },
            "disks": _disk_inventory(),
        },
        "processes": windows.get("processes") or [],
        "services": windows.get("services") or [],
        "startup_entries": windows.get("startup_entries") or [],
        "scheduled_tasks": windows.get("scheduled_tasks") or [],
        "listeners": windows.get("listeners") or [],
        "applications": windows.get("applications") or [],
        "components": {
            "optional_features": windows.get("optional_features") or [],
            "runtimes": windows.get("runtimes") or [],
            "browsers": windows.get("browsers") or [],
            "gpu_drivers": windows.get("gpu_drivers") or [],
            "audio_drivers": windows.get("audio_drivers") or [],
        },
        "collector": {
            "read_only": True,
            "network_used": False,
            "commands": receipts,
            "mutation_commands": 0,
            "warnings": [w for w in warnings if w],
            "secret_fields_excluded": True,
        },
    }
    return _sanitize_mapping(result)


def capture_snapshot(
    root: Path,
    *,
    name: str,
    note: str = "",
    origin: str = "manual",
    collector: Callable[[], dict[str, Any]] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    paths = _ensure_data_dirs(Path(root))
    payload = collect_system_snapshot(collector=collector)
    snapshot_id = "SNP-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8].upper()
    snapshot = {
        "schema": "foxai.repair_baseline.snapshot.v1",
        "snapshot_id": snapshot_id,
        "name": _safe_text(name, 160) or "Unnamed Snapshot",
        "note": _safe_text(note, 2000),
        "origin": _safe_text(origin, 80) or "manual",
        "session_id": _safe_text(session_id, 80),
        "created_at": _utc_now(),
        "payload": payload,
        "payload_sha256": _sha256_bytes(_json_bytes(payload)),
        "read_only_capture": True,
        "system_modified": False,
        "network_used": False,
    }
    filename = f"{snapshot_id}_{_slug(snapshot['name'])}.json"
    path = paths["snapshots"] / filename
    _atomic_json_write(path, snapshot)
    return {"ok": True, "message": f"Snapshot captured: {snapshot['name']}", "snapshot": _snapshot_summary(snapshot, path), "path": str(path)}


def _snapshot_summary(snapshot: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    payload = snapshot.get("payload") or {}
    resources = payload.get("resources") or {}
    return {
        "snapshot_id": snapshot.get("snapshot_id", ""),
        "name": snapshot.get("name", ""),
        "note": snapshot.get("note", ""),
        "origin": snapshot.get("origin", ""),
        "session_id": snapshot.get("session_id", ""),
        "created_at": snapshot.get("created_at", ""),
        "machine_name": ((payload.get("machine") or {}).get("computer_name") or ""),
        "process_count": len(payload.get("processes") or []),
        "service_count": len(payload.get("services") or []),
        "startup_count": len(payload.get("startup_entries") or []),
        "application_count": len(payload.get("applications") or []),
        "listener_count": len(payload.get("listeners") or []),
        "available_memory_bytes": _safe_int((((resources.get("memory") or {}).get("available_bytes")))),
        "path": str(path or ""),
        "payload_sha256": snapshot.get("payload_sha256", ""),
    }


def list_snapshots(root: Path) -> dict[str, Any]:
    paths = _ensure_data_dirs(Path(root))
    state = _read_json(paths["state"], {})
    items = []
    for path in sorted(paths["snapshots"].glob("*.json"), reverse=True):
        snapshot = _read_json(path, None)
        if not isinstance(snapshot, dict) or not snapshot.get("snapshot_id"):
            continue
        summary = _snapshot_summary(snapshot, path)
        summary["known_good"] = snapshot.get("snapshot_id") == state.get("known_good_snapshot_id")
        items.append(summary)
    sessions = _read_json(paths["sessions"], {"sessions": []}).get("sessions") or []
    return {
        "ok": True,
        "snapshots": items,
        "known_good_snapshot_id": state.get("known_good_snapshot_id", ""),
        "sessions": sessions,
        "data_path": str(paths["base"]),
        "read_only_system": True,
    }


def _load_snapshot(root: Path, snapshot_id: str) -> tuple[dict[str, Any], Path]:
    paths = _ensure_data_dirs(Path(root))
    snapshot_id = _safe_text(snapshot_id, 100)
    for path in paths["snapshots"].glob(f"{snapshot_id}_*.json"):
        snapshot = _read_json(path, None)
        if isinstance(snapshot, dict) and snapshot.get("snapshot_id") == snapshot_id:
            return snapshot, path
    raise FileNotFoundError(f"Snapshot was not found: {snapshot_id}")


def mark_known_good(root: Path, snapshot_id: str, *, confirm: bool) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "message": "Explicit confirmation is required before changing the known-good baseline."}
    snapshot, _ = _load_snapshot(root, snapshot_id)
    paths = _ensure_data_dirs(Path(root))
    state = _read_json(paths["state"], {})
    state.update({
        "schema": "foxai.repair_baseline.state.v1",
        "known_good_snapshot_id": snapshot_id,
        "known_good_name": snapshot.get("name", ""),
        "updated_at": _utc_now(),
    })
    _atomic_json_write(paths["state"], state)
    return {"ok": True, "message": f"Known-good baseline set to {snapshot.get('name') or snapshot_id}.", "state": state}


def _identity(item: dict[str, Any], fields: Iterable[str]) -> str:
    return "|".join(_safe_text(item.get(field), 1000).casefold() for field in fields)


def _map_by(items: list[dict[str, Any]], fields: Iterable[str]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = _identity(item, fields)
        if key.strip("|"):
            result[key] = item
    return result


def _diff_items(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    *,
    identity_fields: tuple[str, ...],
    compare_fields: tuple[str, ...],
    category: str,
) -> list[dict[str, Any]]:
    bmap = _map_by(before, identity_fields)
    amap = _map_by(after, identity_fields)
    changes: list[dict[str, Any]] = []
    for key in sorted(set(amap) - set(bmap)):
        item = amap[key]
        changes.append(_change(category, "Added", item, None, item))
    for key in sorted(set(bmap) - set(amap)):
        item = bmap[key]
        changes.append(_change(category, "Removed", item, item, None))
    for key in sorted(set(bmap) & set(amap)):
        old, new = bmap[key], amap[key]
        changed = {field: {"before": old.get(field), "after": new.get(field)} for field in compare_fields if old.get(field) != new.get(field)}
        if changed:
            changes.append(_change(category, "Changed", new, old, new, details=changed))
    return changes


def _change(category: str, action: str, item: dict[str, Any], before: Any, after: Any, details: Any = None) -> dict[str, Any]:
    name = item.get("display_name") or item.get("name") or item.get("path") or item.get("local_port") or "Item"
    classification = "Review Suggested"
    evidence = details if details is not None else {"before": before, "after": after}
    if category == "processes":
        proc_name = _safe_text(item.get("name"), 260).casefold()
        classification = "Runtime Noise" if proc_name in RUNTIME_NOISE_NAMES else "Observation"
    elif category in {"resources"}:
        classification = "Observation"
    elif category in {"applications", "startup_entries", "listeners", "services", "scheduled_tasks", "components"}:
        classification = "Significant Change" if action in {"Added", "Removed", "Enabled", "Disabled"} else "Review Suggested"
    return {
        "category": category,
        "action": action,
        "name": _safe_text(name, 500),
        "classification": classification,
        "evidence": _sanitize_mapping(evidence),
    }


def _resource_changes(before: dict[str, Any], after: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    deltas: dict[str, Any] = {}
    bmem = (((before.get("resources") or {}).get("memory") or {}))
    amem = (((after.get("resources") or {}).get("memory") or {}))
    for key in ("available_bytes", "committed_bytes", "cached_bytes"):
        bv, av = bmem.get(key), amem.get(key)
        if bv is None or av is None:
            continue
        delta = _safe_int(av) - _safe_int(bv)
        deltas[f"memory_{key}_delta"] = delta
        if delta:
            changes.append({
                "category": "resources", "action": "Increased" if delta > 0 else "Decreased",
                "name": key.replace("_", " ").title(), "classification": "Runtime Noise",
                "evidence": {"before": bv, "after": av, "delta": delta},
            })
    bdisks = _map_by(((before.get("resources") or {}).get("disks") or []), ("mount",))
    adisks = _map_by(((after.get("resources") or {}).get("disks") or []), ("mount",))
    disk_deltas = {}
    for key in sorted(set(bdisks) & set(adisks)):
        delta = _safe_int(adisks[key].get("free_bytes")) - _safe_int(bdisks[key].get("free_bytes"))
        if delta:
            mount = adisks[key].get("mount")
            disk_deltas[str(mount)] = delta
            changes.append({
                "category": "resources", "action": "Increased" if delta > 0 else "Decreased",
                "name": f"Free disk space {mount}", "classification": "Observation",
                "evidence": {"before": bdisks[key].get("free_bytes"), "after": adisks[key].get("free_bytes"), "delta": delta},
            })
    deltas["disk_free_bytes_delta"] = disk_deltas
    return changes, deltas


def compare_snapshots(root: Path, before_id: str, after_id: str, *, save: bool = True) -> dict[str, Any]:
    before_doc, _ = _load_snapshot(root, before_id)
    after_doc, _ = _load_snapshot(root, after_id)
    before = before_doc.get("payload") or {}
    after = after_doc.get("payload") or {}
    changes: list[dict[str, Any]] = []
    changes += _diff_items(before.get("applications") or [], after.get("applications") or [], identity_fields=("name", "version", "publisher"), compare_fields=("version", "publisher", "install_location"), category="applications")
    changes += _diff_items(before.get("services") or [], after.get("services") or [], identity_fields=("name",), compare_fields=("state", "start_type", "executable_path", "service_account_category"), category="services")
    # Add explicit Started/Stopped/Enabled/Disabled service semantics.
    for change in changes:
        if change["category"] != "services" or change["action"] != "Changed":
            continue
        fields = change.get("evidence") or {}
        state = fields.get("state") or {}
        start_type = fields.get("start_type") or {}
        if state:
            old, new = str(state.get("before", "")).casefold(), str(state.get("after", "")).casefold()
            if old != "running" and new == "running": change["action"] = "Started"
            elif old == "running" and new != "running": change["action"] = "Stopped"
        if start_type:
            old, new = str(start_type.get("before", "")).casefold(), str(start_type.get("after", "")).casefold()
            if old == "disabled" and new != "disabled": change["action"] = "Enabled"
            elif old != "disabled" and new == "disabled": change["action"] = "Disabled"
    changes += _diff_items(before.get("startup_entries") or [], after.get("startup_entries") or [], identity_fields=("source", "scope", "name"), compare_fields=("target", "enabled"), category="startup_entries")
    changes += _diff_items(before.get("scheduled_tasks") or [], after.get("scheduled_tasks") or [], identity_fields=("path",), compare_fields=("state", "enabled"), category="scheduled_tasks")
    changes += _diff_items(before.get("listeners") or [], after.get("listeners") or [], identity_fields=("protocol", "local_address", "local_port", "process_name"), compare_fields=("scope",), category="listeners")
    changes += _diff_items(before.get("processes") or [], after.get("processes") or [], identity_fields=("name", "executable_path"), compare_fields=("publisher", "signature_status", "services"), category="processes")
    component_changes = []
    for section in ("optional_features", "runtimes", "browsers", "gpu_drivers", "audio_drivers"):
        component_changes += _diff_items(
            ((before.get("components") or {}).get(section) or []),
            ((after.get("components") or {}).get(section) or []),
            identity_fields=("name", "path"), compare_fields=("version", "driver_version", "state", "status"),
            category="components",
        )
    changes += component_changes
    resource_changes, resource_deltas = _resource_changes(before, after)
    changes += resource_changes
    counts = {
        "applications": len(after.get("applications") or []) - len(before.get("applications") or []),
        "services": len(after.get("services") or []) - len(before.get("services") or []),
        "startup_entries": len(after.get("startup_entries") or []) - len(before.get("startup_entries") or []),
        "scheduled_tasks": len(after.get("scheduled_tasks") or []) - len(before.get("scheduled_tasks") or []),
        "listeners": len(after.get("listeners") or []) - len(before.get("listeners") or []),
        "processes": len(after.get("processes") or []) - len(before.get("processes") or []),
    }
    summary_by_action: dict[str, int] = {}
    summary_by_classification: dict[str, int] = {}
    for change in changes:
        summary_by_action[change["action"]] = summary_by_action.get(change["action"], 0) + 1
        summary_by_classification[change["classification"]] = summary_by_classification.get(change["classification"], 0) + 1
    comparison_id = "CMP-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8].upper()
    comparison = {
        "schema": "foxai.repair_baseline.comparison.v1",
        "comparison_id": comparison_id,
        "created_at": _utc_now(),
        "before": _snapshot_summary(before_doc),
        "after": _snapshot_summary(after_doc),
        "summary": {
            "total_changes": len(changes),
            "by_action": summary_by_action,
            "by_classification": summary_by_classification,
            "count_deltas": counts,
            "resource_deltas": resource_deltas,
        },
        "changes": changes,
        "neutral_interpretation": True,
        "system_modified": False,
        "network_used": False,
    }
    path = None
    if save:
        paths = _ensure_data_dirs(Path(root))
        path = paths["comparisons"] / f"{comparison_id}_{_slug(before_doc.get('name'))}_to_{_slug(after_doc.get('name'))}.json"
        _atomic_json_write(path, comparison)
    return {"ok": True, "message": _comparison_sentence(comparison), "comparison": comparison, "path": str(path or "")}


def _comparison_sentence(comparison: dict[str, Any]) -> str:
    actions = comparison.get("summary", {}).get("by_action", {})
    pieces = []
    for key in ("Added", "Removed", "Changed", "Started", "Stopped", "Enabled", "Disabled"):
        count = int(actions.get(key, 0) or 0)
        if count:
            pieces.append(f"{count} {key.lower()}")
    return (", ".join(pieces[:6]) + ".") if pieces else "No persistent structural changes were found; runtime observations may still be present."


def export_comparison(root: Path, comparison_id: str, formats: list[str] | None = None) -> dict[str, Any]:
    paths = _ensure_data_dirs(Path(root))
    comparison = None
    source_path = None
    for path in paths["comparisons"].glob(f"{_safe_text(comparison_id, 100)}_*.json"):
        candidate = _read_json(path, None)
        if isinstance(candidate, dict) and candidate.get("comparison_id") == comparison_id:
            comparison, source_path = candidate, path
            break
    if comparison is None:
        raise FileNotFoundError(f"Comparison was not found: {comparison_id}")
    requested = {str(x).strip().lower() for x in (formats or ["html", "markdown", "json"])}
    created = []
    stem = source_path.stem
    if "json" in requested:
        target = paths["exports"] / f"{stem}.json"
        _atomic_json_write(target, comparison)
        created.append(str(target))
    if "markdown" in requested or "md" in requested:
        target = paths["exports"] / f"{stem}.md"
        target.write_text(_comparison_markdown(comparison), encoding="utf-8")
        created.append(str(target))
    if "html" in requested:
        target = paths["exports"] / f"{stem}.html"
        target.write_text(_comparison_html(comparison), encoding="utf-8")
        created.append(str(target))
    return {"ok": True, "message": f"Exported {len(created)} local comparison file(s).", "files": created, "network_used": False, "secret_fields_excluded": True}


def _comparison_markdown(comparison: dict[str, Any]) -> str:
    before, after = comparison.get("before") or {}, comparison.get("after") or {}
    lines = [
        "# Repair Bay System Change Comparison", "",
        f"- Comparison: `{comparison.get('comparison_id','')}`",
        f"- Before: **{before.get('name','')}** — {before.get('created_at','')}",
        f"- After: **{after.get('name','')}** — {after.get('created_at','')}",
        f"- Summary: { _comparison_sentence(comparison) }", "",
        "## Changes", "",
    ]
    for item in comparison.get("changes") or []:
        lines += [
            f"### {item.get('action')} — {item.get('name')}",
            f"- Category: {item.get('category')}",
            f"- Classification: {item.get('classification')}",
            "- Evidence:", "```json", json.dumps(item.get("evidence"), indent=2, ensure_ascii=False), "```", "",
        ]
    lines += ["---", "Local read-only report. Secret-bearing fields were excluded. No network transmission occurred.", ""]
    return "\n".join(lines)


def _comparison_html(comparison: dict[str, Any]) -> str:
    rows = []
    for item in comparison.get("changes") or []:
        rows.append(
            "<details><summary><b>" + html.escape(str(item.get("action"))) + "</b> — "
            + html.escape(str(item.get("name"))) + " <small>" + html.escape(str(item.get("classification")))
            + "</small></summary><pre>" + html.escape(json.dumps(item.get("evidence"), indent=2, ensure_ascii=False)) + "</pre></details>"
        )
    return """<!doctype html><meta charset=utf-8><title>Repair Bay Change Comparison</title>
<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px;background:#11151a;color:#edf2f7}details{border:1px solid #46505c;border-radius:10px;padding:10px;margin:10px 0;background:#171d24}summary{cursor:pointer}pre{white-space:pre-wrap;background:#0d1117;padding:12px;border-radius:8px;overflow:auto}small{color:#b9c2cf}</style>
<h1>Repair Bay System Change Comparison</h1><p>""" + html.escape(_comparison_sentence(comparison)) + "</p>" + "".join(rows) + "<p><small>Local read-only report. Secret-bearing fields were excluded. No network transmission occurred.</small></p>"


def _load_sessions(root: Path) -> tuple[dict[str, Any], Path]:
    paths = _ensure_data_dirs(Path(root))
    doc = _read_json(paths["sessions"], {"schema": "foxai.repair_baseline.sessions.v1", "sessions": []})
    if not isinstance(doc, dict):
        doc = {"schema": "foxai.repair_baseline.sessions.v1", "sessions": []}
    doc.setdefault("sessions", [])
    return doc, paths["sessions"]


def begin_change_session(root: Path, *, name: str, note: str = "", collector: Callable[[], dict[str, Any]] | None = None) -> dict[str, Any]:
    session_id = "SES-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8].upper()
    before = capture_snapshot(root, name=f"Before — {name}", note=note, origin="change_session_before", collector=collector, session_id=session_id)
    doc, path = _load_sessions(root)
    session = {
        "session_id": session_id, "name": _safe_text(name, 160) or "Change Session", "note": _safe_text(note, 2000),
        "status": "waiting_for_after", "created_at": _utc_now(), "before_snapshot_id": before["snapshot"]["snapshot_id"],
        "after_snapshot_id": "", "comparison_id": "", "external_change_performed_by_repair_bay": False,
    }
    doc["sessions"].append(session)
    _atomic_json_write(path, doc)
    return {"ok": True, "message": "Before snapshot captured. Perform the external change, then capture the After snapshot.", "session": session, "before": before}


def capture_change_session_after(root: Path, session_id: str, *, note: str = "", collector: Callable[[], dict[str, Any]] | None = None) -> dict[str, Any]:
    doc, path = _load_sessions(root)
    session = next((x for x in doc["sessions"] if x.get("session_id") == session_id), None)
    if not session:
        raise FileNotFoundError(f"Change session was not found: {session_id}")
    if session.get("status") != "waiting_for_after":
        return {"ok": False, "message": "This change session is not waiting for an After snapshot.", "session": session}
    after = capture_snapshot(root, name=f"After — {session.get('name')}", note=note, origin="change_session_after", collector=collector, session_id=session_id)
    comparison_result = compare_snapshots(root, session["before_snapshot_id"], after["snapshot"]["snapshot_id"], save=True)
    session.update({
        "status": "completed", "completed_at": _utc_now(),
        "after_snapshot_id": after["snapshot"]["snapshot_id"],
        "comparison_id": comparison_result["comparison"]["comparison_id"],
    })
    _atomic_json_write(path, doc)
    return {"ok": True, "message": "After snapshot captured and comparison receipt created.", "session": session, "after": after, "comparison": comparison_result}


def close_change_session(root: Path, session_id: str, *, cancel: bool = False) -> dict[str, Any]:
    doc, path = _load_sessions(root)
    session = next((x for x in doc["sessions"] if x.get("session_id") == session_id), None)
    if not session:
        raise FileNotFoundError(f"Change session was not found: {session_id}")
    if session.get("status") == "completed":
        return {"ok": False, "message": "Completed sessions cannot be cancelled or closed without their After snapshot.", "session": session}
    session.update({"status": "cancelled" if cancel else "closed_without_after", "closed_at": _utc_now()})
    _atomic_json_write(path, doc)
    return {"ok": True, "message": "Change session cancelled." if cancel else "Change session closed without an After snapshot.", "session": session}


def api_dispatch(root: Path, route: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    try:
        if route == "/api/repair/baseline/list":
            return list_snapshots(root)
        if route == "/api/repair/baseline/capture":
            return capture_snapshot(root, name=data.get("name") or "Manual Snapshot", note=data.get("note") or "", origin=data.get("origin") or "manual")
        if route == "/api/repair/baseline/known_good":
            return mark_known_good(root, data.get("snapshot_id") or "", confirm=bool(data.get("confirm")))
        if route == "/api/repair/baseline/compare":
            return compare_snapshots(root, data.get("before_id") or "", data.get("after_id") or "", save=True)
        if route == "/api/repair/baseline/export":
            return export_comparison(root, data.get("comparison_id") or "", data.get("formats") or ["html", "markdown", "json"])
        if route == "/api/repair/baseline/session_begin":
            return begin_change_session(root, name=data.get("name") or "Change Session", note=data.get("note") or "")
        if route == "/api/repair/baseline/session_after":
            return capture_change_session_after(root, data.get("session_id") or "", note=data.get("note") or "")
        if route == "/api/repair/baseline/session_cancel":
            return close_change_session(root, data.get("session_id") or "", cancel=True)
        if route == "/api/repair/baseline/session_close":
            return close_change_session(root, data.get("session_id") or "", cancel=False)
        return {"ok": False, "message": "Unknown System Baseline action."}
    except FileNotFoundError as exc:
        return {"ok": False, "message": str(exc)}
    except Exception as exc:
        return {"ok": False, "message": f"System Baseline action failed: {type(exc).__name__}: {exc}"}


__all__ = [
    "BASELINE_VERSION", "DATA_RELATIVE", "collect_system_snapshot", "capture_snapshot",
    "list_snapshots", "mark_known_good", "compare_snapshots", "export_comparison",
    "begin_change_session", "capture_change_session_after", "close_change_session", "api_dispatch",
]
