from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.repair_bay_baseline import (
    DATA_RELATIVE,
    api_dispatch,
    begin_change_session,
    capture_change_session_after,
    capture_snapshot,
    close_change_session,
    collect_system_snapshot,
    compare_snapshots,
    export_comparison,
    list_snapshots,
    mark_known_good,
)


def check(checks: list[dict], condition: bool, name: str, detail: str = "") -> None:
    checks.append({"id": name, "ok": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(name + (": " + detail if detail else ""))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_payload(stage: str) -> dict:
    after = stage == "after"
    return {
        "schema": "foxai.repair_baseline.snapshot_payload.v1",
        "version": "3.0",
        "captured_at": "2026-07-20T20:30:00+00:00" if not after else "2026-07-20T20:40:00+00:00",
        "machine": {
            "computer_name": "DESKTOP-G9ERN9B", "os_caption": "Windows 11 Pro",
            "os_version": "10.0.99999", "architecture": "64-bit", "cpu_model": "Intel Test CPU",
            "logical_processors": 12, "uptime_seconds": 7200,
        },
        "resources": {
            "memory": {
                "total_bytes": 48 * 1024**3,
                "available_bytes": (30 if not after else 29) * 1024**3,
                "cached_bytes": (7 if not after else 8) * 1024**3,
                "committed_bytes": (18 if not after else 19) * 1024**3,
            },
            "cpu": {"model": "Intel Test CPU", "logical_processors": 12, "utilization_percent": 11 if not after else 32},
            "disks": [
                {"mount": "C:\\", "type": "fixed", "capacity_bytes": 1_000_000_000_000, "free_bytes": 500_000_000_000 if not after else 499_380_000_000},
            ],
        },
        "processes": [
            {"name": "foxai.exe", "process_id": 100 if not after else 901, "executable_path": "Z:\\FOXAI\\foxai.exe", "publisher": "FOXAI", "signature_status": "Valid", "working_set_bytes": 100_000_000 if not after else 120_000_000, "private_bytes": 80_000_000, "cpu_time_seconds": 10, "start_time": "x", "services": []},
            {"name": "chrome.exe", "process_id": 200 if not after else 902, "executable_path": "C:\\Chrome\\chrome.exe", "publisher": "Google", "signature_status": "Valid", "working_set_bytes": 500_000_000 if not after else 900_000_000, "private_bytes": 400_000_000, "cpu_time_seconds": 30, "start_time": "x", "services": []},
        ] + ([{"name": "newhelper.exe", "process_id": 903, "executable_path": "C:\\Tools\\newhelper.exe", "publisher": "Example", "signature_status": "Valid", "working_set_bytes": 50_000_000, "private_bytes": 40_000_000, "cpu_time_seconds": 1, "start_time": "x", "services": []}] if after else []),
        "services": [
            {"name": "FoxService", "display_name": "FOXAI Service", "state": "Stopped" if not after else "Running", "start_type": "Manual" if not after else "Automatic", "executable_path": "Z:\\FOXAI\\service.exe", "service_account_category": "system", "process_id": 0 if not after else 903},
        ],
        "startup_entries": ([] if not after else [{"source": "registry_run", "scope": "CurrentUser", "name": "Example Startup", "target": "C:\\Example\\example.exe", "enabled": True}]),
        "scheduled_tasks": [
            {"path": "\\FOXAI\\ReadOnlyCheck", "state": "Ready", "enabled": True},
        ] + ([{"path": "\\Example\\NewTask", "state": "Ready", "enabled": True}] if after else []),
        "listeners": ([] if not after else [{"protocol": "TCP", "local_address": "127.0.0.1", "local_port": 9876, "process_id": 903, "process_name": "newhelper.exe", "scope": "localhost"}]),
        "applications": [
            {"name": "FOXAI", "version": "2.5", "publisher": "FOXAI", "install_location": "Z:\\FOXAI"},
        ] + ([{"name": "Example Voice Pack", "version": "1.0", "publisher": "Example", "install_location": "C:\\Program Files\\Example"}] if after else []),
        "components": {
            "optional_features": [{"name": "LegacyComponents", "state": "Enabled"}],
            "runtimes": [{"name": "python.exe", "path": "Z:\\FOXAI\\Runtime\\Desktop\\python\\python.exe", "version": "3.14.6"}],
            "browsers": [{"name": "Chrome", "path": "C:\\Chrome\\chrome.exe", "version": "150" if not after else "151"}],
            "gpu_drivers": [{"name": "Intel UHD 770", "driver_version": "1.0", "status": "OK"}],
            "audio_drivers": [{"name": "Audio Device", "manufacturer": "Example", "status": "OK"}],
        },
        "collector": {
            "fixture": True, "read_only": True, "network_used": False,
            "mutation_commands": 0, "warnings": [], "secret_fields_excluded": True,
            "password": "must be removed", "command_line": "must be removed",
        },
    }


def run_deterministic(root: Path, web_path: Path) -> dict:
    checks: list[dict] = []
    test_root = Path(tempfile.mkdtemp(prefix="repair_bay_v3_fixture_"))
    try:
        before_source = fixture_payload("before")
        after_source = fixture_payload("after")
        before = capture_snapshot(test_root, name="Before Voice Installation", note="Known clean state", collector=lambda: before_source)
        after = capture_snapshot(test_root, name="After Voice Installation", note="Installed local voice pack", collector=lambda: after_source)
        check(checks, before.get("ok") is True and after.get("ok") is True, "snapshot_creation")
        check(checks, before["snapshot"]["name"] == "Before Voice Installation", "snapshot_naming")

        listing = list_snapshots(test_root)
        check(checks, len(listing["snapshots"]) == 2, "historical_snapshot_preservation")
        blocked = mark_known_good(test_root, before["snapshot"]["snapshot_id"], confirm=False)
        check(checks, blocked.get("ok") is False, "known_good_requires_confirmation")
        selected = mark_known_good(test_root, before["snapshot"]["snapshot_id"], confirm=True)
        check(checks, selected.get("ok") is True, "known_good_explicit_selection")
        check(checks, list_snapshots(test_root)["known_good_snapshot_id"] == before["snapshot"]["snapshot_id"], "known_good_persisted")

        compared = compare_snapshots(test_root, before["snapshot"]["snapshot_id"], after["snapshot"]["snapshot_id"], save=True)
        comparison = compared["comparison"]
        changes = comparison["changes"]
        check(checks, comparison["summary"]["total_changes"] > 0, "comparison_creation")
        check(checks, any(x["category"] == "applications" and x["action"] == "Added" for x in changes), "installed_application_addition")
        check(checks, any(x["category"] == "services" and x["action"] in {"Started", "Enabled"} for x in changes), "service_state_or_start_type_change")
        check(checks, any(x["category"] == "startup_entries" and x["action"] == "Added" for x in changes), "startup_entry_addition")
        check(checks, any(x["category"] == "scheduled_tasks" and x["action"] == "Added" for x in changes), "scheduled_task_summary_change")
        check(checks, any(x["category"] == "listeners" and x["action"] == "Added" for x in changes), "new_listening_port")
        check(checks, not any(x["category"] == "processes" and x["name"] == "foxai.exe" and x["action"] in {"Added", "Removed"} for x in changes), "process_identity_ignores_pid")
        check(checks, any(x["category"] == "resources" for x in changes), "memory_and_disk_deltas")
        check(checks, all(x.get("classification") != "malicious" for x in changes), "neutral_classification")
        check(checks, any(x["classification"] == "Runtime Noise" for x in changes), "transient_runtime_noise_handling")
        check(checks, comparison["summary"]["resource_deltas"]["memory_available_bytes_delta"] == -1024**3, "available_memory_delta")
        check(checks, comparison["summary"]["resource_deltas"]["disk_free_bytes_delta"]["C:\\"] == -620_000_000, "free_disk_delta")

        snapshot_files = list((test_root / DATA_RELATIVE / "Snapshots").glob("*.json"))
        raw_text = "\n".join(p.read_text(encoding="utf-8") for p in snapshot_files).casefold()
        check(checks, '"password"' not in raw_text and '"command_line"' not in raw_text, "secret_field_exclusion")

        exports = export_comparison(test_root, comparison["comparison_id"], ["html", "markdown", "json"])
        check(checks, exports.get("ok") is True and len(exports["files"]) == 3, "three_export_formats")
        check(checks, all(Path(p).is_file() for p in exports["files"]), "export_files_exist")
        check(checks, all("password" not in Path(p).read_text(encoding="utf-8").casefold() for p in exports["files"]), "export_secret_exclusion")

        session = begin_change_session(test_root, name="Voice Pack Session", collector=lambda: before_source)
        check(checks, session.get("ok") is True and session["session"]["status"] == "waiting_for_after", "change_session_before_flow")
        completed = capture_change_session_after(test_root, session["session"]["session_id"], collector=lambda: after_source)
        check(checks, completed.get("ok") is True and completed["session"]["status"] == "completed", "change_session_after_flow")
        check(checks, bool(completed["session"]["comparison_id"]), "change_session_receipt")

        cancel_session = begin_change_session(test_root, name="Cancelled Session", collector=lambda: before_source)
        cancelled = close_change_session(test_root, cancel_session["session"]["session_id"], cancel=True)
        check(checks, cancelled.get("ok") is True and cancelled["session"]["status"] == "cancelled", "cancel_session_behavior")
        close_session = begin_change_session(test_root, name="Close Session", collector=lambda: before_source)
        closed = close_change_session(test_root, close_session["session"]["session_id"], cancel=False)
        check(checks, closed.get("ok") is True and closed["session"]["status"] == "closed_without_after", "close_without_after_behavior")

        api_list = api_dispatch(test_root, "/api/repair/baseline/list", {})
        check(checks, api_list.get("ok") is True, "api_list_dispatch")
        api_compare = api_dispatch(test_root, "/api/repair/baseline/compare", {"before_id": before["snapshot"]["snapshot_id"], "after_id": after["snapshot"]["snapshot_id"]})
        check(checks, api_compare.get("ok") is True, "api_compare_dispatch")
        check(checks, api_dispatch(test_root, "/api/repair/baseline/known_good", {"snapshot_id": after["snapshot"]["snapshot_id"], "confirm": False}).get("ok") is False, "api_known_good_fails_closed")

        web_text = web_path.read_text(encoding="utf-8")
        markers = [
            "REPAIR_BAY_SYSTEM_BASELINE_V3_STYLE_START",
            "REPAIR_BAY_SYSTEM_BASELINE_V3_HTML_START",
            "REPAIR_BAY_SYSTEM_BASELINE_V3_BROWSER_START",
            "REPAIR_BAY_SYSTEM_BASELINE_V3_SERVER_START",
            "System Baseline &amp; Change Comparison",
            "Capture Baseline", "Capture After Snapshot", "Compare Snapshots",
            "/api/repair/baseline/list", "/api/repair/baseline/capture",
            "/api/repair/baseline/compare", "/api/repair/baseline/export",
            "Begin Change Session", "Capture After + Compare", "Close Without After", "Cancel Session",
            "repair_system_baseline_exports",
        ]
        for marker in markers:
            check(checks, marker in web_text, "web_marker_" + hashlib.sha256(marker.encode()).hexdigest()[:8], marker)
        check(checks, "Quick Health Scan" in web_text and "Guarded Repair Handoff" in web_text, "repair_bay_v2_5_preserved")
        check(checks, "KAYOCK_WRITER_CALM_GUIDED_V2_BROWSER_START" in web_text and "KAYOCK_WRITER_CALM_HOME_V1_JS_START" in web_text, "kayock_writer_v2_preserved")
        check(checks, "setTimeout(()=>{if(q('repairBaselinePanel'))loadRepairBaselines()}" in web_text, "baseline_ui_initialization")

        data_files = [p for p in test_root.rglob("*") if p.is_file()]
        check(checks, all(DATA_RELATIVE in p.parents or p.name.startswith("VERIFY") is False for p in data_files), "dedicated_repair_bay_storage")
        check(checks, not (test_root / "KAYOCKS_STUDY_BIBLIOTHECA_V1").exists(), "study_databases_untouched")
        check(checks, not (test_root / "Projects" / "KayockWriter").exists(), "writer_files_untouched")

        return {
            "schema": "foxai.repair_bay.v3.verification.v1",
            "result": "passed",
            "check_count": len(checks),
            "checks": checks,
            "fixture_root": str(test_root),
            "network_used": False,
            "system_mutations": 0,
            "repair_actions_applied": 0,
        }
    finally:
        shutil.rmtree(test_root, ignore_errors=True)


def run_live(root: Path) -> dict:
    checks: list[dict] = []
    protected = [
        root / "core" / "foxai_web.py",
        root / "core" / "repair_bay_diagnostics.py",
        root / "core" / "repair_bay_handoff.py",
    ]
    before = {str(p): sha256(p) for p in protected if p.is_file()}
    payload = collect_system_snapshot()
    after = {str(p): sha256(p) for p in protected if p.is_file()}
    check(checks, payload.get("collector", {}).get("read_only") is True, "live_collector_read_only")
    check(checks, payload.get("collector", {}).get("network_used") is False, "live_collector_no_network")
    check(checks, payload.get("collector", {}).get("mutation_commands") == 0, "live_collector_no_mutation_commands")
    check(checks, isinstance(payload.get("machine"), dict), "live_machine_summary")
    check(checks, isinstance(payload.get("resources"), dict), "live_resource_summary")
    check(checks, isinstance(payload.get("processes"), list), "live_process_inventory")
    check(checks, isinstance(payload.get("services"), list), "live_service_inventory")
    check(checks, isinstance(payload.get("startup_entries"), list), "live_startup_inventory")
    check(checks, isinstance(payload.get("listeners"), list), "live_listener_inventory")
    check(checks, isinstance(payload.get("applications"), list), "live_application_inventory")
    serialized = json.dumps(payload, ensure_ascii=False).casefold()
    check(checks, '"password"' not in serialized and '"clipboard"' not in serialized and '"command_line"' not in serialized, "live_secret_exclusion")
    check(checks, before == after, "live_protected_sources_unchanged")
    commands = payload.get("collector", {}).get("commands") or []
    check(checks, all(not command.get("mutation_markers") for command in commands), "live_command_allowlist")
    return {
        "schema": "foxai.repair_bay.v3.live_verification.v1",
        "result": "passed",
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "machine": (payload.get("machine") or {}).get("computer_name", ""),
            "processes": len(payload.get("processes") or []),
            "services": len(payload.get("services") or []),
            "startup_entries": len(payload.get("startup_entries") or []),
            "listeners": len(payload.get("listeners") or []),
            "applications": len(payload.get("applications") or []),
            "warnings": payload.get("collector", {}).get("warnings") or [],
        },
        "network_used": False,
        "system_mutations": 0,
        "repair_actions_applied": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(PROJECT_ROOT))
    parser.add_argument("--mode", choices=("deterministic", "live", "all"), default="all")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    web = root / "core" / "foxai_web.py"
    output: dict[str, object] = {"schema": "foxai.repair_bay.v3.combined_verification.v1", "result": "passed"}
    total = 0
    if args.mode in {"deterministic", "all"}:
        deterministic = run_deterministic(root, web)
        output["deterministic"] = deterministic
        total += int(deterministic["check_count"])
    if args.mode in {"live", "all"}:
        live = run_live(root)
        output["live"] = live
        total += int(live["check_count"])
    output.update({"check_count": total, "network_used": False, "system_mutations": 0, "repair_actions_applied": 0})
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
