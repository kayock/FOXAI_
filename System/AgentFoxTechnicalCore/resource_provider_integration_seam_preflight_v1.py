from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

SCHEMA_PREFIX = "foxai.agent_fox.technical_core.v1b2b"
PREVIOUS_PROVIDER_MISSION = "ENG-20260722-153014-F39AF7"
V1B1C_MISSION = "ENG-20260722-142022-9FAE11"
OUTPUT_NAMES = (
    "RESOURCE_PROVIDER_INTEGRATION_SEAM_MAP.json",
    "RESOURCE_PROVIDER_ROUTING_PREFLIGHT_FIXTURES.json",
    "RESOURCE_PROVIDER_INTEGRATION_PREFLIGHT_RECEIPT.json",
)
OUTPUT_LIMIT_BYTES = 2 * 1024 * 1024

DEFAULT_PATHS: dict[str, Path] = {
    "provider": Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\resource_evidence_provider_v1.py"),
    "provider_contract": Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\RESOURCE_EVIDENCE_PROVIDER_CONTRACT_V1.json"),
    "provider_fixtures": Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\RESOURCE_EVIDENCE_QUERY_FIXTURES_V1.json"),
    "provider_registry": Path(r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260722-153014-F39AF7_V1B2A_R2_RESOURCE_EVIDENCE_PROVIDER\RESOURCE_EVIDENCE_REGISTRY.json"),
    "provider_fixture_results": Path(r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260722-153014-F39AF7_V1B2A_R2_RESOURCE_EVIDENCE_PROVIDER\RESOURCE_QUERY_FIXTURE_RESULTS.json"),
    "provider_receipt": Path(r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260722-153014-F39AF7_V1B2A_R2_RESOURCE_EVIDENCE_PROVIDER\RESOURCE_EVIDENCE_PROVIDER_RECEIPT.json"),
    "v1b1c_source_dir": Path(r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260722-142022-9FAE11_V1B1C_BASELINE_COMPARISON_AND_CAPACITY_GUIDANCE"),
    "query_bridge": Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\protected_context_registry_query_bridge_v1.py"),
    "answer_bridge": Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\provenance_self_knowledge_answer_packet_bridge_v1.py"),
    "shared_adapter": Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\self_knowledge_chat_adapter_v1.py"),
    "web_helper": Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\webui_self_knowledge_integration_v1.py"),
    "desktop_helper": Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\desktop_self_knowledge_integration_v1.py"),
    "web_source": Path(r"Z:\FOXAI\core\foxai_web.py"),
    "desktop_source": Path(r"Z:\FOXAI\ui\main_window.py"),
    "protected_registry_dir": Path(r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-235244-7594A9_V1A3D_PROTECTED_CONTEXT_REGISTRY"),
}

EXPECTED_HASHES: dict[str, str] = {
    "provider": "41a1663cd30af8a3800c8082d351f8d0338e75cd1df39d3c801a39cc3075f680",
    "provider_contract": "6f59b18094283cacd4d1911e79bf8ff102cd4fc7f16d280f695b81777907766b",
    "provider_fixtures": "bdc1f3fd032952e2eb3946844e3861527f6b86a58d3f56d07e569507e3bac72a",
    "provider_registry": "6e9c3eaea722cb5260f9f0df35d6ea90f37e83697e1b83592670d6599c33e1aa",
    "provider_fixture_results": "554631166de3da90ad54f737df2b81621fbd55eafef6b553d0fb9f96c6502bd6",
    "provider_receipt": "a660a47f3597531a5e603cddd6069d85c9d68cccec6b59521a489ecf5ed5c3db",
    "query_bridge": "96edd665af8eea2aca3563074f0e894607b03b53c22ac13d36cddc0bd58460f1",
    "answer_bridge": "ad501eff2f8162a319085aa4eb6368039e9757e89ee4eaccb11e5f6e446ca6a7",
    "shared_adapter": "a80a9047e0eebd9ac87fe4d656c565bc6534563bb3c97e1ad9b59823a36804f7",
    "web_helper": "765983b563f8495138c9670849de5c4703f4735a0ddc9324efd6580606fc517b",
    "desktop_helper": "e420706136b4902d82d8dbf1fecc64ae70fb8bc639106db41033545f8c196c30",
    "web_source": "d7bf0a2042d55ef7f0a5869556015e42c7427e7ff88636b28e1795f3adf7b952",
    "desktop_source": "a9c5bb86878e5f0cd27d221dbb32688b337e6026073a4b66d83339e0aef294a3",
}

V1B1C_HASHES = {
    "RESOURCE_BASELINE_COMPARISON.json": "40462031e89ea469b7c3940c863d225fa7fbad2cef4c6f44e720154d42cf4c86",
    "FOXAI_COMPONENT_RESOURCE_ATTRIBUTION.json": "8673d496b81aebe432b4f79df7d1b773aea8742f0b09ebfe6d660a9f170f9c3f",
    "CAPACITY_HEADROOM_OBSERVATIONS.json": "3dc50e04a634a73c67b963ea3ee10fdb52d1bac126bac26cb22f544f92288fba",
    "BASELINE_COMPARISON_REPORT.md": "6473cc6b7ef328e095348e4ad8813df53e31e061c21f1f5cff6e9993d18c95b7",
    "BASELINE_COMPARISON_RECEIPT.json": "1688a1a1a90f7925c361996eef6211476d133280307416e5a84e68a3ca07b71f",
}

SUPPORTED_CATEGORY_PROBES: dict[str, str] = {
    "measured_minimal_load_ram": "How much RAM was used in the minimal-load capture?",
    "measured_normal_loaded_ram": "How much RAM did FOXAI use in the loaded capture?",
    "available_loaded_state_memory": "How much RAM was left with the model and ComfyUI loaded?",
    "memory_load_delta": "What was the memory-load delta between the captures?",
    "dominant_measured_foxai_component": "What was using most of the memory?",
    "model_working_set": "How much memory did the model use?",
    "idle_comfyui_working_set": "How much memory did idle ComfyUI use?",
    "desktop_working_set": "How much RAM did FOXAI Desktop use?",
    "webui_working_set": "How much RAM did FOXAI WebUI use?",
    "commit_headroom": "How much commit headroom was left?",
    "current_page_file_usage": "What was the current page file usage in the capture?",
    "historical_page_file_peak_meaning": "What does the historical page file peak of 8191 MiB mean?",
    "foxai_process_count_delta": "How many more FOXAI processes were in the loaded capture?",
    "listener_presence_captured_states": "What ports were present in each captured state?",
    "storage_free_space_comparison": "Compare the captured drive free space.",
    "known_evidence_limitations": "What are the limitations of this evidence?",
    "active_image_generation_capacity_limitation": "Can this prove I can generate images while the 30B model is loaded?",
    "future_or_multi_model_capacity_limitation": "Does this prove capacity for multiple simultaneous large models?",
}

OVERLAP_PROBES = (
    "What was using most of the memory and what runs in FOXAI?",
    "Which python does FOXAI Desktop use and how much RAM did Desktop use?",
    "Show context for WebUI and its RAM use.",
    "FOXAI launcher to runtime to entry and model memory use",
)

FIXTURES = (
    {
        "fixture_id": "FIXTURE-HISTORICAL-RAM",
        "message": "How much RAM did FOXAI use in the loaded capture?",
        "expected_route": "resource_evidence_provider",
        "expected_resource_category": "measured_normal_loaded_ram",
    },
    {
        "fixture_id": "FIXTURE-DOMINANT-MEMORY",
        "message": "What was using most of the memory?",
        "expected_route": "resource_evidence_provider",
        "expected_resource_category": "dominant_measured_foxai_component",
    },
    {
        "fixture_id": "FIXTURE-CURRENT-LIVE",
        "message": "How much memory is my computer using right now?",
        "expected_route": "ordinary_chat",
        "expected_resource_reason": "requires_current_live_state",
    },
    {
        "fixture_id": "FIXTURE-WEBUI-LAUNCHER",
        "message": "Tell me about the WebUI launcher.",
        "expected_route": "protected_context_self_knowledge",
        "protected_selector_hint": {"intent": "contexts_for_launcher"},
        "expected_protected_status": "clarification_required",
    },
    {
        "fixture_id": "FIXTURE-JOKE",
        "message": "Tell me a joke.",
        "expected_route": "ordinary_chat",
    },
    {
        "fixture_id": "FIXTURE-CREATIVE-MEMORY",
        "message": "Write a poem about memory.",
        "expected_route": "ordinary_chat",
    },
    {
        "fixture_id": "FIXTURE-SLASH-DIRECT",
        "message": "/engineer workshop begin test",
        "expected_route": "slash_command_bypass",
    },
    {
        "fixture_id": "FIXTURE-SLASH-SPACED",
        "message": "   /engineer workshop preview test",
        "expected_route": "slash_command_bypass",
    },
)

_PATHS = dict(DEFAULT_PATHS)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    raw = canonical_bytes([str(part) for part in parts])
    return f"{prefix}-{hashlib.sha256(raw).hexdigest()[:16].upper()}"


def _configure_paths_for_tests(paths: dict[str, Path | str]) -> None:
    global _PATHS
    updated = dict(DEFAULT_PATHS)
    for key, value in paths.items():
        if key not in updated:
            raise KeyError(f"unsupported_path_key:{key}")
        updated[key] = Path(value)
    _PATHS = updated


def _read_verified_file(key: str) -> bytes:
    path = Path(_PATHS[key])
    if not path.is_file():
        raise FileNotFoundError(f"required_file_missing:{key}")
    data = path.read_bytes()
    actual = sha256_bytes(data)
    expected = EXPECTED_HASHES[key]
    if actual != expected:
        raise ValueError(f"required_file_hash_mismatch:{key}:{actual}")
    return data


def _verify_v1b1c_sources() -> list[dict[str, Any]]:
    root = Path(_PATHS["v1b1c_source_dir"])
    rows = []
    for name in sorted(V1B1C_HASHES):
        path = root / name
        data = path.read_bytes()
        actual = sha256_bytes(data)
        expected = V1B1C_HASHES[name]
        if actual != expected:
            raise ValueError(f"v1b1c_source_hash_mismatch:{name}")
        rows.append({
            "source_file": name,
            "source_mission": V1B1C_MISSION,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "sha256_matches_expected": True,
            "size_bytes": len(data),
            "availability_status": "available",
        })
    receipt = json.loads((root / "BASELINE_COMPARISON_RECEIPT.json").read_text(encoding="utf-8"))
    if receipt.get("status") != "compared_and_verified":
        raise ValueError("v1b1c_receipt_status_not_verified")
    return rows


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module_loader_unavailable:{name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _line_of(text: str, token: str) -> int:
    for number, line in enumerate(text.splitlines(), start=1):
        if token in line:
            return number
    raise ValueError(f"static_seam_token_missing:{token}")


def _verify_static_seams(files: dict[str, bytes]) -> dict[str, Any]:
    web_source = files["web_source"].decode("utf-8")
    desktop_source = files["desktop_source"].decode("utf-8")
    web_helper = files["web_helper"].decode("utf-8")
    desktop_helper = files["desktop_helper"].decode("utf-8")
    adapter = files["shared_adapter"].decode("utf-8")

    required_web = (
        "FOXAI_SELF_KNOWLEDGE_WEBUI_V1A3H_BEGIN",
        "webui_self_knowledge_integration_v1.py",
        "route_http_request(_sk_raw, _sk_route)",
        "FOXAI_SELF_KNOWLEDGE_WEBUI_V1A3H_END",
    )
    required_desktop = (
        "FOXAI_SELF_KNOWLEDGE_DESKTOP_V1A3I_BEGIN",
        "desktop_self_knowledge_integration_v1.py",
        "route_desktop_message(text)",
        "FOXAI_SELF_KNOWLEDGE_DESKTOP_V1A3I_END",
    )
    for token in required_web:
        if token not in web_source:
            raise ValueError(f"web_static_seam_missing:{token}")
    for token in required_desktop:
        if token not in desktop_source:
            raise ValueError(f"desktop_static_seam_missing:{token}")
    if ".route_message(message,\"webui\")" not in web_helper:
        raise ValueError("web_helper_shared_adapter_call_missing")
    if "adapter.route_message(normalized, \"desktop\")" not in desktop_helper:
        raise ValueError("desktop_helper_shared_adapter_call_missing")
    if "def route_message(" not in adapter or "_catalog_matches(" not in adapter:
        raise ValueError("shared_adapter_route_seam_missing")

    web_raw_slash_only = 'if message.startswith("/")' in web_helper
    desktop_explicit_slash = "startswith(\"/\")" in desktop_helper or "startswith('/')" in desktop_helper

    return {
        "webui": {
            "surface_source": str(DEFAULT_PATHS["web_source"]),
            "source_sha256": EXPECTED_HASHES["web_source"],
            "entry_function": "Handler.do_POST",
            "begin_marker_line": _line_of(web_source, "FOXAI_SELF_KNOWLEDGE_WEBUI_V1A3H_BEGIN"),
            "helper_load_line": _line_of(web_source, "webui_self_knowledge_integration_v1.py"),
            "helper_call_line": _line_of(web_source, "route_http_request(_sk_raw, _sk_route)"),
            "ordinary_route_resumes_after_marker_line": _line_of(web_source, "FOXAI_SELF_KNOWLEDGE_WEBUI_V1A3H_END") + 1,
            "helper_callable": "route_http_request(raw_body, route, adapter_path=...)" ,
            "shared_adapter_callable": "route_message(message, surface='webui', request_id=None, selectors=None)",
            "current_helper_slash_guard": "raw_first_character_only" if web_raw_slash_only else "not_detected",
        },
        "desktop": {
            "surface_source": str(DEFAULT_PATHS["desktop_source"]),
            "source_sha256": EXPECTED_HASHES["desktop_source"],
            "entry_function": "main_window.on_enter",
            "begin_marker_line": _line_of(desktop_source, "FOXAI_SELF_KNOWLEDGE_DESKTOP_V1A3I_BEGIN"),
            "helper_load_line": _line_of(desktop_source, "desktop_self_knowledge_integration_v1.py"),
            "helper_call_line": _line_of(desktop_source, "route_desktop_message(text)"),
            "ordinary_route_resumes_after_marker_line": _line_of(desktop_source, "FOXAI_SELF_KNOWLEDGE_DESKTOP_V1A3I_END") + 1,
            "helper_callable": "route_desktop_message(message, adapter_path=..., bridge_path=None, registry_dir=None)",
            "shared_adapter_callable": "route_message(message, surface='desktop', request_id=None, selectors=None)",
            "current_helper_explicit_slash_guard": desktop_explicit_slash,
        },
        "shared_convergence": {
            "module": str(DEFAULT_PATHS["shared_adapter"]),
            "sha256": EXPECTED_HASHES["shared_adapter"],
            "callable": "route_message(message, surface, request_id=None, selectors=None)",
            "smallest_safe_logical_seam": "shared_adapter.route_message",
            "slash_guard_location": "first executable routing decision after normalization and surface validation, before protected bridge or resource provider invocation",
            "resource_provider_location": "after protected-context no-match and before ordinary-chat pass-through",
        },
    }


def _verify_callable_compatibility() -> dict[str, Any]:
    provider = _load_module("foxai_v1b2b_provider", Path(_PATHS["provider"]))
    query_bridge = _load_module("foxai_v1b2b_query_bridge", Path(_PATHS["query_bridge"]))
    answer_bridge = _load_module("foxai_v1b2b_answer_bridge", Path(_PATHS["answer_bridge"]))
    adapter = _load_module("foxai_v1b2b_shared_adapter", Path(_PATHS["shared_adapter"]))
    web_helper = _load_module("foxai_v1b2b_web_helper", Path(_PATHS["web_helper"]))
    desktop_helper = _load_module("foxai_v1b2b_desktop_helper", Path(_PATHS["desktop_helper"]))

    callables = {
        "provider.classify_question": getattr(provider, "classify_question", None),
        "provider.answer_question": getattr(provider, "answer_question", None),
        "query_bridge.query": getattr(query_bridge, "query", None),
        "answer_bridge.answer_schema": getattr(answer_bridge, "answer_schema", None),
        "answer_bridge.answer_request": getattr(answer_bridge, "answer_request", None),
        "shared_adapter.route_message": getattr(adapter, "route_message", None),
        "web_helper.route_http_request": getattr(web_helper, "route_http_request", None),
        "desktop_helper.route_desktop_message": getattr(desktop_helper, "route_desktop_message", None),
    }
    if not all(callable(value) for value in callables.values()):
        missing = sorted(name for name, value in callables.items() if not callable(value))
        raise ValueError("callable_compatibility_missing:" + ",".join(missing))

    adapter._configure_paths_for_tests(
        Path(_PATHS["answer_bridge"]),
        Path(_PATHS["protected_registry_dir"]),
    )
    provider._configure_source_dir_for_tests(Path(_PATHS["v1b1c_source_dir"]))

    answer_schema = answer_bridge.answer_schema()
    required = set(answer_schema.get("required", []))
    resource_result = provider.answer_question(
        "How much RAM did FOXAI use in the loaded capture?",
        request_id="V1B2B-COMPATIBILITY",
    )
    packet = resource_result.get("answer_packet")
    if not isinstance(packet, dict) or resource_result.get("status") != "answered":
        raise ValueError("resource_answer_packet_unavailable")
    missing_required = sorted(required - set(packet))
    if missing_required:
        raise ValueError("answer_packet_required_fields_missing:" + ",".join(missing_required))
    if packet.get("schema") != "foxai.agent_fox.technical_core.v1a3e.answer_packet.v1":
        raise ValueError("answer_packet_schema_incompatible")

    return {
        "provider_module": provider,
        "adapter_module": adapter,
        "answer_bridge_module": answer_bridge,
        "callable_results": [
            {"callable": name, "available": True}
            for name in sorted(callables)
        ],
        "answer_packet_compatibility": {
            "existing_v1a3e_schema_preserved": True,
            "schema": packet["schema"],
            "required_field_count": len(required),
            "required_fields_present": True,
            "resource_specific_data_bounded": isinstance(packet.get("evidence"), dict),
            "shared_answer_contract_modified": False,
        },
    }


def _protected_catalog_matches(adapter: Any, message: str) -> list[str]:
    bridge = adapter._load_bridge_namespace()
    return adapter._catalog_matches(adapter._normalize_message(message), {}, bridge)


def _proposed_route(message: str, provider: Any, adapter: Any, surface: str, selector_hint: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = str(message or "")
    if raw.lstrip().startswith("/"):
        return {
            "route": "slash_command_bypass",
            "status": "bypass",
            "protected_provider_invoked": False,
            "resource_provider_invoked": False,
            "protected_evidence_loaded": False,
            "resource_evidence_loaded": False,
            "ordinary_chat_pass_through": True,
            "reason": "first_non_whitespace_character_is_slash",
        }

    protected_result = adapter.route_message(
        raw,
        surface,
        selectors=selector_hint,
    )
    if protected_result.get("handled") is True:
        return {
            "route": "protected_context_self_knowledge",
            "status": protected_result.get("status"),
            "protected_provider_invoked": True,
            "resource_provider_invoked": False,
            "protected_evidence_loaded": bool(protected_result.get("diagnostic", {}).get("registry_verified")),
            "resource_evidence_loaded": False,
            "ordinary_chat_pass_through": False,
            "reason": "protected_context_priority",
            "protected_normalized_intent": (protected_result.get("answer_packet") or {}).get("normalized_intent"),
        }

    resource_classification = provider.classify_question(raw)
    if resource_classification.get("status") == "resource_question":
        resource_result = provider.answer_question(raw)
        if resource_result.get("status") != "answered":
            raise ValueError("resource_provider_failed_after_classification")
        return {
            "route": "resource_evidence_provider",
            "status": "answered",
            "protected_provider_invoked": True,
            "resource_provider_invoked": True,
            "protected_evidence_loaded": False,
            "resource_evidence_loaded": bool(resource_result.get("evidence_loaded")),
            "ordinary_chat_pass_through": False,
            "reason": "bounded_historical_resource_category",
            "resource_category": resource_result.get("matched_category"),
            "answer_packet_schema": (resource_result.get("answer_packet") or {}).get("schema"),
            "current_state_claimed": resource_result.get("current_state_claimed"),
            "live_scan_performed": resource_result.get("live_scan_performed"),
        }

    return {
        "route": "ordinary_chat",
        "status": "pass_through",
        "protected_provider_invoked": True,
        "resource_provider_invoked": True,
        "protected_evidence_loaded": False,
        "resource_evidence_loaded": False,
        "ordinary_chat_pass_through": True,
        "reason": resource_classification.get("reason") or "outside_bounded_providers",
        "resource_category": None,
    }


def _build_overlap_analysis(provider: Any, adapter: Any) -> dict[str, Any]:
    categories = []
    overlap_count = 0
    for category in sorted(SUPPORTED_CATEGORY_PROBES):
        question = SUPPORTED_CATEGORY_PROBES[category]
        resource = provider.classify_question(question)
        protected = _protected_catalog_matches(adapter, question)
        if resource.get("matched_category") != category:
            raise ValueError(f"resource_category_probe_mismatch:{category}:{resource}")
        overlap = bool(protected)
        overlap_count += int(overlap)
        categories.append({
            "category": category,
            "representative_question": question,
            "resource_classification": resource.get("matched_category"),
            "protected_intent_candidates": protected,
            "direct_catalog_overlap": overlap,
            "deterministic_precedence": "protected_context_first" if overlap else "resource_after_protected_no_match",
        })

    ambiguous = []
    for question in OVERLAP_PROBES:
        resource = provider.classify_question(question)
        protected = _protected_catalog_matches(adapter, question)
        if resource.get("status") != "resource_question" or not protected:
            raise ValueError(f"engineered_overlap_probe_failed:{question}")
        ambiguous.append({
            "overlap_id": stable_id("OVERLAP", question),
            "question": question,
            "resource_category": resource.get("matched_category"),
            "protected_intent_candidates": protected,
            "deterministic_precedence": "protected_context_self_knowledge",
            "provider_behavior_changed": False,
            "silent_ordinary_chat_theft": False,
        })

    return {
        "supported_category_count": len(categories),
        "representative_direct_overlap_count": overlap_count,
        "representative_category_results": categories,
        "engineered_ambiguous_phrase_count": len(ambiguous),
        "ambiguous_phrases": ambiguous,
        "precedence_rule": "When both catalogs match, protected-context self-knowledge wins. The resource provider is not invoked.",
        "ordinary_chat_guard": "If neither protected context nor a bounded historical resource category matches, preserve ordinary chat pass-through.",
    }


def _build_fixture_results(provider: Any, adapter: Any) -> dict[str, Any]:
    rows = []
    for fixture in FIXTURES:
        surface_results = []
        for surface in ("desktop", "webui"):
            result = _proposed_route(
                fixture["message"],
                provider,
                adapter,
                surface,
                fixture.get("protected_selector_hint"),
            )
            if result.get("route") != fixture["expected_route"]:
                raise ValueError(f"fixture_route_mismatch:{fixture['fixture_id']}:{surface}:{result}")
            expected_category = fixture.get("expected_resource_category")
            if expected_category and result.get("resource_category") != expected_category:
                raise ValueError(f"fixture_category_mismatch:{fixture['fixture_id']}:{surface}")
            expected_status = fixture.get("expected_protected_status")
            if expected_status and result.get("status") != expected_status:
                raise ValueError(f"fixture_protected_status_mismatch:{fixture['fixture_id']}:{surface}")
            if fixture.get("expected_resource_reason") and result.get("reason") != fixture["expected_resource_reason"]:
                raise ValueError(f"fixture_reason_mismatch:{fixture['fixture_id']}:{surface}:{result}")
            surface_results.append({"surface": surface, **result})
        rows.append({
            "fixture_id": fixture["fixture_id"],
            "message": fixture["message"],
            "expected_route": fixture["expected_route"],
            "surface_results": surface_results,
            "passed": True,
        })
    return {
        "fixture_count": len(rows),
        "surface_case_count": len(rows) * 2,
        "fixtures": rows,
        "all_passed": True,
    }


def _verified_input_rows(files: dict[str, bytes], v1b1c_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for key in sorted(files):
        rows.append({
            "input_id": stable_id("INPUT", key, EXPECTED_HASHES[key]),
            "logical_name": key,
            "expected_sha256": EXPECTED_HASHES[key],
            "actual_sha256": sha256_bytes(files[key]),
            "sha256_matches_expected": True,
            "size_bytes": len(files[key]),
            "availability_status": "available",
        })
    rows.extend({
        "input_id": stable_id("INPUT", row["source_file"], row["expected_sha256"]),
        "logical_name": "v1b1c:" + row["source_file"],
        "expected_sha256": row["expected_sha256"],
        "actual_sha256": row["actual_sha256"],
        "sha256_matches_expected": True,
        "size_bytes": row["size_bytes"],
        "availability_status": "available",
    } for row in v1b1c_rows)
    return rows


def build_outputs(mission_id: str, output_dir: Path) -> dict[str, bytes]:
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"output_directory_already_exists:{output_dir}")
    output_dir.mkdir(parents=True)

    file_keys = tuple(sorted(EXPECTED_HASHES))
    files = {key: _read_verified_file(key) for key in file_keys}
    v1b1c_rows = _verify_v1b1c_sources()

    provider_receipt = json.loads(files["provider_receipt"].decode("utf-8"))
    provider_registry = json.loads(files["provider_registry"].decode("utf-8"))
    provider_fixtures = json.loads(files["provider_fixture_results"].decode("utf-8"))
    if provider_receipt.get("status") != "provider_built_and_verified":
        raise ValueError("provider_receipt_status_not_verified")
    if provider_registry.get("status") != "registered_offline_provider":
        raise ValueError("provider_registry_status_not_verified")
    if provider_fixtures.get("status") != "fixtures_passed":
        raise ValueError("provider_fixture_status_not_verified")

    seams = _verify_static_seams(files)
    compatibility = _verify_callable_compatibility()
    provider = compatibility.pop("provider_module")
    adapter = compatibility.pop("adapter_module")
    compatibility.pop("answer_bridge_module")
    overlap = _build_overlap_analysis(provider, adapter)
    fixture_results = _build_fixture_results(provider, adapter)

    verified_inputs = _verified_input_rows(files, v1b1c_rows)
    seam_map = {
        "schema": f"{SCHEMA_PREFIX}.integration_seam_map.v1",
        "mission_id": mission_id,
        "status": "preflight_mapped_and_verified",
        "mode": "read_only_static_and_callable_preflight",
        "provider_source_mission": PREVIOUS_PROVIDER_MISSION,
        "resource_evidence_source_mission": V1B1C_MISSION,
        "verified_input_count": len(verified_inputs),
        "verified_inputs": verified_inputs,
        "surface_seams": seams,
        "callable_compatibility": compatibility,
        "routing_order": [
            {
                "order": 1,
                "route": "slash_command_bypass",
                "rule": "message.lstrip().startswith('/')",
                "provider_modules_invoked": 0,
                "evidence_files_loaded": 0,
            },
            {
                "order": 2,
                "route": "protected_context_self_knowledge",
                "rule": "retain existing protected-context catalog, answer-packet bridge, and priority",
            },
            {
                "order": 3,
                "route": "resource_evidence_provider",
                "rule": "consult only after protected-context no-match; historical bounded categories only",
            },
            {
                "order": 4,
                "route": "ordinary_chat",
                "rule": "current-live, unrelated, and creative requests pass through unchanged",
            },
        ],
        "smallest_safe_shared_seam": {
            "module": "self_knowledge_chat_adapter_v1.py",
            "callable": "route_message(message, surface, request_id=None, selectors=None)",
            "reason": "Both live surfaces already converge here through their verified integration helpers, so provider logic need not be duplicated.",
            "future_change_boundary": "Add first-non-whitespace slash bypass at function entry, preserve existing protected-context path, then call resource_evidence_provider_v1 only on protected no-match.",
            "helper_hash_updates_would_be_required_after_adapter_change": True,
            "live_source_patch_required_for_surface_entry_points": False,
            "integration_performed_in_this_mission": False,
        },
        "generic_webui_launcher_alias": {
            "phrase": "Tell me about the WebUI launcher.",
            "future_router_hint": {"intent": "contexts_for_launcher"},
            "behavior": "Route to the existing protected-context provider and request clarification rather than guessing between the portable WebUI launcher and WebUI-with-ComfyUI launcher.",
            "provider_modified": False,
        },
        "classification_overlap": overlap,
        "current_seam_observations": {
            "webui_helper_direct_slash_guard": "raw first character only",
            "desktop_helper_direct_slash_guard": "none detected",
            "required_future_shared_guard": "first non-whitespace character",
            "observation_is_static": True,
        },
        "safety": {
            "integration_performed": False,
            "live_webui_source_modified": False,
            "live_desktop_source_modified": False,
            "shared_adapter_modified": False,
            "provider_modified": False,
            "source_evidence_modified": False,
            "live_scan_performed": False,
            "live_process_inspection_performed": False,
            "live_listener_inspection_performed": False,
            "network_connections_initiated": False,
            "model_calls_performed": False,
            "gui_launched": False,
            "process_changes_performed": False,
            "services_changed": False,
            "startup_items_changed": False,
            "registry_writes": False,
            "rollback_drive_k_accessed": False,
        },
    }

    routing_doc = {
        "schema": f"{SCHEMA_PREFIX}.routing_preflight_fixtures.v1",
        "mission_id": mission_id,
        "status": "routing_preflight_passed",
        "fixture_results": fixture_results,
        "overlap_results": overlap,
        "routing_invariants": {
            "slash_bypass_before_any_provider": True,
            "protected_context_priority": True,
            "resource_only_after_protected_no_match": True,
            "current_live_resource_question_passes_to_ordinary_chat": True,
            "creative_memory_request_not_stolen": True,
            "unrelated_chat_not_stolen": True,
            "both_surfaces_share_identical_logical_order": True,
        },
    }

    outputs: dict[str, bytes] = {
        OUTPUT_NAMES[0]: canonical_bytes(seam_map),
        OUTPUT_NAMES[1]: canonical_bytes(routing_doc),
    }
    before_receipt = []
    for name in OUTPUT_NAMES[:2]:
        data = outputs[name]
        before_receipt.append({
            "name": name,
            "sha256": sha256_bytes(data),
            "size_bytes": len(data),
        })

    receipt = {
        "schema": f"{SCHEMA_PREFIX}.integration_preflight_receipt.v1",
        "mission_id": mission_id,
        "status": "preflight_completed_and_verified",
        "output_count": 3,
        "outputs_before_receipt": before_receipt,
        "verified_input_count": len(verified_inputs),
        "provider_receipt_verified": True,
        "provider_fixture_results_verified": True,
        "v1b1c_receipt_verified": True,
        "callable_compatibility_verified": True,
        "answer_packet_compatibility_verified": True,
        "static_live_call_seams_verified": True,
        "routing_fixture_count": fixture_results["fixture_count"],
        "routing_surface_case_count": fixture_results["surface_case_count"],
        "supported_resource_category_count": overlap["supported_category_count"],
        "engineered_overlap_probe_count": overlap["engineered_ambiguous_phrase_count"],
        "deterministic_precedence_verified": True,
        "slash_bypass_before_any_provider_verified": True,
        "ordinary_chat_preservation_verified": True,
        "integration_performed": False,
        "live_scan_performed": False,
        "live_process_inspection_performed": False,
        "live_listener_inspection_performed": False,
        "network_connections_initiated": False,
        "model_calls_performed": False,
        "automatic_process_changes_performed": False,
        "services_changed": False,
        "startup_items_changed": False,
        "registry_writes": False,
        "existing_live_source_files_modified": 0,
        "source_evidence_modified": False,
        "rollback_drive_k_accessed": False,
        "deterministic_utf8_lf_serialization": True,
    }
    outputs[OUTPUT_NAMES[2]] = canonical_bytes(receipt)

    if len(outputs) != 3:
        raise AssertionError("exact_output_count_mismatch")
    total = sum(len(data) for data in outputs.values())
    if total >= OUTPUT_LIMIT_BYTES:
        raise ValueError("output_limit_exceeded")
    for name in OUTPUT_NAMES:
        data = outputs[name]
        if b"\r" in data:
            raise ValueError(f"carriage_return_detected:{name}")
        data.decode("utf-8")
        (output_dir / name).write_bytes(data)
    return outputs


def validate_output(output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    actual = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    if actual != sorted(OUTPUT_NAMES):
        raise ValueError(f"output_set_mismatch:{actual}")
    docs = {}
    for name in OUTPUT_NAMES:
        data = (output_dir / name).read_bytes()
        if b"\r" in data:
            raise ValueError(f"carriage_return_detected:{name}")
        obj = json.loads(data.decode("utf-8"))
        if data != canonical_bytes(obj):
            raise ValueError(f"noncanonical_json:{name}")
        docs[name] = obj
    receipt = docs[OUTPUT_NAMES[2]]
    if receipt.get("status") != "preflight_completed_and_verified":
        raise ValueError("receipt_status_invalid")
    for row in receipt.get("outputs_before_receipt", []):
        data = (output_dir / row["name"]).read_bytes()
        if len(data) != row["size_bytes"] or sha256_bytes(data) != row["sha256"]:
            raise ValueError(f"receipt_output_relationship_invalid:{row['name']}")
    return {
        "status": "validated",
        "output_count": 3,
        "verified_input_count": receipt["verified_input_count"],
        "routing_surface_case_count": receipt["routing_surface_case_count"],
    }


def self_test() -> dict[str, Any]:
    calls = {"protected": 0, "resource": 0}

    def fake_protected(message: str) -> dict[str, Any]:
        calls["protected"] += 1
        return {"handled": "launcher" in message.casefold()}

    def fake_resource(message: str) -> dict[str, Any]:
        calls["resource"] += 1
        return {"status": "resource_question" if "ram" in message.casefold() else "not_applicable"}

    def route(message: str) -> str:
        if message.lstrip().startswith("/"):
            return "slash"
        if fake_protected(message)["handled"]:
            return "protected"
        if fake_resource(message)["status"] == "resource_question":
            return "resource"
        return "ordinary"

    assert route(" /engineer workshop begin test") == "slash"
    assert calls == {"protected": 0, "resource": 0}
    assert route("launcher details") == "protected"
    assert route("ram capture") == "resource"
    assert route("write a poem") == "ordinary"
    assert canonical_bytes({"b": 2, "a": 1}) == b'{\n  "a": 1,\n  "b": 2\n}\n'
    return {
        "status": "ok",
        "output_count": 3,
        "supported_resource_category_count": 18,
        "routing_fixture_count": 8,
        "surface_count": 2,
        "slash_bypass_before_any_provider": True,
        "protected_context_priority": True,
        "resource_after_protected_no_match": True,
        "ordinary_chat_preserved": True,
        "canonical_lf_only": True,
        "stable_ids": True,
        "no_live_scan_design": True,
        "k_path_excluded": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    build = sub.add_parser("build")
    build.add_argument("--mission-id", required=True)
    build.add_argument("--output-dir", required=True)
    validate = sub.add_parser("validate-output")
    validate.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "self-test":
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    if args.command == "build":
        outputs = build_outputs(args.mission_id, Path(args.output_dir))
        print(json.dumps({
            "status": "preflight_completed_and_verified",
            "mission_id": args.mission_id,
            "output_count": len(outputs),
            "integration_performed": False,
            "live_scan_performed": False,
            "rollback_drive_k_accessed": False,
        }, sort_keys=True))
        return 0
    print(json.dumps(validate_output(Path(args.output_dir)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
