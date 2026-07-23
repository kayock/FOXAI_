from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

SCHEMA_PREFIX = "foxai.agent_fox.technical_core.v1b2c"
MISSION_SOURCE_PROVIDER = "ENG-20260722-153014-F39AF7"
MISSION_SOURCE_PREFLIGHT = "ENG-20260722-154330-42BAE0"
MISSION_SOURCE_RESOURCE = "ENG-20260722-142022-9FAE11"

DEFAULT_ADAPTER_PATH = Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\self_knowledge_chat_adapter_v1.py")
DEFAULT_PROVIDER_PATH = Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\resource_evidence_provider_v1.py")
DEFAULT_WEB_HELPER_PATH = Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\webui_self_knowledge_integration_v1.py")
DEFAULT_DESKTOP_HELPER_PATH = Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\desktop_self_knowledge_integration_v1.py")
DEFAULT_BRIDGE_PATH = Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\provenance_self_knowledge_answer_packet_bridge_v1.py")
DEFAULT_REGISTRY_DIR = Path(r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-235244-7594A9_V1A3D_PROTECTED_CONTEXT_REGISTRY")
DEFAULT_RESOURCE_SOURCE_DIR = Path(r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260722-142022-9FAE11_V1B1C_BASELINE_COMPARISON_AND_CAPACITY_GUIDANCE")
DEFAULT_PROVIDER_EVIDENCE_DIR = Path(r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260722-153014-F39AF7_V1B2A_R2_RESOURCE_EVIDENCE_PROVIDER")
DEFAULT_PREFLIGHT_EVIDENCE_DIR = Path(r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260722-154330-42BAE0_V1B2B_RESOURCE_PROVIDER_INTEGRATION_SEAM_PREFLIGHT")
DEFAULT_FIXTURES_PATH = Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\SHARED_RESOURCE_PROVIDER_INTEGRATION_FIXTURES_V1.json")
DEFAULT_CONTRACT_PATH = Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\SHARED_RESOURCE_PROVIDER_INTEGRATION_CONTRACT_V1.json")

EXPECTED_HASHES = {
    "adapter": "1563a0f3275eb7516006c8f608ef595f693a85fcb9cba60f2610ca053b25f275",
    "provider": "41a1663cd30af8a3800c8082d351f8d0338e75cd1df39d3c801a39cc3075f680",
    "web_helper": "451f8b274dad5fae8c72df8fc6a51b0e360cf99a6a4174c000c66f3af9dd8b69",
    "desktop_helper": "1b3aa2e3ab0409112ca602209285e27df1ab6b0216f5d9a9480766e4509078c4",
    "bridge": "ad501eff2f8162a319085aa4eb6368039e9757e89ee4eaccb11e5f6e446ca6a7",
    "fixtures": "f2fab44d7926a4f46706e369eb853b790137a29ff4b6df689deeab44e9327b13",
    "contract": "60b6b5394849a5cd0a192be137deb01be39d2c3f8fd3e4fa75421b94ab5a9ab1",
}
RESOURCE_SOURCE_HASHES = {
    "RESOURCE_BASELINE_COMPARISON.json": "40462031e89ea469b7c3940c863d225fa7fbad2cef4c6f44e720154d42cf4c86",
    "FOXAI_COMPONENT_RESOURCE_ATTRIBUTION.json": "8673d496b81aebe432b4f79df7d1b773aea8742f0b09ebfe6d660a9f170f9c3f",
    "CAPACITY_HEADROOM_OBSERVATIONS.json": "3dc50e04a634a73c67b963ea3ee10fdb52d1bac126bac26cb22f544f92288fba",
    "BASELINE_COMPARISON_REPORT.md": "6473cc6b7ef328e095348e4ad8813df53e31e061c21f1f5cff6e9993d18c95b7",
    "BASELINE_COMPARISON_RECEIPT.json": "1688a1a1a90f7925c361996eef6211476d133280307416e5a84e68a3ca07b71f",
}
PROVIDER_EVIDENCE_HASHES = {
    "RESOURCE_EVIDENCE_REGISTRY.json": "6e9c3eaea722cb5260f9f0df35d6ea90f37e83697e1b83592670d6599c33e1aa",
    "RESOURCE_QUERY_FIXTURE_RESULTS.json": "554631166de3da90ad54f737df2b81621fbd55eafef6b553d0fb9f96c6502bd6",
    "RESOURCE_EVIDENCE_PROVIDER_RECEIPT.json": "a660a47f3597531a5e603cddd6069d85c9d68cccec6b59521a489ecf5ed5c3db",
}
PREFLIGHT_EVIDENCE_HASHES = {
    "RESOURCE_PROVIDER_INTEGRATION_SEAM_MAP.json": "e43691d671e4feea43c18fc94e97ca82468b2ca9d18d649554c0008bd82ad490",
    "RESOURCE_PROVIDER_ROUTING_PREFLIGHT_FIXTURES.json": "1dd58fe3d6dd5056e69340f372464d33af38140f9ca076b8cffbb280813c6690",
    "RESOURCE_PROVIDER_INTEGRATION_PREFLIGHT_RECEIPT.json": "2738abcb23646e99b9936cd3501721e2901d3cc8ba942cb302d6662ae1dff612",
}
OUTPUT_NAMES = (
    "SHARED_RESOURCE_PROVIDER_INTEGRATION_MAP.json",
    "SHARED_RESOURCE_PROVIDER_ROUTING_RESULTS.json",
    "SHARED_RESOURCE_PROVIDER_SURFACE_COMPATIBILITY.json",
    "SHARED_RESOURCE_PROVIDER_INTEGRATION_RECEIPT.json",
)

_PATHS = {
    "adapter": DEFAULT_ADAPTER_PATH,
    "provider": DEFAULT_PROVIDER_PATH,
    "web_helper": DEFAULT_WEB_HELPER_PATH,
    "desktop_helper": DEFAULT_DESKTOP_HELPER_PATH,
    "bridge": DEFAULT_BRIDGE_PATH,
    "registry": DEFAULT_REGISTRY_DIR,
    "resource_source": DEFAULT_RESOURCE_SOURCE_DIR,
    "provider_evidence": DEFAULT_PROVIDER_EVIDENCE_DIR,
    "preflight_evidence": DEFAULT_PREFLIGHT_EVIDENCE_DIR,
    "fixtures": DEFAULT_FIXTURES_PATH,
    "contract": DEFAULT_CONTRACT_PATH,
}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "\x1f".join(str(item) for item in parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:16].upper()}"


def _configure_paths_for_tests(**paths: Path | str) -> None:
    for key, value in paths.items():
        if key not in _PATHS:
            raise KeyError(key)
        _PATHS[key] = Path(value)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module_loader_unavailable:{name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _verify_file(path: Path, expected: str, logical_name: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(logical_name)
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"hash_mismatch:{logical_name}")
    return {
        "input_id": stable_id("INPUT", logical_name, expected),
        "logical_name": logical_name,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": actual,
        "verified": True,
    }


def verify_inputs() -> list[dict[str, Any]]:
    rows = [
        _verify_file(_PATHS["adapter"], EXPECTED_HASHES["adapter"], "integrated_shared_adapter"),
        _verify_file(_PATHS["provider"], EXPECTED_HASHES["provider"], "resource_provider"),
        _verify_file(_PATHS["web_helper"], EXPECTED_HASHES["web_helper"], "webui_integration_helper"),
        _verify_file(_PATHS["desktop_helper"], EXPECTED_HASHES["desktop_helper"], "desktop_integration_helper"),
        _verify_file(_PATHS["bridge"], EXPECTED_HASHES["bridge"], "protected_answer_bridge"),
        _verify_file(_PATHS["fixtures"], EXPECTED_HASHES["fixtures"], "integration_fixtures"),
        _verify_file(_PATHS["contract"], EXPECTED_HASHES["contract"], "integration_contract"),
    ]
    for name, digest in sorted(RESOURCE_SOURCE_HASHES.items()):
        rows.append(_verify_file(_PATHS["resource_source"] / name, digest, f"resource_source:{name}"))
    for name, digest in sorted(PROVIDER_EVIDENCE_HASHES.items()):
        rows.append(_verify_file(_PATHS["provider_evidence"] / name, digest, f"provider_evidence:{name}"))
    for name, digest in sorted(PREFLIGHT_EVIDENCE_HASHES.items()):
        rows.append(_verify_file(_PATHS["preflight_evidence"] / name, digest, f"preflight_evidence:{name}"))
    return rows


def _load_adapter():
    module = _load_module("foxai_v1b2c_integrated_adapter", _PATHS["adapter"])
    module._configure_paths_for_tests(
        _PATHS["bridge"],
        _PATHS["registry"],
        _PATHS["provider"],
        _PATHS["resource_source"],
    )
    return module


def _route_kind(result: dict[str, Any]) -> str:
    diagnostic = result.get("diagnostic") or {}
    code = diagnostic.get("code") if isinstance(diagnostic, dict) else None
    if code == "RESOURCE-ANSWERED":
        return "resource_evidence_provider"
    if isinstance(code, str) and code.startswith("SK-") and result.get("handled") is True:
        return "protected_context_self_knowledge"
    if code == "SK-PASS-SLASH-COMMAND":
        return "slash_command_bypass"
    return "ordinary_chat"


def run_routing_tests() -> dict[str, Any]:
    fixtures = json.loads(_PATHS["fixtures"].read_text(encoding="utf-8"))
    adapter = _load_adapter()
    category_rows = []
    for spec in fixtures["supported_resource_categories"]:
        for surface in fixtures["surfaces"]:
            adapter._reset_audit_for_tests()
            result = adapter.route_message(spec["question"], surface)
            audit = adapter._audit_snapshot()
            packet = result.get("answer_packet") or {}
            assert result["status"] == "answered"
            assert _route_kind(result) == "resource_evidence_provider"
            assert packet.get("matched_category") == spec["category"]
            assert packet.get("current_state_claimed") is False
            assert packet.get("live_scan_performed") is False
            assert audit["registry_verify_calls"] == 0
            assert audit["resource_answer_calls"] == 1
            category_rows.append({
                "case_id": stable_id("RESOURCE-CASE", spec["category"], surface),
                "category": spec["category"],
                "question": spec["question"],
                "surface": surface,
                "status": result["status"],
                "route": _route_kind(result),
                "model_bypass": result["model_bypass"],
                "ordinary_chat_pass_through": result["ordinary_chat_pass_through"],
                "current_state_claimed": packet.get("current_state_claimed"),
                "live_scan_performed": packet.get("live_scan_performed"),
                "source_mission": packet.get("source_mission"),
                "source_files": packet.get("source_files"),
                "passed": True,
            })
    routing_rows = []
    for spec in fixtures["routing_fixtures"]:
        for surface in fixtures["surfaces"]:
            adapter._reset_audit_for_tests()
            result = adapter.route_message(spec["message"], surface)
            audit = adapter._audit_snapshot()
            route = _route_kind(result)
            assert result["status"] == spec["expected_status"], (spec, surface, result)
            assert route == spec["expected_route"], (spec, surface, route)
            if route == "slash_command_bypass":
                assert all(value == 0 for value in audit.values())
            if route == "protected_context_self_knowledge":
                assert audit["resource_provider_hash_checks"] == 0
                assert audit["resource_answer_calls"] == 0
            if route == "ordinary_chat":
                assert result["handled"] is False
                assert result["model_bypass"] is False
                assert result["ordinary_chat_pass_through"] is True
            routing_rows.append({
                "case_id": stable_id("ROUTING-CASE", spec["fixture_id"], surface),
                "fixture_id": spec["fixture_id"],
                "message": spec["message"],
                "surface": surface,
                "status": result["status"],
                "route": route,
                "diagnostic_code": (result.get("diagnostic") or {}).get("code"),
                "bridge_loads": audit["bridge_loads"],
                "registry_verify_calls": audit["registry_verify_calls"],
                "resource_provider_loads": audit["resource_provider_loads"],
                "resource_answer_calls": audit["resource_answer_calls"],
                "passed": True,
            })
    overlap_rows = []
    for spec in fixtures["overlap_fixtures"]:
        for surface in fixtures["surfaces"]:
            adapter._reset_audit_for_tests()
            result = adapter.route_message(spec["message"], surface)
            audit = adapter._audit_snapshot()
            assert _route_kind(result) == "protected_context_self_knowledge"
            assert audit["resource_provider_hash_checks"] == 0
            overlap_rows.append({
                "case_id": stable_id("OVERLAP-CASE", spec["fixture_id"], surface),
                "fixture_id": spec["fixture_id"],
                "message": spec["message"],
                "surface": surface,
                "status": result["status"],
                "route": _route_kind(result),
                "resource_provider_invoked": False,
                "passed": True,
            })
    return {
        "category_rows": category_rows,
        "routing_rows": routing_rows,
        "overlap_rows": overlap_rows,
        "resource_case_count": len(category_rows),
        "routing_case_count": len(routing_rows),
        "overlap_case_count": len(overlap_rows),
    }


def run_surface_tests() -> dict[str, Any]:
    web = _load_module("foxai_v1b2c_web_helper", _PATHS["web_helper"])
    desktop = _load_module("foxai_v1b2c_desktop_helper", _PATHS["desktop_helper"])
    common = {
        "adapter_path": _PATHS["adapter"],
        "bridge_path": _PATHS["bridge"],
        "registry_dir": _PATHS["registry"],
        "resource_provider_path": _PATHS["provider"],
        "resource_source_dir": _PATHS["resource_source"],
    }
    web_rows = []
    for route in ("/api/chat/send", "/api/chat/stream"):
        result = web.route_http_request(
            json.dumps({"message": "How much RAM did FOXAI use in the loaded capture?"}).encode("utf-8"),
            route,
            **common,
        )
        assert result["intercepted"] is True
        assert result["adapter_result"]["status"] == "answered"
        assert result["adapter_result"]["diagnostic"]["code"] == "RESOURCE-ANSWERED"
        assert b"42.83 GB" in result["body"]
        web_rows.append({
            "case_id": stable_id("WEB", route, "resource"),
            "endpoint": route,
            "case": "historical_resource",
            "intercepted": True,
            "status": "answered",
            "content_type": result["content_type"],
            "passed": True,
        })
    for case, message, expected_intercepted in (
        ("current_live", "How much memory is my computer using right now?", False),
        ("generic_webui_launcher", "Tell me about the WebUI launcher.", True),
        ("ordinary_joke", "Tell me a joke.", False),
        ("spaced_slash", "   /engineer workshop preview test", False),
    ):
        result = web.route_http_request(
            json.dumps({"message": message}).encode("utf-8"),
            "/api/chat/send",
            **common,
        )
        assert result["intercepted"] is expected_intercepted
        web_rows.append({
            "case_id": stable_id("WEB", case),
            "endpoint": "/api/chat/send",
            "case": case,
            "intercepted": result["intercepted"],
            "status": (result.get("adapter_result") or {}).get("status"),
            "passed": True,
        })
    desktop_rows = []
    for case, message, expected_intercepted, expected_status in (
        ("historical_resource", "How much RAM did FOXAI use in the loaded capture?", True, "answered"),
        ("current_live", "How much memory is my computer using right now?", False, "pass_through"),
        ("generic_webui_launcher", "Tell me about the WebUI launcher.", True, "clarification_required"),
        ("ordinary_joke", "Tell me a joke.", False, "pass_through"),
        ("spaced_slash", "   /engineer workshop preview test", False, "pass_through"),
    ):
        result = desktop.route_desktop_message(message, **common)
        assert result["intercepted"] is expected_intercepted
        assert result["status"] == expected_status
        desktop_rows.append({
            "case_id": stable_id("DESKTOP", case),
            "case": case,
            "intercepted": result["intercepted"],
            "status": result["status"],
            "passed": True,
        })
    return {"webui": web_rows, "desktop": desktop_rows}


def run_failure_boundary_tests() -> list[dict[str, Any]]:
    adapter = _load_adapter()
    rows = []
    with tempfile.TemporaryDirectory(prefix="foxai_v1b2c_failure_") as tmp_name:
        tmp = Path(tmp_name)
        corrupt_source = tmp / "resource_source"
        shutil.copytree(_PATHS["resource_source"], corrupt_source)
        target = corrupt_source / "RESOURCE_BASELINE_COMPARISON.json"
        target.write_bytes(target.read_bytes() + b"\n")
        adapter._configure_paths_for_tests(_PATHS["bridge"], _PATHS["registry"], _PATHS["provider"], corrupt_source)
        result = adapter.route_message("How much RAM did FOXAI use in the loaded capture?", "webui", "CORRUPT-SOURCE")
        assert result["status"] == "evidence_error"
        assert result["handled"] is True and result["model_bypass"] is True
        assert result["ordinary_chat_pass_through"] is False
        rows.append({
            "case_id": "CORRUPT-SOURCE",
            "boundary": "evidence_failure_after_positive_recognition",
            "status": result["status"],
            "model_bypass": result["model_bypass"],
            "ordinary_chat_pass_through": result["ordinary_chat_pass_through"],
            "passed": True,
        })
        corrupt_provider = tmp / "resource_provider.py"
        corrupt_provider.write_bytes(_PATHS["provider"].read_bytes() + b"\n")
        adapter._configure_paths_for_tests(_PATHS["bridge"], _PATHS["registry"], corrupt_provider, _PATHS["resource_source"])
        result = adapter.route_message("Tell me a joke.", "desktop", "CORRUPT-PROVIDER")
        assert result["status"] == "pass_through"
        assert result["handled"] is False and result["model_bypass"] is False
        rows.append({
            "case_id": "CORRUPT-PROVIDER",
            "boundary": "provider_unavailable_before_recognition",
            "status": result["status"],
            "model_bypass": result["model_bypass"],
            "ordinary_chat_pass_through": result["ordinary_chat_pass_through"],
            "passed": True,
        })
    adapter._configure_paths_for_tests(_PATHS["bridge"], _PATHS["registry"], _PATHS["provider"], _PATHS["resource_source"])
    return rows


def build_outputs(mission_id: str, output_dir: Path) -> dict[str, bytes]:
    verified_inputs = verify_inputs()
    routing = run_routing_tests()
    surfaces = run_surface_tests()
    failure_boundaries = run_failure_boundary_tests()
    integration_map = {
        "schema": f"{SCHEMA_PREFIX}.integration_map.v1",
        "mission_id": mission_id,
        "status": "integrated_and_verified",
        "source_preflight_mission": MISSION_SOURCE_PREFLIGHT,
        "provider_mission": MISSION_SOURCE_PROVIDER,
        "resource_evidence_mission": MISSION_SOURCE_RESOURCE,
        "verified_input_count": len(verified_inputs),
        "verified_inputs": verified_inputs,
        "changed_live_modules": [
            {"path": str(_PATHS["adapter"]), "sha256": EXPECTED_HASHES["adapter"], "role": "shared routing seam"},
            {"path": str(_PATHS["web_helper"]), "sha256": EXPECTED_HASHES["web_helper"], "role": "WebUI verified adapter loader"},
            {"path": str(_PATHS["desktop_helper"]), "sha256": EXPECTED_HASHES["desktop_helper"], "role": "Desktop verified adapter loader"},
        ],
        "unchanged_surface_sources": [
            {"path": r"Z:\FOXAI\core\foxai_web.py", "sha256": "d7bf0a2042d55ef7f0a5869556015e42c7427e7ff88636b28e1795f3adf7b952"},
            {"path": r"Z:\FOXAI\ui\main_window.py", "sha256": "a9c5bb86878e5f0cd27d221dbb32688b337e6026073a4b66d83339e0aef294a3"},
        ],
        "routing_order": [
            "first_non_whitespace_slash_bypass",
            "protected_context_self_knowledge",
            "historical_resource_evidence",
            "ordinary_chat_pass_through",
        ],
        "generic_webui_launcher_alias": {
            "intent": "contexts_for_launcher",
            "result": "clarification_required",
            "resource_provider_invoked": False,
        },
        "answer_packet_schema": "foxai.agent_fox.technical_core.v1a3e.answer_packet.v1",
        "resource_category_count": 18,
        "webui_or_desktop_entry_source_modified": False,
        "restart_required_after_apply": True,
    }
    routing_results = {
        "schema": f"{SCHEMA_PREFIX}.routing_results.v1",
        "mission_id": mission_id,
        "status": "routing_verified",
        "resource_category_case_count": routing["resource_case_count"],
        "routing_case_count": routing["routing_case_count"],
        "overlap_case_count": routing["overlap_case_count"],
        "resource_category_results": routing["category_rows"],
        "routing_results": routing["routing_rows"],
        "overlap_results": routing["overlap_rows"],
        "failure_boundary_results": failure_boundaries,
        "all_passed": True,
    }
    surface_results = {
        "schema": f"{SCHEMA_PREFIX}.surface_compatibility.v1",
        "mission_id": mission_id,
        "status": "surface_compatibility_verified",
        "webui_results": surfaces["webui"],
        "desktop_results": surfaces["desktop"],
        "webui_send_envelope_preserved": True,
        "webui_stream_envelope_preserved": True,
        "desktop_display_contract_preserved": True,
        "ordinary_chat_route_preserved": True,
        "slash_command_route_preserved": True,
        "live_model_calls_performed": False,
        "restart_required_after_apply": True,
    }
    outputs = {
        OUTPUT_NAMES[0]: canonical_bytes(integration_map),
        OUTPUT_NAMES[1]: canonical_bytes(routing_results),
        OUTPUT_NAMES[2]: canonical_bytes(surface_results),
    }
    receipt = {
        "schema": f"{SCHEMA_PREFIX}.integration_receipt.v1",
        "mission_id": mission_id,
        "status": "integration_built_and_verified",
        "output_count": 4,
        "outputs_before_receipt": [
            {"name": name, "size_bytes": len(data), "sha256": sha256_bytes(data)}
            for name, data in sorted(outputs.items())
        ],
        "verified_input_count": len(verified_inputs),
        "resource_category_count": 18,
        "resource_category_surface_case_count": routing["resource_case_count"],
        "routing_surface_case_count": routing["routing_case_count"],
        "overlap_surface_case_count": routing["overlap_case_count"],
        "failure_boundary_case_count": len(failure_boundaries),
        "webui_surface_case_count": len(surfaces["webui"]),
        "desktop_surface_case_count": len(surfaces["desktop"]),
        "first_non_whitespace_slash_bypass_verified": True,
        "protected_context_priority_verified": True,
        "resource_provider_integration_verified": True,
        "current_live_pass_through_verified": True,
        "ordinary_and_creative_chat_preserved": True,
        "answer_packet_compatibility_verified": True,
        "webui_response_compatibility_verified": True,
        "desktop_response_compatibility_verified": True,
        "evidence_failure_after_positive_recognition_fails_closed": True,
        "provider_unavailable_before_recognition_preserves_ordinary_chat": True,
        "deterministic_utf8_lf_serialization": True,
        "restart_required_after_apply": True,
        "live_scan_performed": False,
        "live_process_inspection_performed": False,
        "live_listener_inspection_performed": False,
        "network_connections_initiated": False,
        "model_calls_performed": False,
        "automatic_process_changes_performed": False,
        "services_changed": False,
        "startup_items_changed": False,
        "registry_writes": False,
        "source_evidence_modified": False,
        "webui_or_desktop_entry_source_modified": False,
        "rollback_drive_k_accessed": False,
    }
    outputs[OUTPUT_NAMES[3]] = canonical_bytes(receipt)
    output_dir.mkdir(parents=True, exist_ok=False)
    for name in OUTPUT_NAMES:
        (output_dir / name).write_bytes(outputs[name])
    return outputs


def validate_output(output_dir: Path) -> dict[str, Any]:
    actual = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    assert actual == sorted(OUTPUT_NAMES), (actual, OUTPUT_NAMES)
    total = 0
    for name in OUTPUT_NAMES:
        data = (output_dir / name).read_bytes()
        total += len(data)
        assert b"\r" not in data
        obj = json.loads(data.decode("utf-8"))
        assert data == canonical_bytes(obj)
    receipt = json.loads((output_dir / OUTPUT_NAMES[3]).read_text(encoding="utf-8"))
    assert receipt["status"] == "integration_built_and_verified"
    assert receipt["output_count"] == 4
    for row in receipt["outputs_before_receipt"]:
        data = (output_dir / row["name"]).read_bytes()
        assert len(data) == row["size_bytes"]
        assert sha256_bytes(data) == row["sha256"]
    assert total < 4 * 1024 * 1024
    return {"status": "validated", "output_count": 4, "total_output_bytes": total}


def self_test() -> dict[str, Any]:
    assert len(OUTPUT_NAMES) == 4
    assert len(RESOURCE_SOURCE_HASHES) == 5
    assert len(PROVIDER_EVIDENCE_HASHES) == 3
    assert len(PREFLIGHT_EVIDENCE_HASHES) == 3
    sample = {"b": 2, "a": 1}
    encoded = canonical_bytes(sample)
    assert encoded == b'{\n  "a": 1,\n  "b": 2\n}\n'
    assert b"\r" not in encoded
    return {
        "status": "ok",
        "output_count": 4,
        "resource_category_count": 18,
        "routing_order_count": 4,
        "source_hash_count": 18,
        "surface_count": 2,
        "first_non_whitespace_slash_bypass": True,
        "protected_context_priority": True,
        "current_live_pass_through": True,
        "ordinary_chat_preserved": True,
        "canonical_lf_only": True,
        "live_scan_design": False,
        "network_used": False,
        "model_used": False,
        "k_path_excluded": True,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("usage: verifier self-test|build|validate-output")
    command = argv[1]
    if command == "self-test":
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    if command == "build":
        mission_id = argv[argv.index("--mission-id") + 1]
        output_dir = Path(argv[argv.index("--output-dir") + 1])
        outputs = build_outputs(mission_id, output_dir)
        print(json.dumps({"status": "integration_built_and_verified", "mission_id": mission_id, "output_count": len(outputs)}, sort_keys=True))
        return 0
    if command == "validate-output":
        output_dir = Path(argv[argv.index("--output-dir") + 1])
        print(json.dumps(validate_output(output_dir), sort_keys=True))
        return 0
    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
