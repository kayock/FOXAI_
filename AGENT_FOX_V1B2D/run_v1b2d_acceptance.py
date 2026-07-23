from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

MISSION_ID = "ENG-20260722-183657-F5AF85"
TITLE = "Agent Fox Technical Core V1B-2D — Dual-Interface Live Acceptance Verification"
ROOT = Path(r"Z:\FOXAI")
CORE = ROOT / "System" / "AgentFoxTechnicalCore"
MISSIONS = ROOT / "System" / "EngineeringWorkshop" / "missions"
FINAL_DIR = MISSIONS / f"{MISSION_ID}_V1B2D_DUAL_INTERFACE_LIVE_ACCEPTANCE"
TEMP_DIR = MISSIONS / f".{MISSION_ID}_V1B2D_DUAL_INTERFACE_LIVE_ACCEPTANCE_BUILDING"

PATHS = {
    "adapter": CORE / "self_knowledge_chat_adapter_v1.py",
    "provider": CORE / "resource_evidence_provider_v1.py",
    "web_helper": CORE / "webui_self_knowledge_integration_v1.py",
    "desktop_helper": CORE / "desktop_self_knowledge_integration_v1.py",
    "verifier": CORE / "shared_resource_provider_integration_verifier_v1.py",
    "bridge": CORE / "provenance_self_knowledge_answer_packet_bridge_v1.py",
    "contract": CORE / "SHARED_RESOURCE_PROVIDER_INTEGRATION_CONTRACT_V1.json",
    "fixtures": CORE / "SHARED_RESOURCE_PROVIDER_INTEGRATION_FIXTURES_V1.json",
    "webui_source": ROOT / "core" / "foxai_web.py",
    "desktop_source": ROOT / "ui" / "main_window.py",
}
EXPECTED = {
    "adapter": "1563a0f3275eb7516006c8f608ef595f693a85fcb9cba60f2610ca053b25f275",
    "provider": "41a1663cd30af8a3800c8082d351f8d0338e75cd1df39d3c801a39cc3075f680",
    "web_helper": "451f8b274dad5fae8c72df8fc6a51b0e360cf99a6a4174c000c66f3af9dd8b69",
    "desktop_helper": "1b3aa2e3ab0409112ca602209285e27df1ab6b0216f5d9a9480766e4509078c4",
    "verifier": "fdf30e7b33ac1fda8d88d2ac761fae3ca93f3a01a3261b03e3832a55898d39ce",
    "bridge": "ad501eff2f8162a319085aa4eb6368039e9757e89ee4eaccb11e5f6e446ca6a7",
    "contract": "60b6b5394849a5cd0a192be137deb01be39d2c3f8fd3e4fa75421b94ab5a9ab1",
    "fixtures": "f2fab44d7926a4f46706e369eb853b790137a29ff4b6df689deeab44e9327b13",
    "webui_source": "d7bf0a2042d55ef7f0a5869556015e42c7427e7ff88636b28e1795f3adf7b952",
    "desktop_source": "a9c5bb86878e5f0cd27d221dbb32688b337e6026073a4b66d83339e0aef294a3",
}
VERIFIER_OUTPUTS = (
    "SHARED_RESOURCE_PROVIDER_INTEGRATION_MAP.json",
    "SHARED_RESOURCE_PROVIDER_ROUTING_RESULTS.json",
    "SHARED_RESOURCE_PROVIDER_SURFACE_COMPATIBILITY.json",
    "SHARED_RESOURCE_PROVIDER_INTEGRATION_RECEIPT.json",
)
ACCEPTANCE_RECEIPT = "V1B2D_DUAL_INTERFACE_LIVE_ACCEPTANCE_RECEIPT.json"
RESOURCE_QUESTION = "How much RAM did FOXAI use in the loaded capture?"
CURRENT_LIVE_QUESTION = "How much memory is my computer using right now?"
ORDINARY_QUESTION = "Tell me a joke."
SLASH_COMMAND = "   /engineer workshop preview test"


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_json(argv: list[str], timeout: int) -> dict[str, Any]:
    result = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {argv}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"command returned no JSON: {argv}")
    return json.loads(lines[-1])


def verify_live_hashes() -> list[dict[str, Any]]:
    rows = []
    for name, path in PATHS.items():
        if not path.is_file():
            raise FileNotFoundError(f"required live file missing: {path}")
        digest = sha256_file(path)
        if digest != EXPECTED[name]:
            raise ValueError(f"unexpected live hash for {name}: {digest}")
        rows.append({"name": name, "path": str(path), "sha256": digest, "size_bytes": path.stat().st_size})
    for path in list(PATHS.values()) + [FINAL_DIR, TEMP_DIR]:
        if str(path).casefold().startswith("k:\\"):
            raise AssertionError("K path entered acceptance configuration")
    return rows


def direct_surface_acceptance() -> dict[str, Any]:
    adapter = load_module("foxai_v1b2d_adapter", PATHS["adapter"])
    web = load_module("foxai_v1b2d_web", PATHS["web_helper"])
    desktop = load_module("foxai_v1b2d_desktop", PATHS["desktop_helper"])

    request_id = "V1B2D-EQUIVALENCE-RESOURCE"
    web_adapter = adapter.route_message(RESOURCE_QUESTION, "webui", request_id)
    desktop_adapter = adapter.route_message(RESOURCE_QUESTION, "desktop", request_id)
    for result in (web_adapter, desktop_adapter):
        assert result["handled"] is True
        assert result["status"] == "answered"
        assert result["model_bypass"] is True
        assert result["ordinary_chat_pass_through"] is False
        assert result["diagnostic"]["code"] == "RESOURCE-ANSWERED"
        packet = result["answer_packet"]
        assert packet["current_state_claimed"] is False
        assert packet["live_scan_performed"] is False
    assert web_adapter["answer_text"] == desktop_adapter["answer_text"]
    assert web_adapter["answer_packet"] == desktop_adapter["answer_packet"]

    web_send = web.route_http_request(
        json.dumps({"message": RESOURCE_QUESTION}).encode("utf-8"),
        "/api/chat/send",
    )
    web_stream = web.route_http_request(
        json.dumps({"message": RESOURCE_QUESTION}).encode("utf-8"),
        "/api/chat/stream",
    )
    desktop_resource = desktop.route_desktop_message(RESOURCE_QUESTION)
    assert web_send["intercepted"] is True and web_send["adapter_result"]["status"] == "answered"
    assert web_stream["intercepted"] is True and web_stream["adapter_result"]["status"] == "answered"
    assert desktop_resource["intercepted"] is True and desktop_resource["status"] == "answered"
    assert web_send["adapter_result"]["answer_text"] == desktop_resource["answer_text"]
    assert web_stream["adapter_result"]["answer_text"] == desktop_resource["answer_text"]

    web_current = web.route_http_request(json.dumps({"message": CURRENT_LIVE_QUESTION}).encode("utf-8"), "/api/chat/send")
    desktop_current = desktop.route_desktop_message(CURRENT_LIVE_QUESTION)
    assert web_current["intercepted"] is False
    assert desktop_current["intercepted"] is False and desktop_current["status"] == "pass_through"

    web_ordinary = web.route_http_request(json.dumps({"message": ORDINARY_QUESTION}).encode("utf-8"), "/api/chat/send")
    desktop_ordinary = desktop.route_desktop_message(ORDINARY_QUESTION)
    assert web_ordinary["intercepted"] is False
    assert desktop_ordinary["intercepted"] is False and desktop_ordinary["status"] == "pass_through"

    web_slash = web.route_http_request(json.dumps({"message": SLASH_COMMAND}).encode("utf-8"), "/api/chat/send")
    desktop_slash = desktop.route_desktop_message(SLASH_COMMAND)
    assert web_slash["intercepted"] is False
    assert desktop_slash["intercepted"] is False and desktop_slash["status"] == "pass_through"

    return {
        "same_resource_answer_text": True,
        "same_resource_answer_packet": True,
        "webui_send_answered": True,
        "webui_stream_answered": True,
        "desktop_answered": True,
        "current_live_pass_through_both_surfaces": True,
        "ordinary_chat_pass_through_both_surfaces": True,
        "slash_command_bypass_both_surfaces": True,
        "current_state_claimed": False,
        "live_scan_performed": False,
    }


def validate_verifier_evidence(output_dir: Path) -> dict[str, Any]:
    actual = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    assert actual == sorted(VERIFIER_OUTPUTS), (actual, VERIFIER_OUTPUTS)
    routing = json.loads((output_dir / VERIFIER_OUTPUTS[1]).read_text(encoding="utf-8"))
    surfaces = json.loads((output_dir / VERIFIER_OUTPUTS[2]).read_text(encoding="utf-8"))
    source_receipt = json.loads((output_dir / VERIFIER_OUTPUTS[3]).read_text(encoding="utf-8"))
    assert routing["all_passed"] is True
    assert routing["resource_category_case_count"] == 36
    assert routing["routing_case_count"] == 16
    assert routing["overlap_case_count"] == 8
    assert len(routing["failure_boundary_results"]) == 2
    assert len(surfaces["webui_results"]) == 6
    assert len(surfaces["desktop_results"]) == 5
    assert surfaces["webui_send_envelope_preserved"] is True
    assert surfaces["webui_stream_envelope_preserved"] is True
    assert surfaces["desktop_display_contract_preserved"] is True
    assert surfaces["ordinary_chat_route_preserved"] is True
    assert surfaces["slash_command_route_preserved"] is True
    assert surfaces["live_model_calls_performed"] is False
    for key in (
        "live_scan_performed",
        "live_process_inspection_performed",
        "live_listener_inspection_performed",
        "network_connections_initiated",
        "model_calls_performed",
        "automatic_process_changes_performed",
        "services_changed",
        "startup_items_changed",
        "registry_writes",
        "source_evidence_modified",
        "webui_or_desktop_entry_source_modified",
        "rollback_drive_k_accessed",
    ):
        assert source_receipt[key] is False, key
    return {
        "resource_category_surface_cases": routing["resource_category_case_count"],
        "routing_surface_cases": routing["routing_case_count"],
        "overlap_surface_cases": routing["overlap_case_count"],
        "failure_boundary_cases": len(routing["failure_boundary_results"]),
        "webui_surface_cases": len(surfaces["webui_results"]),
        "desktop_surface_cases": len(surfaces["desktop_results"]),
        "all_passed": True,
    }


def package_self_test() -> int:
    assert MISSION_ID.startswith("ENG-")
    assert FINAL_DIR.name.endswith("V1B2D_DUAL_INTERFACE_LIVE_ACCEPTANCE")
    assert len(EXPECTED) == 10
    assert len(VERIFIER_OUTPUTS) == 4
    blob = canonical_bytes({"b": 2, "a": 1})
    assert blob == b'{\n  "a": 1,\n  "b": 2\n}\n'
    assert b"\r" not in blob
    print(json.dumps({"status": "package_self_test_ok", "mission_id": MISSION_ID}, sort_keys=True))
    return 0


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--package-self-test":
        return package_self_test()
    if len(sys.argv) != 1:
        raise SystemExit("usage: run_v1b2d_acceptance.py [--package-self-test]")
    if FINAL_DIR.exists():
        raise FileExistsError(f"acceptance evidence already exists; no overwrite performed: {FINAL_DIR}")
    if TEMP_DIR.exists():
        raise FileExistsError(f"incomplete acceptance build directory exists; no overwrite performed: {TEMP_DIR}")

    verified_inputs = verify_live_hashes()
    python_exe = Path(sys.executable)
    verifier = PATHS["verifier"]
    self_test_result = run_json([str(python_exe), "-I", "-B", "-S", str(verifier), "self-test"], 90)
    assert self_test_result["status"] == "ok"
    assert self_test_result["resource_category_count"] == 18
    assert self_test_result["surface_count"] == 2
    assert self_test_result["network_used"] is False
    assert self_test_result["model_used"] is False
    assert self_test_result["k_path_excluded"] is True

    try:
        build_result = run_json(
            [str(python_exe), "-I", "-B", "-S", str(verifier), "build", "--mission-id", MISSION_ID, "--output-dir", str(TEMP_DIR)],
            240,
        )
        assert build_result["status"] == "integration_built_and_verified"
        validate_result = run_json(
            [str(python_exe), "-I", "-B", "-S", str(verifier), "validate-output", "--output-dir", str(TEMP_DIR)],
            90,
        )
        assert validate_result["status"] == "validated" and validate_result["output_count"] == 4
        evidence_summary = validate_verifier_evidence(TEMP_DIR)
        direct_summary = direct_surface_acceptance()

        output_manifest = []
        for name in VERIFIER_OUTPUTS:
            path = TEMP_DIR / name
            output_manifest.append({"name": name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
        receipt = {
            "schema": "foxai.agent_fox.technical_core.v1b2d.dual_interface_live_acceptance_receipt.v1",
            "mission_id": MISSION_ID,
            "title": TITLE,
            "status": "accepted_verified",
            "source_integration_mission": "ENG-20260722-165746-DF7E34",
            "verification_mode": "installed route helpers and shared adapter; no GUI process launch",
            "verified_live_input_count": len(verified_inputs),
            "verified_live_inputs": verified_inputs,
            "verifier_self_test": self_test_result,
            "verifier_evidence": evidence_summary,
            "direct_dual_surface_acceptance": direct_summary,
            "core_outputs_before_acceptance_receipt": output_manifest,
            "exact_output_count_including_acceptance_receipt": 5,
            "source_files_modified": 0,
            "existing_live_files_modified": 0,
            "generated_evidence_files": 5,
            "webui_or_desktop_launched": False,
            "model_loaded_or_called": False,
            "live_scan_performed": False,
            "process_or_listener_inspection_performed": False,
            "network_connections_initiated": False,
            "services_changed": False,
            "startup_items_changed": False,
            "registry_writes": False,
            "source_evidence_modified": False,
            "rollback_drive_k_accessed": False,
        }
        (TEMP_DIR / ACCEPTANCE_RECEIPT).write_bytes(canonical_bytes(receipt))
        final_names = sorted(path.name for path in TEMP_DIR.iterdir() if path.is_file())
        assert final_names == sorted((*VERIFIER_OUTPUTS, ACCEPTANCE_RECEIPT))
        TEMP_DIR.rename(FINAL_DIR)
    except Exception:
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
        raise

    final_receipt = FINAL_DIR / ACCEPTANCE_RECEIPT
    result = {
        "status": "accepted_verified",
        "mission_id": MISSION_ID,
        "output_dir": str(FINAL_DIR),
        "acceptance_receipt": str(final_receipt),
        "acceptance_receipt_sha256": sha256_file(final_receipt),
        "generated_evidence_files": 5,
        "source_files_modified": 0,
        "model_calls": 0,
        "live_scans": 0,
        "k_access": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
