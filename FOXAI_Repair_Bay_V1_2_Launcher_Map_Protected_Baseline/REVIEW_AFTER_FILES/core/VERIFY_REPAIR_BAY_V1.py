from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import core.repair_bay_diagnostics as diagnostics
from core.repair_bay_diagnostics import SEVERITIES, run_repair_bay_scan


def tree_snapshot(root: Path) -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        result[str(path.relative_to(root)).replace("\\", "/")] = {
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "mtime_ns": path.stat().st_mtime_ns,
        }
    return result


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_fixture(root: Path) -> None:
    write(root / "core" / "__init__.py", "")
    write(root / "core" / "foxai_web.py", "x = 1\n")
    write(root / "core" / "engineer_agent.py", "class EngineerAgent: pass\n")
    write(root / "Engine" / "llama-server.exe", "engine")
    write(root / "Runtime" / "Desktop" / "python" / "python.exe", "python")
    write(root / "Config" / "model_sources.json", json.dumps({"profiles": {}}))
    write(root / "Models" / "Chat" / "fixture.gguf", "model")
    write(root / "Library" / "README.md", "fixture")
    write(root / "ComfyUI" / "main.py", "x = 1\n")
    write(root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "study_server.py", "x = 1\n")

    write(
        root / "START_FOXAI_WEB_WITH_COMFYUI.bat",
        '@echo off\ncall "%~dp0START_COMFYUI_NORMAL.bat"\n"%~dp0Runtime\\Desktop\\python\\python.exe" "%~dp0core\\foxai_web.py"\n',
    )
    write(
        root / "START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat",
        '@echo off\nstart "ComfyUI" "%~dp0START_COMFYUI_NORMAL.bat"\n"%~dp0Runtime\\Desktop\\python\\python.exe" "%~dp0core\\desktop.py"\n',
    )
    write(
        root / "START_COMFYUI_NORMAL.bat",
        '@echo off\n"%~dp0Runtime\\Desktop\\python\\python.exe" "%~dp0ComfyUI\\main.py"\n',
    )
    write(root / "STATUS_COMFYUI_NORMAL.bat", "@echo off\necho status\n")
    write(root / "STOP_COMFYUI_NORMAL.bat", "@echo off\ntaskkill /IM python.exe\n")
    write(root / "Launch FOXAI Workshop.bat", '@echo off\ncall "%~dp0START_FOXAI_WORKSHOP_PORTABLE.bat"\n')
    write(root / "START_FOXAI_WORKSHOP_PORTABLE.bat", '@echo off\n"%~dp0Runtime\\Desktop\\python\\python.exe" "%~dp0core\\foxai_web.py"\n')
    write(root / "PUSH_TO_GITHUB.bat", "@echo off\ngit status\ngit push\n")
    write(root / "SETUP_GITHUB_REMOTE.bat", "@echo off\ngit remote -v\n")
    write(root / "COMMISSION_FOXAI_USB.bat", '@echo off\n"%~dp0Runtime\\Desktop\\python\\python.exe" commission_usb.py\n')
    write(root / "RESTORE_ACADEMY_REGISTRAR.bat", "@echo off\necho restore only\n")
    write(root / "STOP_FOXAI_CHAT_ENGINE.bat", "@echo off\ntaskkill /IM llama-server.exe\n")
    write(root / "START_FOXAI_WEB.bat", '@echo off\ncall "%~dp0START_FOXAI_WEB_WITH_COMFYUI.bat"\n')
    write(root / "VERIFY_FOXAI_WEB.bat", "@echo off\necho verify\n")
    write(root / "APPLY_FOXAI_WEB_PATCH.bat", "@echo off\necho duplicate historical utility\n")
    write(root / "APPLY_FOXAI_WEB_FIX.bat", "@echo off\necho duplicate historical utility\n")
    write(root / "Start FoxAI.bat", "@echo off\necho alpha duplicate\n")
    write(root / "start FoxAI 3 Alpha.bat", "@echo off\necho alpha duplicate\n")
    write(root / "OLD_UNUSED_COPY.bat", "@echo off\necho old utility\n")
    write(root / "MYSTERY_THING.bat", "@echo off\necho mystery\n")

    write(root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "START_KAYOCKS_STUDY.bat", "@echo off\n")
    write(root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "VERIFY_KAYOCKS_STUDY.bat", "@echo off\n")
    write(root / "System" / "EngineeringWorkshop" / "snapshots" / "fixture.zip", "snapshot")
    write(
        root / "System" / "EngineeringWorkshop" / "receipts" / "fixture.json",
        json.dumps(
            {
                "result": "applied_verified",
                "known_good": [
                    "START_FOXAI_WEB_WITH_COMFYUI.bat",
                    "PUSH_TO_GITHUB.bat",
                    "Launch FOXAI Workshop.bat",
                ],
            }
        ),
    )
    write(root / "Logs" / "web_gui.log", "healthy log\n")

    database = root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "Data" / "bibliotheca.sqlite3"
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    try:
        connection.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO metadata(key,value) VALUES('schema','1')")
        connection.commit()
    finally:
        connection.close()


def finding(report: dict, finding_id: str) -> dict:
    return next(item for item in report["findings"] if item["id"] == finding_id)


def map_item(inventory: dict, name: str) -> dict:
    return next(item for item in inventory["items"] if item["name"] == name)


def assert_report(report: dict, mode: str) -> None:
    assert report["mode"] == mode
    assert report["version"] == "1.2"
    assert report["read_only"] is True
    assert report["safety"]["network_used"] is False
    assert report["safety"]["commands_run"] is False
    assert report["safety"]["files_written"] == 0
    assert report["safety"]["repairs_applied"] == 0
    assert report["proposed_repair_plan"]["status"] == "proposal_only"
    assert report["proposed_repair_plan"]["changes_applied"] == 0
    assert report["summary"]["checks"] == len(report["findings"])
    assert all(item["severity"] in SEVERITIES for item in report["findings"])
    assert sum(report["summary"]["counts"].values()) == len(report["findings"])
    assert all(
        item["suggested_action"] == "No action required."
        for item in report["findings"]
        if item["severity"] == "healthy"
    )


def reboot_fixture(*, confirmed: list[str] | None = None, advisory: list[str] | None = None) -> dict:
    confirmed = list(confirmed or [])
    advisory = list(advisory or [])
    return {
        "available": True,
        "pending": bool(confirmed or advisory),
        "confirmed_pending": bool(confirmed),
        "rename_pending": bool(advisory),
        "confirmed_signals": confirmed,
        "advisory_signals": advisory,
        "signals": confirmed + advisory,
        "source": "verification fixture",
    }


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="repair_bay_v1_2_"))
    build_fixture(root)
    before = tree_snapshot(root)

    original_reboot = diagnostics._windows_pending_reboot
    try:
        diagnostics._windows_pending_reboot = lambda: reboot_fixture()
        quick = run_repair_bay_scan(root, mode="quick", context={"test": True})
        full = run_repair_bay_scan(root, mode="full", context={"test": True})

        assert_report(quick, "quick")
        assert_report(full, "full")
        assert before == tree_snapshot(root), "Read-only scanner modified fixture files."

        zero = finding(full, "zero_byte_live_files")
        assert zero["severity"] == "healthy", zero
        assert "core/__init__.py" in "\n".join(zero["evidence"]), zero

        inventory_finding = finding(full, "root_launcher_inventory")
        inventory = full["evidence"]["launcher_inventory"]
        assert inventory_finding["severity"] == "recommended", inventory_finding
        assert inventory["archive_plan"]["status"] == "proposal_only"
        assert inventory["archive_plan"]["changes_applied"] == 0
        assert inventory["archive_plan"]["delete_allowed"] is False
        assert inventory["archive_plan"]["move_allowed"] is False
        assert inventory["archive_plan"]["rename_allowed"] is False

        web = map_item(inventory, "START_FOXAI_WEB_WITH_COMFYUI.bat")
        comfy = map_item(inventory, "START_COMFYUI_NORMAL.bat")
        workshop = map_item(inventory, "Launch FOXAI Workshop.bat")
        github = map_item(inventory, "PUSH_TO_GITHUB.bat")
        stop = map_item(inventory, "STOP_FOXAI_CHAT_ENGINE.bat")
        commissioning = map_item(inventory, "COMMISSION_FOXAI_USB.bat")
        recovery = map_item(inventory, "RESTORE_ACADEMY_REGISTRAR.bat")
        mystery = map_item(inventory, "MYSTERY_THING.bat")

        assert web["protected"] is True and "known_good_webui" in web["protected_roles"]
        assert "START_COMFYUI_NORMAL.bat" in web["child_launchers"], web
        assert "START_FOXAI_WEB_WITH_COMFYUI.bat" in comfy["called_by"], comfy
        assert any(
            edge["parent"] == "START_FOXAI_WEB_WITH_COMFYUI.bat"
            and edge["child"] == "START_COMFYUI_NORMAL.bat"
            for edge in inventory["relationship_edges"]
        )
        assert "engineering_workshop" in workshop["protected_roles"]
        assert "github_source_backup" in github["protected_roles"]
        assert "stop_control" in stop["protected_roles"]
        assert "commissioning" in commissioning["protected_roles"]
        assert "recovery" in recovery["protected_roles"]
        assert github["receipt_evidence"], github
        assert web["receipt_evidence"], web
        assert workshop["receipt_evidence"], workshop
        assert "GIT" in github["commands"], github
        assert "TASKKILL" in stop["commands"], stop
        assert mystery["entry_point_status"] == "unresolved", mystery
        assert "MYSTERY_THING.bat" in inventory["unresolved_items"]

        external = inventory["protected_baseline"]["external"]
        assert all(item["present"] for item in external), external
        assert {item["role"] for item in external} == {"kayocks_study_start", "kayocks_study_verify"}
        assert inventory["protected_baseline"]["root"], inventory["protected_baseline"]

        assert any(
            set(group["files"]) == {"Start FoxAI.bat", "start FoxAI 3 Alpha.bat"}
            for group in inventory["exact_duplicate_groups"]
        ), inventory["exact_duplicate_groups"]
        candidates = {item["name"] for item in inventory["obsolete_looking_candidates"]}
        assert "start FoxAI 3 Alpha.bat" in candidates, candidates
        assert "OLD_UNUSED_COPY.bat" in candidates, candidates
        assert not any(map_item(inventory, name)["protected"] for name in candidates)

        diagnostics._windows_pending_reboot = lambda: reboot_fixture(
            advisory=["Pending file rename operations"]
        )
        rename_only = run_repair_bay_scan(root, mode="quick")
        rename_finding = finding(rename_only, "pending_reboot")
        assert rename_finding["severity"] == "informational", rename_finding

        diagnostics._windows_pending_reboot = lambda: reboot_fixture(
            confirmed=["Windows Update"],
            advisory=["Pending file rename operations"],
        )
        confirmed = run_repair_bay_scan(root, mode="quick")
        confirmed_finding = finding(confirmed, "pending_reboot")
        assert confirmed_finding["severity"] == "recommended", confirmed_finding
    finally:
        diagnostics._windows_pending_reboot = original_reboot

    live_web = PROJECT_ROOT / "core" / "foxai_web.py"
    assert live_web.is_file(), live_web
    web_text = live_web.read_text(encoding="utf-8")
    for marker in (
        "Read-Only Health Scan",
        "runRepairHealthScan('quick')",
        "/api/repair/health_scan",
        "def repair_bay_health_scan",
        "from core.repair_bay_diagnostics import run_repair_bay_scan",
    ):
        assert marker in web_text, marker

    full_ids = {item["id"] for item in full["findings"]}
    for required in {
        "safety_contract",
        "foxai_root",
        "disk_space",
        "essential_components",
        "known_good_launchers",
        "key_source_syntax",
        "local_models",
        "bibliotheca_database",
        "engineering_workshop_recovery",
        "full_python_syntax",
        "configuration_json",
        "zero_byte_live_files",
        "log_growth",
        "root_launcher_inventory",
    }:
        assert required in full_ids, required

    write(root / "core" / "broken.py", "def broken(:\n")
    (root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "VERIFY_KAYOCKS_STUDY.bat").write_bytes(b"")
    broken_before = tree_snapshot(root)
    diagnostics._windows_pending_reboot = lambda: reboot_fixture()
    try:
        broken = run_repair_bay_scan(root, mode="full")
    finally:
        diagnostics._windows_pending_reboot = original_reboot
    assert broken_before == tree_snapshot(root)
    assert broken["summary"]["counts"]["urgent"] >= 1
    assert broken["summary"]["counts"]["recommended"] >= 1
    assert broken["proposed_repair_plan"]["steps"]
    assert broken["proposed_repair_plan"]["changes_applied"] == 0

    result = {
        "ok": True,
        "schema": "foxai.repair_bay.v1_2.verification",
        "quick_checks": quick["summary"]["checks"],
        "full_checks": full["summary"]["checks"],
        "launcher_contents_parsed": len(inventory["items"]),
        "launcher_relationships_verified": len(inventory["relationship_edges"]),
        "protected_root_launchers_verified": len(inventory["protected_baseline"]["root"]),
        "protected_study_launchers_verified": len(external),
        "receipt_backed_launchers_verified": len(inventory["receipt_backed"]),
        "exact_duplicate_groups_verified": len(inventory["exact_duplicate_groups"]),
        "archive_review_candidates_verified": len(inventory["obsolete_looking_candidates"]),
        "unresolved_items_verified": len(inventory["unresolved_items"]),
        "archive_plan_proposal_only": True,
        "healthy_guidance_corrected": True,
        "empty_init_recognized_as_valid": True,
        "rename_only_restart_marker_informational": True,
        "read_only_tree_unchanged": True,
        "network_used": False,
        "commands_run": False,
        "files_written": 0,
        "repairs_applied": 0,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
