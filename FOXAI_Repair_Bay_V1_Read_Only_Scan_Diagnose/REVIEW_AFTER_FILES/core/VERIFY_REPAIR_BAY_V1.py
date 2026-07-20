from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import sys
from pathlib import Path

SCRIPT_DIR=Path(__file__).resolve().parent
PROJECT_ROOT=SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0,str(PROJECT_ROOT))

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
    write(root / "core" / "foxai_web.py", "x = 1\n")
    write(root / "core" / "engineer_agent.py", "class EngineerAgent: pass\n")
    write(root / "Engine" / "llama-server.exe", "engine")
    write(root / "Runtime" / "Desktop" / "python" / "python.exe", "python")
    write(root / "Config" / "model_sources.json", json.dumps({"profiles": {}}))
    write(root / "Models" / "Chat" / "fixture.gguf", "model")
    write(root / "Library" / "README.md", "fixture")
    write(root / "ComfyUI" / "main.py", "x = 1\n")
    write(root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "study_server.py", "x = 1\n")
    write(root / "START_FOXAI_WEB_WITH_COMFYUI.bat", "@echo off\n")
    write(root / "START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat", "@echo off\n")
    write(root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "START_KAYOCKS_STUDY.bat", "@echo off\n")
    write(root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "VERIFY_KAYOCKS_STUDY.bat", "@echo off\n")
    write(root / "System" / "EngineeringWorkshop" / "snapshots" / "fixture.zip", "snapshot")
    write(root / "System" / "EngineeringWorkshop" / "receipts" / "fixture.json", "{}")
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


def assert_report(report: dict, mode: str) -> None:
    assert report["mode"] == mode
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


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="repair_bay_v1_"))
    build_fixture(root)
    before = tree_snapshot(root)

    quick = run_repair_bay_scan(root, mode="quick", context={"test": True})
    full = run_repair_bay_scan(root, mode="full", context={"test": True})

    assert_report(quick, "quick")
    assert_report(full, "full")
    after = tree_snapshot(root)
    assert before == after, "Read-only scanner modified fixture files."

    live_web=PROJECT_ROOT / "core" / "foxai_web.py"
    assert live_web.is_file(), live_web
    web_text=live_web.read_text(encoding="utf-8")
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
        "root_launcher_clutter",
    }:
        assert required in full_ids, required

    # Prove practical findings appear without the scanner attempting repairs.
    write(root / "core" / "broken.py", "def broken(:\n")
    (root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "VERIFY_KAYOCKS_STUDY.bat").write_bytes(b"")
    broken_before = tree_snapshot(root)
    broken = run_repair_bay_scan(root, mode="full")
    broken_after = tree_snapshot(root)
    assert broken_before == broken_after
    assert broken["summary"]["counts"]["urgent"] >= 1
    assert broken["summary"]["counts"]["recommended"] >= 1
    assert broken["proposed_repair_plan"]["steps"]
    assert broken["proposed_repair_plan"]["changes_applied"] == 0

    result = {
        "ok": True,
        "schema": "foxai.repair_bay.v1.verification",
        "quick_checks": quick["summary"]["checks"],
        "full_checks": full["summary"]["checks"],
        "broken_fixture_urgent": broken["summary"]["counts"]["urgent"],
        "broken_fixture_recommended": broken["summary"]["counts"]["recommended"],
        "read_only_tree_unchanged": True,
        "network_used": False,
        "commands_run": False,
        "repairs_applied": 0,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
