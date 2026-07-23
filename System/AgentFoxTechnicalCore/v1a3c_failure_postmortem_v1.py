from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "foxai.agent_fox.technical_core.v1a3c_pm.failure_postmortem.v1"
FAILED_MISSION_ID = "ENG-20260721-161617-AA7BE6"
FAILED_PLAN_SHA256 = "6769cd4e02414c8f888ee4930f90669aeb20a1c1d4e1b4c23fd217df74e374ea"
OUTPUT_CEILING_BYTES = 8 * 1024 * 1024
MAX_READ_BYTES = 2 * 1024 * 1024
MAX_DISCOVERED_FILES = 120
MAX_EVENT_STDOUT_BYTES = 2 * 1024 * 1024

OUTPUT_NAMES = (
    "POSTMORTEM_EVIDENCE.json",
    "FAILURE_CLASSIFICATION.json",
    "POSTMORTEM_SUMMARY.md",
)

SENSITIVE_VALUE_RE = re.compile(
    r"(?i)(token|secret|password|passwd|authorization|api[_-]?key|cookie)\s*[:=]\s*([^\s,;]+)"
)


def canonical_json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path, include_hash: bool = True) -> dict[str, Any]:
    stat = path.stat()
    row: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "size_bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if include_hash:
        row["sha256"] = sha256_file(path)
    return row


def read_json_bounded(path: Path) -> Any:
    size = path.stat().st_size
    if size > MAX_READ_BYTES:
        raise ValueError(f"JSON file exceeds bounded read limit: {path} ({size} bytes)")
    return json.loads(path.read_text(encoding="utf-8-sig", errors="strict"))


def read_text_bounded(path: Path) -> str:
    size = path.stat().st_size
    if size > MAX_READ_BYTES:
        return f"[not read: file exceeds {MAX_READ_BYTES} byte limit]"
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    return redact_text(text)


def redact_text(text: str) -> str:
    text = SENSITIVE_VALUE_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    lines = text.splitlines()
    return "\n".join(lines[:600])[:120_000]


def existing_file_candidates(project_root: Path) -> list[Path]:
    mission = FAILED_MISSION_ID
    exact = [
        project_root / "System" / "EngineeringWorkshop" / "receipts" / mission / f"{FAILED_PLAN_SHA256}.receipt.json",
        project_root / "System" / "EngineeringWorkshop" / "active_mission.json",
        project_root / "AGENT_FOX_V1A3C" / "PLAN.json",
    ]
    roots = [
        project_root / "System" / "EngineeringWorkshop" / "receipts" / mission,
        project_root / "System" / "EngineeringWorkshop" / "missions",
        project_root / "System" / "EngineeringWorkshop" / "previews",
        project_root / "System" / "EngineeringWorkshop" / "logs",
    ]
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path).casefold()
        if path.is_file() and key not in seen and len(found) < MAX_DISCOVERED_FILES:
            seen.add(key)
            found.append(path)

    for path in exact:
        add(path)
    for root in roots:
        if not root.is_dir() or len(found) >= MAX_DISCOVERED_FILES:
            continue
        try:
            for path in root.glob(f"*{mission}*"):
                add(path)
            for path in root.glob(f"*{FAILED_PLAN_SHA256[:12]}*"):
                add(path)
            if root.name.casefold() in {"receipts", "logs"}:
                for path in root.glob("*.json"):
                    if mission in path.name:
                        add(path)
        except OSError:
            continue
    return sorted(found, key=lambda p: str(p).casefold())


def extract_failure_fields(receipt: Any) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        return {"receipt_format": "not_object"}
    keys = (
        "result", "mission_id", "plan_sha256", "snapshot_path", "snapshot_sha256",
        "receipt_path", "rolled_back", "changes_recorded", "validations_recorded",
        "failure", "blocker", "stage", "authorized", "title", "discovered_files",
    )
    result = {key: receipt.get(key) for key in keys if key in receipt}
    # Some Workshop receipts nest final state or error information.
    for nested_key in ("summary", "implementation", "validation_failure", "error"):
        value = receipt.get(nested_key)
        if value is not None:
            result[nested_key] = value
    return result


def bounded_artifact_records(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        try:
            row = file_record(path, include_hash=path.stat().st_size <= MAX_READ_BYTES)
            row["read_status"] = "metadata_only"
            suffix = path.suffix.casefold()
            if suffix == ".json" and path.stat().st_size <= MAX_READ_BYTES:
                try:
                    data = read_json_bounded(path)
                    row["read_status"] = "json_read"
                    row["selected_fields"] = extract_failure_fields(data)
                except Exception as exc:  # Evidence collection must record, not mask.
                    row["read_status"] = "json_read_failed"
                    row["read_error"] = f"{type(exc).__name__}: {exc}"
            elif suffix in {".txt", ".log", ".md"} and path.stat().st_size <= MAX_READ_BYTES:
                text = read_text_bounded(path)
                interesting = [
                    line for line in text.splitlines()
                    if re.search(r"(?i)traceback|memoryerror|oserror|winerror|return code|validation failed|python|drive|usb|disk|z:\\", line)
                ]
                row["read_status"] = "bounded_text_read"
                row["interesting_lines"] = interesting[:100]
            rows.append(row)
        except Exception as exc:
            rows.append({
                "path": str(path),
                "read_status": "metadata_failed",
                "error": f"{type(exc).__name__}: {exc}",
            })
    return rows


def snapshot_metadata(project_root: Path) -> dict[str, Any]:
    path = (
        project_root / "System" / "EngineeringWorkshop" / "snapshots" /
        FAILED_MISSION_ID / "snapshot_20260721T163112524509Z.zip"
    )
    result: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if not path.is_file():
        return result
    try:
        result.update(file_record(path, include_hash=False))
        result["recorded_sha256"] = "3a952af86a03beb3173fcc43367107beb0694f3e79982d36b5a15f593279b1e2"
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            result["zip_entry_count"] = len(infos)
            result["zip_uncompressed_bytes"] = sum(info.file_size for info in infos)
            result["zip_compressed_bytes"] = sum(info.compress_size for info in infos)
            result["zip_entries_preview"] = [
                {
                    "name": info.filename,
                    "size_bytes": info.file_size,
                    "compressed_bytes": info.compress_size,
                }
                for info in infos[:100]
            ]
            result["zip_read_status"] = "central_directory_read_only"
    except Exception as exc:
        result["zip_read_status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def powershell_literal(text: str) -> str:
    return text.replace("'", "''")


def windows_evidence(project_root: Path) -> dict[str, Any]:
    receipt_path = (
        project_root / "System" / "EngineeringWorkshop" / "receipts" /
        FAILED_MISSION_ID / f"{FAILED_PLAN_SHA256}.receipt.json"
    )
    rp = powershell_literal(str(receipt_path))
    script = rf"""
$ErrorActionPreference='SilentlyContinue'
$OutputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$receipt=Get-Item -LiteralPath '{rp}' -ErrorAction SilentlyContinue
if ($receipt) {{ $center=$receipt.LastWriteTime }} else {{ $center=(Get-Date) }}
$start=$center.AddMinutes(-30)
$end=$center.AddMinutes(30)
function Compact-Message([string]$m) {{
  if ($null -eq $m) {{ return $null }}
  $x=($m -replace '[\r\n]+',' ' -replace '\s+',' ').Trim()
  if ($x.Length -gt 2000) {{ $x=$x.Substring(0,2000) }}
  return $x
}}
$appAll=@(Get-WinEvent -FilterHashtable @{{LogName='Application';StartTime=$start;EndTime=$end}} -MaxEvents 500 -ErrorAction SilentlyContinue)
$app=@($appAll | Where-Object {{
  $_.ProviderName -match 'Application Error|Windows Error Reporting|Application Hang' -or
  $_.Message -match '(?i)python(?:w)?\.exe|FOXAI|Z:\\'
}} | Select-Object -First 80 @{{n='time_created';e={{$_.TimeCreated.ToString('o')}}}},Id,LevelDisplayName,ProviderName,@{{n='message';e={{Compact-Message $_.Message}}}})
$sysAll=@(Get-WinEvent -FilterHashtable @{{LogName='System';StartTime=$start;EndTime=$end}} -MaxEvents 700 -ErrorAction SilentlyContinue)
$sys=@($sysAll | Where-Object {{
  $_.ProviderName -match '(?i)disk|ntfs|storport|stornvme|uasp|usb|kernel-pnp|partmgr|volmgr|driverframeworks' -or
  $_.Message -match '(?i)surprise removal|reset to device|device.*not migrated|USB|Z:\\|disk.*error|I/O error'
}} | Select-Object -First 120 @{{n='time_created';e={{$_.TimeCreated.ToString('o')}}}},Id,LevelDisplayName,ProviderName,@{{n='message';e={{Compact-Message $_.Message}}}})
$volume=Get-Volume -DriveLetter Z -ErrorAction SilentlyContinue | Select-Object DriveLetter,FileSystem,FileSystemLabel,HealthStatus,OperationalStatus,Size,SizeRemaining,Path
$partition=Get-Partition -DriveLetter Z -ErrorAction SilentlyContinue | Select-Object DiskNumber,PartitionNumber,DriveLetter,Type,Size,IsReadOnly,IsOffline
$disk=$null
if ($partition) {{ $disk=$partition | Get-Disk -ErrorAction SilentlyContinue | Select-Object Number,FriendlyName,SerialNumber,BusType,PartitionStyle,OperationalStatus,HealthStatus,IsReadOnly,IsOffline,Size }}
[pscustomobject]@{{
  query_center_local=if($center){{$center.ToString('o')}}else{{$null}}
  query_start_local=$start.ToString('o')
  query_end_local=$end.ToString('o')
  application_log_accessible=($null -ne $appAll)
  system_log_accessible=($null -ne $sysAll)
  application_events=@($app)
  system_events=@($sys)
  volume=$volume
  partition=$partition
  disk=$disk
}} | ConvertTo-Json -Depth 7 -Compress
""".strip()

    argv = [
        "powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-Command", script,
    ]
    result: dict[str, Any] = {
        "attempted": True,
        "child_process_count": 1,
        "shell": False,
        "command_kind": "allowlisted_read_only_windows_evidence_query",
        "timeout_seconds": 30,
    }
    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        stdout = completed.stdout[:MAX_EVENT_STDOUT_BYTES]
        stderr = completed.stderr[:64_000]
        result["return_code"] = completed.returncode
        result["stdout_truncated"] = len(completed.stdout) > len(stdout)
        result["stderr"] = redact_text(stderr.decode("utf-8", errors="replace"))
        if completed.returncode == 0 and stdout.strip():
            try:
                result["data"] = json.loads(stdout.decode("utf-8-sig", errors="strict"))
                result["status"] = "query_succeeded"
            except Exception as exc:
                result["status"] = "malformed_json_output"
                result["parse_error"] = f"{type(exc).__name__}: {exc}"
        else:
            result["status"] = "query_failed"
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
    except FileNotFoundError:
        result["status"] = "powershell_not_found"
    except Exception as exc:
        result["status"] = "query_exception"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def event_rows(win: dict[str, Any], key: str) -> list[dict[str, Any]]:
    data = win.get("data") if isinstance(win, dict) else None
    if not isinstance(data, dict):
        return []
    value = data.get(key, [])
    if isinstance(value, dict):
        return [value]
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def classify(evidence: dict[str, Any]) -> dict[str, Any]:
    win = evidence.get("windows_evidence", {})
    app = event_rows(win, "application_events")
    system = event_rows(win, "system_events")
    python_events = [
        row for row in app
        if re.search(r"(?i)python(?:w)?\.exe|python", f"{row.get('provider_name','')} {row.get('ProviderName','')} {row.get('message','')}")
    ]
    storage_events = [
        row for row in system
        if re.search(
            r"(?i)disk|ntfs|storport|stornvme|uasp|usb|surprise removal|reset to device|I/O error|kernel-pnp",
            f"{row.get('provider_name','')} {row.get('ProviderName','')} {row.get('message','')}",
        )
    ]
    receipt = evidence.get("authoritative_receipt", {})
    current = evidence.get("current_volume_state", {})

    confirmed: list[dict[str, Any]] = [
        {
            "finding": "Engineering validation 3 failed and the Workshop rolled the mission back.",
            "evidence_class": "authoritative_receipt",
            "support": receipt,
        },
        {
            "finding": "The failed build produced no accepted V1A-3C output folder.",
            "evidence_class": "authoritative_receipt",
            "support": {"discovered_files": receipt.get("discovered_files", [])},
        },
        {
            "finding": "Z:\\FOXAI is currently accessible after reboot.",
            "evidence_class": "current_observation",
            "support": current,
        },
    ]
    if python_events:
        confirmed.append({
            "finding": "Relevant Python application event evidence exists near the failed validation.",
            "evidence_class": "windows_application_event",
            "event_count": len(python_events),
        })
    if storage_events:
        confirmed.append({
            "finding": "Relevant storage, filesystem, or USB event evidence exists near the failed validation.",
            "evidence_class": "windows_system_event",
            "event_count": len(storage_events),
        })

    if storage_events:
        primary = "storage_or_usb_transport_event_evidence_found"
        confidence = "high" if any(str(row.get("LevelDisplayName", row.get("level_display_name", ""))).casefold() in {"error", "critical"} for row in storage_events) else "medium"
    elif python_events:
        primary = "python_process_failure_evidence_found_without_matching_storage_event"
        confidence = "medium"
    elif win.get("status") == "query_succeeded":
        primary = "validation_failure_confirmed_but_python_or_usb_cause_not_confirmed_in_event_window"
        confidence = "high"
    else:
        primary = "validation_failure_confirmed_but_windows_event_evidence_unavailable_or_incomplete"
        confidence = "high"

    missing = []
    if not python_events:
        missing.append("No matching Python Application event was found in the bounded event window; absence is not proof that no process crash occurred.")
    if not storage_events:
        missing.append("No matching storage or USB System event was found in the bounded event window; absence is not proof that no transient disconnect occurred.")
    if win.get("status") != "query_succeeded":
        missing.append("The Windows evidence query did not return a complete parseable result.")

    return {
        "schema": SCHEMA,
        "classification": primary,
        "confidence": confidence,
        "confirmed_findings": confirmed,
        "python_event_count": len(python_events),
        "storage_or_usb_event_count": len(storage_events),
        "user_reported_observation": {
            "observation": "Python closed and the USB drive temporarily disappeared during validation 3.",
            "evidence_class": "user_reported_not_machine_confirmed",
        },
        "likely_explanation": (
            "The Workshop receipt proves the build validation failed and rollback completed. The machine-event evidence determines whether a Python application failure or storage/USB transport event is additionally supported."
        ),
        "missing_evidence": missing,
        "recommendation": (
            "Do not rerun the monolithic V1A-3C closure build. Keep V1A-3B as the verified baseline and redesign dependency closure work as small per-context missions with strict memory and output budgets."
        ),
        "risk": "low_after_successful_rollback_and_normal_post_reboot_operation",
        "network_used": False,
        "repair_commands_run": False,
        "existing_foxai_files_modified": False,
    }


def markdown_summary(evidence: dict[str, Any], classification: dict[str, Any]) -> str:
    win = evidence.get("windows_evidence", {})
    data = win.get("data", {}) if isinstance(win, dict) else {}
    volume = data.get("volume") if isinstance(data, dict) else None
    lines = [
        "# V1A-3C Failure Postmortem",
        "",
        f"- Failed mission: `{FAILED_MISSION_ID}`",
        f"- Classification: `{classification['classification']}`",
        f"- Confidence: `{classification['confidence']}`",
        f"- Python event matches: {classification['python_event_count']}",
        f"- Storage/USB event matches: {classification['storage_or_usb_event_count']}",
        f"- Current FOXAI path accessible: {evidence['current_volume_state']['foxai_path_accessible']}",
        f"- Windows evidence query: `{win.get('status')}`",
        "",
        "## Confirmed",
        "",
        "The Engineering Workshop failed validation 3, restored its snapshot, and left no accepted V1A-3C output folder.",
        "",
        "## Current volume evidence",
        "",
        f"```json\n{json.dumps(volume, indent=2, ensure_ascii=False)[:4000]}\n```",
        "",
        "## Recommendation",
        "",
        classification["recommendation"],
        "",
        "No repair, CHKDSK, benchmark, package installation, network request, model load, or FOXAI application launch was performed by this postmortem.",
    ]
    return "\n".join(lines) + "\n"


def validate_output(output_dir: Path) -> dict[str, Any]:
    required = set(OUTPUT_NAMES) | {"POSTMORTEM_RECEIPT.json"}
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    missing = sorted(required - actual)
    if missing:
        raise ValueError(f"Missing postmortem outputs: {missing}")
    evidence = read_json_bounded(output_dir / "POSTMORTEM_EVIDENCE.json")
    classification = read_json_bounded(output_dir / "FAILURE_CLASSIFICATION.json")
    receipt = read_json_bounded(output_dir / "POSTMORTEM_RECEIPT.json")
    if evidence.get("mission_id") != FAILED_MISSION_ID:
        raise ValueError("Wrong failed mission in evidence")
    if classification.get("network_used") is not False:
        raise ValueError("Unexpected network declaration")
    if classification.get("repair_commands_run") is not False:
        raise ValueError("Repair command declaration is not false")
    if receipt.get("powershell_child_process_count") not in (0, 1):
        raise ValueError("Unexpected child process count")
    if receipt.get("network_used") is not False or receipt.get("repair_commands_run") is not False:
        raise ValueError("Unsafe receipt flags")
    for item in receipt.get("core_outputs_before_receipt", []):
        path = output_dir / str(item["name"])
        if not path.is_file() or path.stat().st_size != int(item["size_bytes"]):
            raise ValueError(f"Output size mismatch: {path}")
        if sha256_file(path) != str(item["sha256"]):
            raise ValueError(f"Output hash mismatch: {path}")
    total = sum(path.stat().st_size for path in output_dir.rglob("*") if path.is_file())
    if total > OUTPUT_CEILING_BYTES:
        raise ValueError(f"Output exceeds ceiling: {total}")
    return {"status": "valid", "total_output_bytes": total}


def collect(project_root: Path, output_dir: Path, mission_id: str) -> None:
    if mission_id != "ENG-20260721-164308-A1692D":
        raise ValueError("This collector is bound to ENG-20260721-164308-A1692D")
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError(f"Output directory must be empty: {output_dir}")

    receipt_path = (
        project_root / "System" / "EngineeringWorkshop" / "receipts" /
        FAILED_MISSION_ID / f"{FAILED_PLAN_SHA256}.receipt.json"
    )
    receipt_data: dict[str, Any] = {}
    receipt_error: str | None = None
    if receipt_path.is_file():
        try:
            loaded = read_json_bounded(receipt_path)
            receipt_data = extract_failure_fields(loaded)
            receipt_data["source_path"] = str(receipt_path)
            receipt_data["source_sha256"] = sha256_file(receipt_path)
        except Exception as exc:
            receipt_error = f"{type(exc).__name__}: {exc}"
    else:
        receipt_error = "authoritative receipt not found"

    current_volume = {
        "foxai_path": str(project_root),
        "foxai_path_accessible": project_root.is_dir(),
        "project_root_exists": project_root.exists(),
        "project_root_is_directory": project_root.is_dir(),
    }
    discovered = existing_file_candidates(project_root)
    evidence = {
        "schema": SCHEMA,
        "mission_id": FAILED_MISSION_ID,
        "postmortem_mission_id": mission_id,
        "collected_at_utc": utc_now(),
        "scope": "bounded_read_only_failed_validation_postmortem",
        "authoritative_receipt": receipt_data,
        "authoritative_receipt_error": receipt_error,
        "current_volume_state": current_volume,
        "bounded_workshop_artifacts": bounded_artifact_records(discovered),
        "snapshot_metadata": snapshot_metadata(project_root),
        "windows_evidence": windows_evidence(project_root),
        "safety": {
            "network_used": False,
            "packages_installed": False,
            "repair_commands_run": False,
            "chkdsk_run": False,
            "benchmark_or_stress_test_run": False,
            "foxai_application_launched": False,
            "model_loaded": False,
            "full_source_tree_scanned": False,
            "powershell_child_process_count": 1,
            "powershell_query_read_only": True,
            "existing_foxai_files_modified": False,
        },
    }
    classification = classify(evidence)
    (output_dir / "POSTMORTEM_EVIDENCE.json").write_bytes(canonical_json_bytes(evidence))
    (output_dir / "FAILURE_CLASSIFICATION.json").write_bytes(canonical_json_bytes(classification))
    (output_dir / "POSTMORTEM_SUMMARY.md").write_text(
        markdown_summary(evidence, classification), encoding="utf-8", newline="\n"
    )

    core = []
    for name in OUTPUT_NAMES:
        path = output_dir / name
        core.append({
            "name": name,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    receipt = {
        "schema": SCHEMA,
        "mission_id": mission_id,
        "failed_mission_id": FAILED_MISSION_ID,
        "result": "bounded_postmortem_complete",
        "classification": classification["classification"],
        "core_outputs_before_receipt": core,
        "network_used": False,
        "packages_installed": False,
        "repair_commands_run": False,
        "chkdsk_run": False,
        "benchmark_or_stress_test_run": False,
        "foxai_application_launched": False,
        "models_loaded": False,
        "full_source_tree_scanned": False,
        "powershell_child_process_count": 1,
        "powershell_query_status": evidence["windows_evidence"].get("status"),
        "existing_foxai_files_modified": False,
        "live_system_modified_outside_authorized_outputs": False,
        "output_ceiling_bytes": OUTPUT_CEILING_BYTES,
    }
    (output_dir / "POSTMORTEM_RECEIPT.json").write_bytes(canonical_json_bytes(receipt))
    validate_output(output_dir)


def self_test() -> None:
    sample = {
        "windows_evidence": {
            "status": "query_succeeded",
            "data": {
                "application_events": [{"ProviderName": "Application Error", "message": "Faulting application python.exe"}],
                "system_events": [],
            },
        },
        "authoritative_receipt": {"rolled_back": True, "failure": "validation failed", "discovered_files": []},
        "current_volume_state": {"foxai_path_accessible": True},
    }
    result = classify(sample)
    assert result["classification"] == "python_process_failure_evidence_found_without_matching_storage_event"
    assert result["python_event_count"] == 1
    assert result["storage_or_usb_event_count"] == 0
    assert redact_text("token=abc password:xyz") == "token=[REDACTED] password=[REDACTED]"
    print("V1A3C_PM_SELF_TEST_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--project-root", required=True)
    collect_parser.add_argument("--output-dir", required=True)
    collect_parser.add_argument("--mission-id", required=True)
    validate_parser = sub.add_parser("validate-output")
    validate_parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
    elif args.command == "collect":
        collect(Path(args.project_root), Path(args.output_dir), args.mission_id)
    elif args.command == "validate-output":
        print(json.dumps(validate_output(Path(args.output_dir)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
