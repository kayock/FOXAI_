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
from core.repair_bay_diagnostics import SEVERITIES, run_launcher_index, run_repair_bay_scan
from core.repair_bay_handoff import build_repair_handoff


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
    write(root / "BRIDGE_COMMAND.bat", '@echo off\n"%~dp0Runtime\\Desktop\\python\\python.exe" "%~dp0core\\bridge_command.py"\n')
    write(root / "EVENT_BUS_DEMO.bat", '@echo off\n"%~dp0Runtime\\Desktop\\python\\python.exe" "%~dp0core\\event_bus_demo.py"\n')
    write(root / "CAPTAINS_LOG_VIEW.bat", '@echo off\nexplorer "%~dp0Logs"\n')

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
    assert report["version"] == "1.3"
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
    root = Path(tempfile.mkdtemp(prefix="repair_bay_v1_3_"))
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

        index_before = tree_snapshot(root)
        launcher_index = run_launcher_index(root, context={"test": True})
        assert launcher_index["version"] == "1.3"
        assert launcher_index["read_only"] is True
        assert launcher_index["safety"]["batch_files_executed"] is False
        assert launcher_index["safety"]["network_used"] is False
        assert launcher_index["safety"]["commands_run"] is False
        assert launcher_index["safety"]["files_written"] == 0
        assert launcher_index["safety"]["moves"] == 0
        assert launcher_index["safety"]["renames"] == 0
        assert launcher_index["safety"]["deletions"] == 0
        assert launcher_index["safety"]["repairs_applied"] == 0
        assert index_before == tree_snapshot(root), "Launcher Index modified fixture files."

        indexed_inventory = launcher_index["inventory"]
        assert len(indexed_inventory["items"]) == indexed_inventory["total"]
        assert indexed_inventory["index_filters"]["categories"]
        assert indexed_inventory["index_filters"]["entry_point_statuses"]
        indexed_web = map_item(indexed_inventory, "START_FOXAI_WEB_WITH_COMFYUI.bat")
        indexed_mystery = map_item(indexed_inventory, "MYSTERY_THING.bat")
        indexed_bridge = map_item(indexed_inventory, "BRIDGE_COMMAND.bat")
        indexed_demo = map_item(indexed_inventory, "EVENT_BUS_DEMO.bat")
        indexed_log = map_item(indexed_inventory, "CAPTAINS_LOG_VIEW.bat")
        assert indexed_web["purpose_confidence"] == "high"
        assert indexed_web["exact_duplicate_membership"] == []
        assert indexed_mystery["resolution_state"] == "unresolved", indexed_mystery
        assert indexed_mystery["unresolved_reason"], indexed_mystery
        assert indexed_bridge["resolution_state"] == "resolved", indexed_bridge
        assert indexed_bridge["entry_point_status"] == "utility_entry_point", indexed_bridge
        assert "bridge_command.py" in " ".join(indexed_bridge["python_scripts"]).casefold()
        assert indexed_demo["resolution_state"] == "resolved", indexed_demo
        assert indexed_log["resolution_state"] == "resolved", indexed_log
        assert indexed_log["entry_point_status"] == "utility_entry_point", indexed_log
        assert indexed_web["search_text"]
        assert any(item.get("exact_duplicate_membership") for item in indexed_inventory["items"])
        assert any(item.get("similar_name_membership") for item in indexed_inventory["items"])
        front = indexed_inventory["approved_front_doors"]
        front_root = {item["name"]: item for item in front["root"]}
        assert front_root["START_FOXAI_WEB_WITH_COMFYUI.bat"]["present"] is True
        assert front_root["START_FOXAI_WEB_WITH_COMFYUI.bat"]["tier"] == "primary"
        assert front_root["START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat"]["present"] is True
        assert front_root["Launch FOXAI Workshop.bat"]["present"] is True
        assert front["external"][0]["present"] is True
        protected_names = {
            item["name"]
            for item in indexed_inventory["protected_baseline"]["root"]
        }
        candidate_names = {
            item["name"]
            for item in indexed_inventory["obsolete_looking_candidates"]
        }
        assert not protected_names.intersection(candidate_names)
        assert indexed_inventory["archive_plan"]["status"] == "proposal_only"
        assert indexed_inventory["archive_plan"]["changes_applied"] == 0

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

    handoff_before = tree_snapshot(root)
    supported_report = {
        "read_only": True,
        "safety": {"network_used": False, "commands_run": False, "files_written": 0, "repairs_applied": 0},
        "findings": [
            {
                "id": "known_good_launchers",
                "title": "Known-good launchers",
                "severity": "recommended",
                "summary": "A protected launcher is missing.",
                "suggested_action": "Restore only the affected launcher from verified evidence.",
                "evidence": ["Missing: START_FOXAI_WEB_WITH_COMFYUI.bat"],
            }
        ],
        "evidence": {},
    }
    supported = build_repair_handoff(root, supported_report, "known_good_launchers", level="guided")
    assert supported["ok"] is True
    assert supported["eligible"] is True, supported
    assert supported["status"] == "ready_for_engineer_review"
    assert supported["repair_kind"] == "restore_known_good_launcher"
    assert supported["affected_paths"] == ["START_FOXAI_WEB_WITH_COMFYUI.bat"], supported
    assert supported["backup_required"] is True
    assert supported["implementation_authorized"] is False
    assert supported["changes_applied"] == 0
    assert supported["mission_staged"] is False
    assert "/engineer workshop begin Repair Bay Plan" in supported["engineer_command"]
    assert "not implementation" in supported["engineer_command"]
    assert "Do not apply" in supported["engineer_command"]
    assert ":: APPLY" not in supported["engineer_command"]
    assert "workshop apply" not in supported["engineer_command"].casefold()


    unresolved_selection = build_repair_handoff(
        root,
        supported_report,
        "finding_that_is_not_in_the_latest_scan",
        level="guided",
    )
    assert unresolved_selection["ok"] is False, unresolved_selection
    assert unresolved_selection["requested_finding_id"] == "finding_that_is_not_in_the_latest_scan"
    assert unresolved_selection["implementation_authorized"] is False
    assert "engineer_command" not in unresolved_selection
    assert "could not be resolved" in unresolved_selection["message"]

    advisory_report = {
        "read_only": True,
        "safety": {"network_used": False, "commands_run": False, "files_written": 0, "repairs_applied": 0},
        "findings": [
            {
                "id": "bibliotheca_database",
                "title": "Bibliotheca database integrity",
                "severity": "urgent",
                "summary": "The database needs specialist review.",
                "suggested_action": "Preserve the database before recovery review.",
                "evidence": ["KAYOCKS_STUDY_BIBLIOTHECA_V1/Data/bibliotheca.sqlite3"],
            }
        ],
        "evidence": {},
    }
    advisory = build_repair_handoff(root, advisory_report, "bibliotheca_database", level="advanced")
    assert advisory["ok"] is True
    assert advisory["eligible"] is False
    assert advisory["status"] == "advisory_only"
    assert advisory["repair_kind"] is None
    assert advisory["implementation_authorized"] is False
    assert advisory["engineer_command"].startswith("/engineer Analyze")

    launcher_report = {
        "read_only": True,
        "safety": {"network_used": False, "commands_run": False, "files_written": 0, "repairs_applied": 0},
        "findings": [
            {
                "id": "root_launcher_inventory",
                "title": "FOXAI launcher map and protected baseline",
                "severity": "recommended",
                "summary": "Two low-confidence legacy candidates deserve manual review.",
                "suggested_action": "Prepare a reversible archive plan only.",
                "evidence": [],
            }
        ],
        "evidence": {
            "launcher_inventory": {
                "protected_baseline": {"root": [{"name": "PUSH_TO_GITHUB.bat"}]},
                "obsolete_looking_candidates": [
                    {"name": "OLD_UNUSED_COPY.bat"},
                    {"name": "start FoxAI 3 Alpha.bat"},
                    {"name": "PUSH_TO_GITHUB.bat"},
                ],
            }
        },
    }
    launcher_handoff = build_repair_handoff(root, launcher_report, "root_launcher_inventory", level="advanced")
    assert launcher_handoff["eligible"] is True, launcher_handoff
    assert launcher_handoff["repair_kind"] == "prepare_reversible_launcher_archive_plan"
    assert "OLD_UNUSED_COPY.bat" in launcher_handoff["affected_paths"]
    assert "start FoxAI 3 Alpha.bat" in launcher_handoff["affected_paths"]
    assert "PUSH_TO_GITHUB.bat" not in launcher_handoff["affected_paths"]
    assert handoff_before == tree_snapshot(root), "Guarded handoff modified fixture files."

    live_web = PROJECT_ROOT / "core" / "foxai_web.py"
    assert live_web.is_file(), live_web
    web_text = live_web.read_text(encoding="utf-8")
    for marker in (
        "Quick Health Scan",
        "runRepairHealthScan('quick')",
        "/api/repair/health_scan",
        "def repair_bay_health_scan",
        "from core.repair_bay_diagnostics import run_repair_bay_scan",
        "Launcher Index",
        "loadRepairLauncherIndex(true)",
        "renderRepairLauncherIndex",
        "/api/repair/launcher_index",
        "def repair_bay_launcher_index",
        "from core.repair_bay_diagnostics import run_launcher_index",
        "REPAIR_BAY_CALM_GUIDED_V1_4_START",
        "Ready for a safe check",
        "Check My Computer",
        "Run a Deeper Check",
        "Show scan details",
        "Self-Repair Bay — Advanced",
        "repairPlainFinding",
        "repairCalmViewModel",
        "renderRepairCalmView",
        "Nothing repairs itself silently",
        "No repair actions are available from this screen",
        "REPAIR_BAY_GUARDED_HANDOFF_V2_HTML_START",
        "Guarded Repair Handoff",
        "Ask Engineer to Prepare a Fix",
        "Prepare Exact Repair Plan",
        "openRepairHandoffInMission",
        "/api/repair/handoff",
        "def repair_bay_prepare_handoff",
        "from core.repair_bay_handoff import build_repair_handoff",
        "implementation_not_authorized",
        "REPAIR_BAY_HANDOFF_READINESS_GUARD_V2_1_BROWSER_START",
        "repairAskEngineerButton",
        "Run a Check First",
        "No Repair Needed",
        "Choose a Finding",
        "handleRepairAskEngineer",
        "validRepairEngineerCommand",
        "repairHandoffFailure",
        "This handoff is already open in Mission Console.",
    ):
        assert marker in web_text, marker

    # Calm Repair Bay is the default; expert data stays inside closed details panels.
    repair_section = web_text.split("<section id=repair class=page>", 1)[1].split("</section>", 1)[0]
    assert repair_section.index("repairCalmShell") < repair_section.index("repairSimpleDetails")
    assert repair_section.index("repairSimpleDetails") < repair_section.index("repairAdvancedView")
    assert "<details class=repairSimpleDetails>" in repair_section
    assert "<details class=repairAdvancedView>" in repair_section
    assert "<summary>Self-Repair Bay — Advanced</summary>" in repair_section
    assert "onclick=\"runRepairHealthScan('quick')\"" in repair_section
    assert "onclick=\"runRepairHealthScan('full')\"" in repair_section
    assert repair_section.index("repairHandoffCard") < repair_section.index("repairLauncherCard")
    assert "Ask Engineer to Prepare a Fix" not in repair_section.split("repairCalmAttention", 1)[0]
    assert "Prepare Exact Repair Plan" in repair_section
    assert "Open in Mission Console" in repair_section
    assert "Repair Bay itself cannot repair anything" in repair_section
    assert 'id=repairAskEngineerButton' in repair_section
    assert 'onclick="handleRepairAskEngineer()" disabled>Run a Check First</button>' in repair_section
    assert 'onclick="openGuidedEngineer()">Ask Engineer</button>' not in repair_section
    assert "Describe a Problem Manually" in repair_section

    readiness_function = web_text.split("async function handleRepairAskEngineer()", 1)[1].split("/* REPAIR_BAY_HANDOFF_READINESS_GUARD_V2_1_BROWSER_END */", 1)[0]
    assert "Run a check first" in readiness_function
    assert "No repair is needed" in readiness_function
    assert "findings.length>1" in readiness_function
    assert "Choose one finding" in readiness_function
    assert "prepareRepairHandoff(findings[0].id,'guided',true)" in readiness_function

    prepare_function = web_text.split("async function prepareRepairHandoff", 1)[1].split("function openRepairHandoffInMission()", 1)[0]
    assert "repairHandoffBusy" in prepare_function
    assert "findings.length===1" in prepare_function
    assert "Choose one finding before asking Engineer" in prepare_function
    assert "returned finding did not match your selection" in prepare_function
    assert "planning request was incomplete" in prepare_function

    handoff_function = web_text.split("function openRepairHandoffInMission()", 1)[1].split("/* REPAIR_BAY_GUARDED_HANDOFF_V2_BROWSER_END */", 1)[0]
    assert "requestNonStreamingChat" not in handoff_function
    assert "/api/chat/send" not in handoff_function
    assert "q('input')" in handoff_function
    assert "validRepairEngineerCommand" in handoff_function
    assert "lastRepairHandoffOpenedId" in handoff_function
    assert "already open in Mission Console" in handoff_function
    assert r"Problem:\\s*$" in web_text

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
        "schema": "foxai.repair_bay.v2.verification",
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
        "launcher_index_verified": True,
        "launcher_index_items_verified": len(indexed_inventory["items"]),
        "approved_front_doors_verified": sum(
            1
            for item in list(front["root"]) + list(front["external"])
            if item.get("present")
        ),
        "unknown_resolution_verified": True,
        "search_and_filter_metadata_verified": True,
        "webui_launcher_index_verified": True,
        "calm_guided_default_verified": True,
        "plain_english_attention_summary_verified": True,
        "scan_details_progressive_disclosure_verified": True,
        "self_repair_bay_advanced_verified": True,
        "advanced_controls_closed_by_default_verified": True,
        "guarded_repair_handoff_verified": True,
        "handoff_readiness_guard_verified": True,
        "pre_scan_handoff_disabled_verified": True,
        "healthy_scan_no_repair_state_verified": True,
        "single_finding_auto_attach_verified": True,
        "multiple_findings_selection_required_verified": True,
        "invalid_finding_fails_closed_verified": True,
        "duplicate_handoff_open_guard_verified": True,
        "blank_problem_guard_verified": True,
        "supported_low_risk_planning_verified": True,
        "unsupported_findings_advisory_verified": True,
        "implementation_authorization_false_verified": True,
        "mission_console_review_before_stage_verified": True,
        "handoff_tree_unchanged": True,
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
