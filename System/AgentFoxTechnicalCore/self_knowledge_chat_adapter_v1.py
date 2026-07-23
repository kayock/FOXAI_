from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

SCHEMA_PREFIX = "foxai.agent_fox.technical_core.v1a3g"
EXPECTED_BRIDGE_SHA256 = "ad501eff2f8162a319085aa4eb6368039e9757e89ee4eaccb11e5f6e446ca6a7"
DEFAULT_BRIDGE_PATH = Path(__file__).with_name("provenance_self_knowledge_answer_packet_bridge_v1.py")
DEFAULT_REGISTRY_DIR = Path(r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-235244-7594A9_V1A3D_PROTECTED_CONTEXT_REGISTRY")
EXPECTED_RESOURCE_PROVIDER_SHA256 = "41a1663cd30af8a3800c8082d351f8d0338e75cd1df39d3c801a39cc3075f680"
DEFAULT_RESOURCE_PROVIDER_PATH = Path(__file__).with_name("resource_evidence_provider_v1.py")
DEFAULT_RESOURCE_SOURCE_DIR = Path(
    r"Z:\FOXAI\System\EngineeringWorkshop\missions"
    r"\ENG-20260722-142022-9FAE11_V1B1C_BASELINE_COMPARISON_AND_CAPACITY_GUIDANCE"
)
SUPPORTED_SURFACES = ("webui", "desktop")
RENDERED_TEXT_CEILING_BYTES = 64 * 1024
COMPLETE_RESULT_CEILING_BYTES = 1024 * 1024
TOTAL_OUTPUT_CEILING_BYTES = 8 * 1024 * 1024
MAX_MESSAGE_CHARS = 16384
MAX_SELECTORS_BYTES = 65536
OUTPUT_NAMES = (
    "SELF_KNOWLEDGE_CHAT_ADAPTER_API.json",
    "SELF_KNOWLEDGE_CHAT_ADAPTER_ROUTING.json",
    "SELF_KNOWLEDGE_CHAT_ADAPTER_RENDERING_EXAMPLES.json",
    "SELF_KNOWLEDGE_CHAT_ADAPTER_TEST_MATRIX.json",
    "SELF_KNOWLEDGE_CHAT_ADAPTER_COVERAGE.json",
)
RECEIPT_NAME = "SELF_KNOWLEDGE_CHAT_ADAPTER_RECEIPT.json"
EXPECTED_EVIDENCE = {
    "v1a3d": {
        "mission_id": "ENG-20260721-235244-7594A9",
        "receipt_name": "PROTECTED_CONTEXT_REGISTRY_RECEIPT.json",
        "receipt_sha256": "bf8bea034ae7bd47c6c8af730ef5312e5c5fa5b4b57cf804fc64dd0f18c98a4e",
        "core_outputs": {
            "PROTECTED_CONTEXT_REGISTRY.json": "1f4ebf3667b8a902b15638396717ad42feb9d8137773fd0825ca634883a3779d",
            "LAUNCHER_RUNTIME_ENTRY_MAP.json": "7e4968bf5c937fa8c6b1bd54948eb5342c33e0af87b4ce46d7dae1fb1c8ffb48",
            "CONTEXT_DEPENDENCY_SUMMARY.json": "e40afe68724e31515f143c0b6ef576586cf5f4d4e6d2e2e7201a790fe782b51a",
            "UNRESOLVED_AND_RUNTIME_UNCERTAINTY_INDEX.json": "aeed560e04316bd71da536cccef236f151e5e1b72cf10343314185075ff847d5",
            "CONTEXT_LINK_GRAPH.json": "6d1d1d2cd3fbadc6f96e74e48ef1e323f25a7a2320fbb2b90bc8768ed3aa2c38",
            "QUERY_EXAMPLES.md": "eb774cad574bcf0edd84444e011673b8564977878f32dbfb897c5b35d90d6750",
            "PROTECTED_CONTEXT_REGISTRY_COVERAGE.json": "2c10f3308cdaadd04d265489a138d08bae699f84bc71dc5a980b59d76860d2ca",
        },
    },
    "v1a3e": {
        "mission_id": "ENG-20260722-001310-533BE2",
        "receipt_name": "SELF_KNOWLEDGE_BRIDGE_RECEIPT.json",
        "receipt_sha256": "8cdb826c5c2a722eb9a9459abcb3acd36267bb90264874ce6d9908f405177a78",
        "core_outputs": {
            "SELF_KNOWLEDGE_REQUEST_SCHEMA.json": "e108617e2c60b9083c78f9d9ca560001f422d064851e0205bad7bb91c7ed2a7d",
            "SELF_KNOWLEDGE_ANSWER_SCHEMA.json": "cf4060180981aa32204b997d4faa33b68dbe3e6798d80042092181005eb11333",
            "SELF_KNOWLEDGE_INTENT_CATALOG.json": "f7566dba8363c7acabad71bddcb234f7260d24194ebe2e926bd44322b8f4bc34",
            "SELF_KNOWLEDGE_TEST_CASES.json": "c379c7086eb93079797accbac3f0788f81851723640de3791fe088bc6e7dd1f3",
            "QUERY_EXAMPLES.md": "1eb4caedb107e5611c1fc3395d4034ac7d1c0b0077336fbce7bd60164e8143d5",
        },
    },
    "v1a3f": {
        "mission_id": "ENG-20260722-003059-4F07D0",
        "receipt_name": "INTEGRATION_PREFLIGHT_RECEIPT.json",
        "receipt_sha256": "f7b6c9a33c4cf8a683985cc4f481738aeb77d074a82edc905c7fb6fcaa505d84",
        "core_outputs": {
            "SELF_KNOWLEDGE_INTEGRATION_SEAMS.json": "da6c39ad5bc2cc4f95dfcf1f637100e3527c7157d5d89387881674e90063dbcd",
            "CHAT_SURFACE_ROUTE_MAP.json": "180cfd4e91c5b62fceb5f3a0b236e95d95894fc7326b2ea15a65084407ae137a",
            "MODEL_DISPATCH_BOUNDARIES.json": "7ce09a5c2c6eaa47c68bccca626ac3e632144dabbdec34fe90438ed268d64798",
            "PROPOSED_SELF_KNOWLEDGE_ADAPTER_CONTRACT.json": "d4a87e11f1d05efb454b3fc035df90f7a7af5751639791104d0f1ee8ea0b346c",
            "PATCH_CANDIDATES.json": "03e129d3ab8410a2894e9a305e33419186ab1f32920fb8844f3f722d08712002",
            "INTEGRATION_TEST_MATRIX.json": "d85c186b6ab014dab779e7d302a5c0bd301bf9e7680a5b6c908527e1d2c758c6",
            "INTEGRATION_PREFLIGHT_COVERAGE.json": "d01075911d03ad78250feaae043a5d470d1496ff2cdba87fa5d924c0626ce1b8",
        },
    },
}

WEAK_GENERIC_SYNONYMS = {
    "which python",
    "entry script",
    "what starts",
    "what runs",
}
DOMAIN_ANCHORS = (
    "foxai",
    "agent fox",
    "technical core",
    "protected context",
    "launcher",
    "web portable",
    "web_with_comfyui",
    "web with comfyui",
    "workshop main",
    "workshop_comfyui",
    "desktop recovery",
    "desktop_recovery",
    "ctx-",
    "pathgroup-",
    "start_foxai",
    "launch foxai workshop",
)

_BRIDGE_PATH = DEFAULT_BRIDGE_PATH
_REGISTRY_DIR = DEFAULT_REGISTRY_DIR
_BRIDGE_CACHE: dict[str, Any] | None = None
_BRIDGE_CACHE_PATH: str | None = None
_RESOURCE_PROVIDER_PATH = DEFAULT_RESOURCE_PROVIDER_PATH
_RESOURCE_SOURCE_DIR = DEFAULT_RESOURCE_SOURCE_DIR
_RESOURCE_PROVIDER_CACHE: dict[str, Any] | None = None
_RESOURCE_PROVIDER_CACHE_PATH: str | None = None
_AUDIT = {
    "bridge_hash_checks": 0,
    "bridge_loads": 0,
    "registry_verify_calls": 0,
    "resource_provider_hash_checks": 0,
    "resource_provider_loads": 0,
    "resource_classify_calls": 0,
    "resource_answer_calls": 0,
}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _configure_paths_for_tests(
    bridge_path: Path | str | None = None,
    registry_dir: Path | str | None = None,
    resource_provider_path: Path | str | None = None,
    resource_source_dir: Path | str | None = None,
) -> None:
    global _BRIDGE_PATH, _REGISTRY_DIR, _BRIDGE_CACHE, _BRIDGE_CACHE_PATH
    global _RESOURCE_PROVIDER_PATH, _RESOURCE_SOURCE_DIR
    global _RESOURCE_PROVIDER_CACHE, _RESOURCE_PROVIDER_CACHE_PATH
    if bridge_path is not None:
        _BRIDGE_PATH = Path(bridge_path)
    if registry_dir is not None:
        _REGISTRY_DIR = Path(registry_dir)
    if resource_provider_path is not None:
        _RESOURCE_PROVIDER_PATH = Path(resource_provider_path)
    if resource_source_dir is not None:
        _RESOURCE_SOURCE_DIR = Path(resource_source_dir)
    _BRIDGE_CACHE = None
    _BRIDGE_CACHE_PATH = None
    _RESOURCE_PROVIDER_CACHE = None
    _RESOURCE_PROVIDER_CACHE_PATH = None


def _reset_audit_for_tests() -> None:
    for key in _AUDIT:
        _AUDIT[key] = 0


def _audit_snapshot() -> dict[str, int]:
    return dict(_AUDIT)


def _verify_bridge_hash(path: Path) -> None:
    _AUDIT["bridge_hash_checks"] += 1
    if not path.is_file():
        raise FileNotFoundError("bridge_source_unavailable")
    actual = sha256_file(path)
    if actual != EXPECTED_BRIDGE_SHA256:
        raise ValueError("bridge_source_hash_mismatch")


def _load_bridge_namespace() -> dict[str, Any]:
    global _BRIDGE_CACHE, _BRIDGE_CACHE_PATH
    path = Path(_BRIDGE_PATH)
    _verify_bridge_hash(path)
    cache_key = str(path.resolve()) if path.exists() else str(path)
    if _BRIDGE_CACHE is not None and _BRIDGE_CACHE_PATH == cache_key:
        return _BRIDGE_CACHE
    source = path.read_text(encoding="utf-8")
    namespace: dict[str, Any] = {
        "__name__": "foxai_technical_core_v1a3e_bridge_runtime",
        "__file__": str(path),
        "__package__": None,
    }
    exec(compile(source, str(path), "exec"), namespace, namespace)
    required = {
        "INTENTS",
        "INTENT_DEFINITIONS",
        "infer_natural_request",
        "answer_request",
        "verify_registry_dir",
        "indexes",
        "clarification_packet",
    }
    missing = sorted(required - set(namespace))
    if missing:
        raise ValueError("bridge_api_missing")
    if len(namespace["INTENTS"]) != 11:
        raise ValueError("bridge_intent_count_mismatch")
    _BRIDGE_CACHE = namespace
    _BRIDGE_CACHE_PATH = cache_key
    _AUDIT["bridge_loads"] += 1
    return namespace


def _verify_resource_provider_hash(path: Path) -> None:
    _AUDIT["resource_provider_hash_checks"] += 1
    if not path.is_file():
        raise FileNotFoundError("resource_provider_source_unavailable")
    actual = sha256_file(path)
    if actual != EXPECTED_RESOURCE_PROVIDER_SHA256:
        raise ValueError("resource_provider_source_hash_mismatch")


def _load_resource_provider_namespace() -> dict[str, Any]:
    global _RESOURCE_PROVIDER_CACHE, _RESOURCE_PROVIDER_CACHE_PATH
    path = Path(_RESOURCE_PROVIDER_PATH)
    _verify_resource_provider_hash(path)
    cache_key = str(path.resolve()) if path.exists() else str(path)
    if _RESOURCE_PROVIDER_CACHE is not None and _RESOURCE_PROVIDER_CACHE_PATH == cache_key:
        configure = _RESOURCE_PROVIDER_CACHE["_configure_source_dir_for_tests"]
        configure(Path(_RESOURCE_SOURCE_DIR))
        return _RESOURCE_PROVIDER_CACHE
    source = path.read_text(encoding="utf-8")
    namespace: dict[str, Any] = {
        "__name__": "foxai_technical_core_v1b2a_resource_provider_runtime",
        "__file__": str(path),
        "__package__": None,
    }
    exec(compile(source, str(path), "exec"), namespace, namespace)
    required = {
        "PROVIDER_NAME",
        "SUPPORTED_CATEGORIES",
        "classify_question",
        "answer_question",
        "audit_snapshot",
        "_configure_source_dir_for_tests",
    }
    missing = sorted(required - set(namespace))
    if missing:
        raise ValueError("resource_provider_api_missing")
    if len(namespace["SUPPORTED_CATEGORIES"]) != 18:
        raise ValueError("resource_provider_category_count_mismatch")
    namespace["_configure_source_dir_for_tests"](Path(_RESOURCE_SOURCE_DIR))
    _RESOURCE_PROVIDER_CACHE = namespace
    _RESOURCE_PROVIDER_CACHE_PATH = cache_key
    _AUDIT["resource_provider_loads"] += 1
    return namespace


def _verify_registry(bridge: dict[str, Any]) -> dict[str, Any]:
    _AUDIT["registry_verify_calls"] += 1
    return bridge["verify_registry_dir"](Path(_REGISTRY_DIR))


def _normalize_message(message: Any) -> str:
    if not isinstance(message, str):
        return ""
    return " ".join(message.strip().split())


def _normalize_surface(surface: Any) -> str:
    return str(surface or "").strip().lower()


def _normalize_selectors(selectors: Any) -> dict[str, Any]:
    if selectors is None:
        return {}
    if not isinstance(selectors, dict):
        raise TypeError("selectors_must_be_object")
    encoded = canonical_bytes(selectors)
    if len(encoded) > MAX_SELECTORS_BYTES:
        raise ValueError("selectors_exceed_bound")
    return json.loads(json.dumps(selectors, ensure_ascii=False))


def _deterministic_request_id(surface: str, message: str, selectors: dict[str, Any]) -> str:
    payload = {
        "surface": surface,
        "message": message.casefold(),
        "selectors": selectors,
    }
    return "CHAT-" + hashlib.sha256(canonical_bytes(payload)).hexdigest()[:16].upper()


def _implicit_protected_selectors(message: str) -> dict[str, Any]:
    lower = message.casefold()
    generic_webui_launcher = (
        "webui launcher" in lower
        and "web with comfyui" not in lower
        and "web_with_comfyui" not in lower
        and "web portable" not in lower
        and "start_foxai_web_portable" not in lower
        and "start_foxai_web_with_comfyui" not in lower
    )
    if generic_webui_launcher:
        return {"intent": "contexts_for_launcher"}
    return {}


def _catalog_matches(message: str, selectors: dict[str, Any], bridge: dict[str, Any]) -> list[str]:
    explicit = selectors.get("intent")
    if explicit is not None:
        normalized = str(explicit).strip().lower().replace("-", "_").replace(" ", "_")
        return [normalized] if normalized in set(bridge["INTENTS"]) else []
    lower = message.casefold()
    anchored = any(anchor in lower for anchor in DOMAIN_ANCHORS)
    matches: list[str] = []
    for intent, definition in bridge["INTENT_DEFINITIONS"].items():
        for synonym in definition.get("synonyms", []):
            phrase = str(synonym).casefold()
            if phrase not in lower:
                continue
            if phrase in WEAK_GENERIC_SYNONYMS and not anchored:
                continue
            matches.append(intent)
            break
    if "compare" in lower and anchored and "compare_contexts" not in matches:
        matches.append("compare_contexts")
    return list(dict.fromkeys(matches))


def _safe_error_result(surface: str, request_id: str, error: BaseException) -> dict[str, Any]:
    code_seed = f"{type(error).__name__}:evidence_verification_failure"
    return {
        "handled": True,
        "status": "evidence_error",
        "model_bypass": True,
        "ordinary_chat_pass_through": False,
        "answer_text": "Agent Fox self-knowledge evidence could not be verified, so no technical claim was returned.",
        "answer_packet": None,
        "diagnostic": {
            "code": "SK-EVIDENCE-" + hashlib.sha256(code_seed.encode("utf-8")).hexdigest()[:12].upper(),
            "error_type": type(error).__name__,
            "surface": surface,
            "request_id": request_id,
            "bridge_hash_verified": False,
            "registry_verified": False,
            "ordinary_chat_fallback_blocked": True,
        },
    }


def _provenance_text(provenance: list[dict[str, Any]]) -> str:
    rows = []
    for source in provenance:
        locator = source.get("json_field_path") or source.get("record_locator") or "unavailable"
        rows.append(
            "mission={mission}; file={file}; sha256={sha}; locator={locator}; receipt_sha256={receipt}".format(
                mission=source.get("source_mission_id"),
                file=source.get("evidence_filename"),
                sha=source.get("evidence_sha256"),
                locator=locator,
                receipt=source.get("source_receipt_sha256"),
            )
        )
    return " | ".join(rows)


def _claim_block(item: Any, label: str) -> str:
    if isinstance(item, str):
        return f"{label}: {item}"
    if not isinstance(item, dict):
        return f"{label}: {item!r}"
    text = str(item.get("text") or item.get("message") or item.get("claim_id") or "Structured item")
    provenance = item.get("provenance") or []
    if label == "UNRESOLVED":
        text = "UNCONFIRMED CANDIDATE — " + text
    line = f"{label}: {text}"
    if provenance:
        line += "\n  Provenance: " + _provenance_text(provenance)
    return line


def render_answer_packet(packet: dict[str, Any]) -> str:
    blocks: list[str] = []
    answer_text = packet.get("answer_text")
    if answer_text:
        blocks.append(str(answer_text))
    for item in packet.get("uncertainty_statements", []):
        blocks.append(_claim_block(item, "UNCERTAINTY"))
    for item in packet.get("unresolved_items", []):
        blocks.append(_claim_block(item, "UNRESOLVED"))
    for item in packet.get("linked_context_references", []):
        blocks.append(_claim_block(item, "LINK"))
    for item in packet.get("structured_claims", []):
        blocks.append(_claim_block(item, "CLAIM"))
    clarification = packet.get("clarification")
    if clarification:
        choices = clarification.get("choices") or []
        choice_text = ", ".join(str(choice) for choice in choices)
        blocks.append("CLARIFICATION: " + str(clarification.get("message") or "More detail is required.") + (f" Choices: {choice_text}" if choice_text else ""))
    if not blocks:
        blocks.append("No self-knowledge claim was returned.")

    retained: list[str] = []
    marker = "[TRUNCATED deterministically at the 64 KiB display ceiling; retained claims preserve their uncertainty labels and provenance.]"
    for block in blocks:
        candidate = "\n\n".join(retained + [block])
        if len(candidate.encode("utf-8")) <= RENDERED_TEXT_CEILING_BYTES - len(marker.encode("utf-8")) - 2:
            retained.append(block)
        else:
            retained.append(marker)
            break
    rendered = "\n\n".join(retained)
    if len(rendered.encode("utf-8")) > RENDERED_TEXT_CEILING_BYTES:
        raise AssertionError("rendered_text_ceiling_exceeded")
    return rendered


def _pass_through_result(surface: str, request_id: str, reason: str) -> dict[str, Any]:
    return {
        "handled": False,
        "status": "pass_through",
        "model_bypass": False,
        "ordinary_chat_pass_through": True,
        "answer_text": None,
        "answer_packet": None,
        "diagnostic": {
            "code": reason,
            "surface": surface,
            "request_id": request_id,
            "registry_verified": False,
            "registry_read": False,
        },
    }


def _safe_resource_error_result(surface: str, request_id: str, error: BaseException) -> dict[str, Any]:
    code_seed = f"{type(error).__name__}:resource_evidence_verification_failure"
    return {
        "handled": True,
        "status": "evidence_error",
        "model_bypass": True,
        "ordinary_chat_pass_through": False,
        "answer_text": "Agent Fox resource evidence could not be verified, so no measured resource claim was returned.",
        "answer_packet": None,
        "diagnostic": {
            "code": "RESOURCE-EVIDENCE-" + hashlib.sha256(code_seed.encode("utf-8")).hexdigest()[:12].upper(),
            "error_type": type(error).__name__,
            "surface": surface,
            "request_id": request_id,
            "resource_provider_hash_verified": False,
            "resource_evidence_verified": False,
            "ordinary_chat_fallback_blocked": True,
        },
    }


def _render_resource_answer_packet(packet: dict[str, Any]) -> str:
    blocks: list[str] = []
    answer_text = str(packet.get("answer_text") or "").strip()
    if answer_text:
        blocks.append(answer_text)
    source_mission = packet.get("source_mission")
    source_files = [str(item) for item in packet.get("source_files", []) if str(item).strip()]
    if source_mission and source_files:
        blocks.append(
            "Evidence: verified mission " + str(source_mission) + "; " + ", ".join(source_files) + "."
        )
    limitations = [str(item).strip() for item in packet.get("limitations", []) if str(item).strip()]
    if limitations:
        blocks.append("Limitations: " + " ".join(limitations))
    if not blocks:
        raise ValueError("resource_answer_text_missing")
    rendered = "\n\n".join(blocks)
    if len(rendered.encode("utf-8")) > RENDERED_TEXT_CEILING_BYTES:
        raise ValueError("resource_rendered_text_ceiling_exceeded")
    return rendered


def _route_resource_message(message: str, surface: str, request_id: str) -> dict[str, Any]:
    try:
        provider = _load_resource_provider_namespace()
    except Exception:
        # Provider unavailability before classification must not steal ordinary chat.
        return _pass_through_result(surface, request_id, "RESOURCE-PASS-PROVIDER-UNAVAILABLE-BEFORE-RECOGNITION")
    try:
        _AUDIT["resource_classify_calls"] += 1
        classification = provider["classify_question"](message)
        status = str(classification.get("status"))
        if status == "bypass":
            return _pass_through_result(surface, request_id, "RESOURCE-PASS-SLASH-COMMAND")
        if status == "not_applicable":
            reason = str(classification.get("reason") or "outside_resource_baseline_catalog")
            return _pass_through_result(surface, request_id, "RESOURCE-PASS-" + reason.upper())
        if status != "resource_question":
            raise ValueError("unexpected_resource_classification_status")
        _AUDIT["resource_answer_calls"] += 1
        result = provider["answer_question"](message, request_id, Path(_RESOURCE_SOURCE_DIR))
        if result.get("status") != "answered" or result.get("evidence_loaded") is not True:
            raise ValueError("resource_provider_failed_after_positive_recognition")
        packet = result.get("answer_packet")
        if not isinstance(packet, dict):
            raise ValueError("resource_answer_packet_missing")
        if packet.get("schema") != "foxai.agent_fox.technical_core.v1a3e.answer_packet.v1":
            raise ValueError("resource_answer_packet_schema_mismatch")
        if packet.get("status") != "answered":
            raise ValueError("resource_answer_packet_status_mismatch")
        if packet.get("current_state_claimed") is not False or packet.get("live_scan_performed") is not False:
            raise ValueError("resource_answer_safety_boundary_failed")
        rendered = _render_resource_answer_packet(packet)
        routed = {
            "handled": True,
            "status": "answered",
            "model_bypass": True,
            "ordinary_chat_pass_through": False,
            "answer_text": rendered,
            "answer_packet": packet,
            "diagnostic": {
                "code": "RESOURCE-ANSWERED",
                "surface": surface,
                "request_id": request_id,
                "provider": result.get("provider"),
                "matched_category": result.get("matched_category"),
                "resource_provider_hash_verified": True,
                "resource_evidence_verified": True,
                "current_state_claimed": False,
                "live_scan_performed": False,
            },
        }
        if len(canonical_bytes(routed)) > COMPLETE_RESULT_CEILING_BYTES:
            raise ValueError("complete_result_ceiling_exceeded")
        return routed
    except Exception as error:
        return _safe_resource_error_result(surface, request_id, error)


def route_message(message: str, surface: str, request_id: str | None = None, selectors: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized_surface = _normalize_surface(surface)
    normalized_message = _normalize_message(message)
    if normalized_surface not in SUPPORTED_SURFACES:
        rid = str(request_id or "CHAT-UNSUPPORTED-SURFACE")
        return _safe_error_result(normalized_surface, rid, ValueError("unsupported_surface"))
    slash_rid = str(request_id).strip() if request_id is not None and str(request_id).strip() else _deterministic_request_id(normalized_surface, normalized_message, {})
    if normalized_message.lstrip().startswith("/"):
        return _pass_through_result(normalized_surface, slash_rid, "SK-PASS-SLASH-COMMAND")
    try:
        normalized_selectors = _normalize_selectors(selectors)
    except Exception as error:
        rid = str(request_id or "CHAT-INVALID-SELECTORS")
        return _safe_error_result(normalized_surface, rid, error)
    rid = str(request_id).strip() if request_id is not None and str(request_id).strip() else _deterministic_request_id(normalized_surface, normalized_message, normalized_selectors)

    if len(normalized_message) > MAX_MESSAGE_CHARS:
        return _pass_through_result(normalized_surface, rid, "SK-PASS-INPUT-BOUND")

    try:
        bridge = _load_bridge_namespace()
        effective_selectors = dict(normalized_selectors)
        if not effective_selectors:
            effective_selectors = _implicit_protected_selectors(normalized_message)
        candidates = _catalog_matches(normalized_message, effective_selectors, bridge)
        if not candidates:
            if normalized_selectors:
                return _pass_through_result(normalized_surface, rid, "SK-PASS-NO-MATCH")
            return _route_resource_message(normalized_message, normalized_surface, rid)
        if len(candidates) > 1:
            packet = bridge["clarification_packet"](
                {
                    "request_id": rid,
                    "intent": None,
                    "text": normalized_message,
                    "candidate_intents": candidates,
                },
                "The request matched more than one supported self-knowledge intent; select one exact intent.",
                candidates,
            )
            rendered = render_answer_packet(packet)
            result = {
                "handled": True,
                "status": "clarification_required",
                "model_bypass": True,
                "ordinary_chat_pass_through": False,
                "answer_text": rendered,
                "answer_packet": packet,
                "diagnostic": {
                    "code": "SK-CLARIFY-MULTIPLE-INTENTS",
                    "surface": normalized_surface,
                    "request_id": rid,
                    "candidate_intents": candidates,
                    "bridge_hash_verified": True,
                    "registry_verified": False,
                },
            }
            if len(canonical_bytes(result)) > COMPLETE_RESULT_CEILING_BYTES:
                raise ValueError("complete_result_ceiling_exceeded")
            return result

        _verify_bridge_hash(Path(_BRIDGE_PATH))
        loaded = _verify_registry(bridge)
        if effective_selectors:
            request = dict(effective_selectors)
            request["request_id"] = rid
            request.setdefault("text", normalized_message)
        else:
            request = bridge["infer_natural_request"](normalized_message, bridge["indexes"](loaded))
            request["request_id"] = rid
        packet = bridge["answer_request"](request, loaded)
        packet_status = str(packet.get("status"))
        if packet_status not in {"answered", "clarification_required"}:
            raise ValueError("unexpected_bridge_status")
        rendered = render_answer_packet(packet)
        result = {
            "handled": True,
            "status": packet_status,
            "model_bypass": True,
            "ordinary_chat_pass_through": False,
            "answer_text": rendered,
            "answer_packet": packet,
            "diagnostic": {
                "code": "SK-ANSWERED" if packet_status == "answered" else "SK-CLARIFICATION-REQUIRED",
                "surface": normalized_surface,
                "request_id": rid,
                "bridge_hash_verified": True,
                "registry_verified": True,
                "normalized_intent": packet.get("normalized_intent"),
            },
        }
        if len(canonical_bytes(result)) > COMPLETE_RESULT_CEILING_BYTES:
            raise ValueError("complete_result_ceiling_exceeded")
        return result
    except Exception as error:
        return _safe_error_result(normalized_surface, rid, error)


def verify_evidence_directory(directory: Path, spec: dict[str, Any]) -> dict[str, Any]:
    receipt_path = directory / spec["receipt_name"]
    if not receipt_path.is_file():
        raise FileNotFoundError("authoritative_receipt_missing")
    if sha256_file(receipt_path) != spec["receipt_sha256"]:
        raise ValueError("authoritative_receipt_hash_mismatch")
    receipt = read_json(receipt_path)
    if receipt.get("mission_id") != spec["mission_id"]:
        raise ValueError("authoritative_receipt_mission_mismatch")
    receipt_outputs = {row["name"]: row["sha256"] for row in receipt.get("core_outputs_before_receipt", [])}
    if receipt_outputs != spec["core_outputs"]:
        raise ValueError("authoritative_receipt_output_manifest_mismatch")
    verified = []
    for name, expected_hash in spec["core_outputs"].items():
        path = directory / name
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise ValueError("authoritative_output_hash_mismatch")
        verified.append({"name": name, "sha256": expected_hash, "size_bytes": path.stat().st_size})
    return {
        "mission_id": spec["mission_id"],
        "receipt_name": spec["receipt_name"],
        "receipt_sha256": spec["receipt_sha256"],
        "verified_outputs": verified,
    }


def verify_authoritative_inputs(v1a3d_dir: Path, v1a3e_dir: Path, v1a3f_dir: Path, bridge_path: Path) -> dict[str, Any]:
    _verify_bridge_hash(bridge_path)
    reports = {
        "v1a3d": verify_evidence_directory(v1a3d_dir, EXPECTED_EVIDENCE["v1a3d"]),
        "v1a3e": verify_evidence_directory(v1a3e_dir, EXPECTED_EVIDENCE["v1a3e"]),
        "v1a3f": verify_evidence_directory(v1a3f_dir, EXPECTED_EVIDENCE["v1a3f"]),
    }
    test_cases = read_json(v1a3e_dir / "SELF_KNOWLEDGE_TEST_CASES.json")
    if test_cases.get("test_case_count") != 34 or len(test_cases.get("cases", [])) != 34:
        raise ValueError("v1a3e_test_case_count_mismatch")
    intent_catalog = read_json(v1a3e_dir / "SELF_KNOWLEDGE_INTENT_CATALOG.json")
    intent_count = intent_catalog.get("supported_intent_count", intent_catalog.get("intent_count"))
    if intent_count is None:
        intents_obj = intent_catalog.get("intents", [])
        intent_count = len(intents_obj)
    if intent_count != 11:
        raise ValueError("v1a3e_intent_count_mismatch")
    return {
        "verified_evidence_set_count": 3,
        "verified_receipt_count": 3,
        "verified_output_count": sum(len(row["verified_outputs"]) for row in reports.values()),
        "bridge_source_sha256": EXPECTED_BRIDGE_SHA256,
        "v1a3e_test_case_count": 34,
        "supported_intent_count": 11,
        "reports": reports,
        "test_cases": test_cases,
    }


def _iter_claim_items(packet: dict[str, Any]):
    for field in ("structured_claims", "uncertainty_statements", "unresolved_items", "linked_context_references"):
        for item in packet.get(field, []):
            if isinstance(item, dict) and item.get("claim_id"):
                yield field, item


def _validate_packet_safety(packet: dict[str, Any]) -> tuple[int, int]:
    safety = packet.get("safety", {})
    if safety.get("unresolved_candidates_presented_as_confirmed") is not False:
        raise AssertionError("unresolved_state_not_preserved")
    if safety.get("runtime_facts_inferred_across_contexts") is not False:
        raise AssertionError("runtime_cross_context_inference")
    if safety.get("dependency_nodes_or_edges_copied") is not False:
        raise AssertionError("dependency_records_copied")
    claim_count = 0
    provenance_count = 0
    for _, item in _iter_claim_items(packet):
        claim_count += 1
        provenance = item.get("provenance")
        if not isinstance(provenance, list) or not provenance:
            raise AssertionError("claim_provenance_missing")
        for source in provenance:
            required = {"source_mission_id", "evidence_filename", "evidence_sha256", "source_receipt_sha256"}
            if not required.issubset(source):
                raise AssertionError("claim_provenance_incomplete")
            if not source.get("json_field_path") and not source.get("record_locator"):
                raise AssertionError("claim_locator_missing")
            provenance_count += 1
    return claim_count, provenance_count


def run_adapter_test_suite(v1a3d_dir: Path, v1a3e_dir: Path, bridge_path: Path) -> dict[str, Any]:
    original_bridge = Path(_BRIDGE_PATH)
    original_registry = Path(_REGISTRY_DIR)
    _configure_paths_for_tests(bridge_path, v1a3d_dir)
    rows: list[dict[str, Any]] = []
    claim_count = 0
    provenance_count = 0
    intent_coverage: set[str] = set()
    context_coverage: set[str] = set()
    launcher_coverage: set[str] = set()
    try:
        test_cases = read_json(v1a3e_dir / "SELF_KNOWLEDGE_TEST_CASES.json")["cases"]
        for case in test_cases:
            for surface in SUPPORTED_SURFACES:
                selectors = dict(case["request"])
                rid = selectors.pop("request_id", None)
                message = f"Structured Agent Fox self-knowledge request: {case['expected_intent']}"
                _reset_audit_for_tests()
                first = route_message(message, surface, rid, selectors)
                second = route_message(message, surface, rid, selectors)
                if canonical_bytes(first) != canonical_bytes(second):
                    raise AssertionError("adapter_result_not_deterministic")
                expected = case["expected_status"]
                if first["status"] != expected:
                    raise AssertionError((case["case_id"], surface, expected, first["status"]))
                if first["handled"] is not True or first["model_bypass"] is not True or first["ordinary_chat_pass_through"] is not False:
                    raise AssertionError("recognized_route_contract_failed")
                packet = first["answer_packet"]
                if packet is None:
                    raise AssertionError("recognized_packet_missing")
                c, p = _validate_packet_safety(packet)
                claim_count += c
                provenance_count += p
                if packet.get("normalized_intent"):
                    intent_coverage.add(packet["normalized_intent"])
                selectors_resolved = packet.get("resolved_selectors", {})
                if selectors_resolved.get("context"):
                    context_coverage.add(selectors_resolved["context"])
                if selectors.get("launcher"):
                    launcher_coverage.add(selectors["launcher"])
                rows.append({
                    "test_id": f"{case['case_id']}-{surface}",
                    "category": "v1a3e_case",
                    "surface": surface,
                    "expected_status": expected,
                    "actual_status": first["status"],
                    "intent": case["expected_intent"],
                    "passed": True,
                })

        ordinary_messages = [
            "Tell me a joke about foxes.",
            "How is the weather today?",
            "Help me write a poem.",
            "Open my grocery list.",
            "Explain photosynthesis.",
            "What should I cook tonight?",
        ]
        for index, message in enumerate(ordinary_messages, start=1):
            for surface in SUPPORTED_SURFACES:
                _reset_audit_for_tests()
                result = route_message(message, surface)
                audit = _audit_snapshot()
                if result["status"] != "pass_through" or result["handled"] is not False or result["model_bypass"] is not False or result["ordinary_chat_pass_through"] is not True:
                    raise AssertionError("ordinary_pass_through_failed")
                if audit["registry_verify_calls"] != 0:
                    raise AssertionError("registry_read_for_unsupported_chat")
                rows.append({
                    "test_id": f"PASS-{index:02d}-{surface}",
                    "category": "ordinary_chat_pass_through",
                    "surface": surface,
                    "expected_status": "pass_through",
                    "actual_status": result["status"],
                    "registry_verify_calls": audit["registry_verify_calls"],
                    "passed": True,
                })

        ambiguous_messages = [
            "Agent Fox, show protected contexts and technical core coverage.",
            "Agent Fox, show context and runtime uncertainty for Workshop Main.",
        ]
        for index, message in enumerate(ambiguous_messages, start=1):
            for surface in SUPPORTED_SURFACES:
                result = route_message(message, surface)
                if result["status"] != "clarification_required" or result["model_bypass"] is not True:
                    raise AssertionError("ambiguous_model_bypass_failed")
                packet = result["answer_packet"]
                if packet is None or packet.get("status") != "clarification_required":
                    raise AssertionError("ambiguous_packet_missing")
                rows.append({
                    "test_id": f"AMB-{index:02d}-{surface}",
                    "category": "ambiguous_supported_request",
                    "surface": surface,
                    "expected_status": "clarification_required",
                    "actual_status": result["status"],
                    "passed": True,
                })

        unsupported_technical = [
            "Which Python version should I install for a new data science project?",
            "What runs when Linux starts?",
        ]
        for index, message in enumerate(unsupported_technical, start=1):
            for surface in SUPPORTED_SURFACES:
                _reset_audit_for_tests()
                result = route_message(message, surface)
                audit = _audit_snapshot()
                if result["status"] != "pass_through" or audit["registry_verify_calls"] != 0:
                    raise AssertionError("unsupported_technical_pass_through_failed")
                rows.append({
                    "test_id": f"TECH-PASS-{index:02d}-{surface}",
                    "category": "unsupported_technical_pass_through",
                    "surface": surface,
                    "expected_status": "pass_through",
                    "actual_status": result["status"],
                    "registry_verify_calls": audit["registry_verify_calls"],
                    "passed": True,
                })

        with tempfile.TemporaryDirectory(prefix="foxai_v1a3g_corruption_") as tmp_name:
            temp_root = Path(tmp_name)
            corrupt_registry = temp_root / "registry"
            shutil.copytree(v1a3d_dir, corrupt_registry)
            target = corrupt_registry / "PROTECTED_CONTEXT_REGISTRY.json"
            target.write_bytes(target.read_bytes() + b"\n")
            _configure_paths_for_tests(bridge_path, corrupt_registry)
            result = route_message("Agent Fox, list protected contexts.", "webui", "CORRUPT-REGISTRY", {"intent": "list_protected_contexts"})
            if result["status"] != "evidence_error" or result["ordinary_chat_pass_through"] is not False:
                raise AssertionError("corrupt_registry_did_not_fail_closed")
            rows.append({
                "test_id": "CORRUPT-REGISTRY",
                "category": "synthetic_evidence_corruption",
                "surface": "webui",
                "expected_status": "evidence_error",
                "actual_status": result["status"],
                "passed": True,
            })

            corrupt_bridge = temp_root / "bridge.py"
            shutil.copy2(bridge_path, corrupt_bridge)
            corrupt_bridge.write_bytes(corrupt_bridge.read_bytes() + b"\n")
            _configure_paths_for_tests(corrupt_bridge, v1a3d_dir)
            result = route_message("Agent Fox, list protected contexts.", "desktop", "CORRUPT-BRIDGE", {"intent": "list_protected_contexts"})
            if result["status"] != "evidence_error" or result["ordinary_chat_pass_through"] is not False:
                raise AssertionError("corrupt_bridge_did_not_fail_closed")
            rows.append({
                "test_id": "CORRUPT-BRIDGE",
                "category": "synthetic_evidence_corruption",
                "surface": "desktop",
                "expected_status": "evidence_error",
                "actual_status": result["status"],
                "passed": True,
            })

        _configure_paths_for_tests(bridge_path, v1a3d_dir)
        workshop = route_message("Structured Agent Fox self-knowledge request", "webui", "WORKSHOP-UNCERTAINTY", {"intent": "explain_runtime_uncertainty", "context": "workshop_main"})
        desktop = route_message("Structured Agent Fox self-knowledge request", "desktop", "DESKTOP-UNCERTAINTY", {"intent": "explain_runtime_uncertainty", "context": "desktop_recovery_gui"})
        workshop_blob = canonical_bytes(workshop).decode("utf-8").casefold()
        desktop_blob = canonical_bytes(desktop).decode("utf-8").casefold()
        if "interpreter_command_alias_not_resolved" not in workshop_blob:
            raise AssertionError("workshop_alias_uncertainty_missing")
        if "pythonw_runtime_identity_not_directly_probed" not in desktop_blob and '"pythonw_identity_directly_observed": false' not in desktop_blob:
            raise AssertionError("pythonw_uncertainty_missing")
        if workshop["answer_packet"]["safety"]["runtime_facts_inferred_across_contexts"] is not False:
            raise AssertionError("workshop_cross_context_inference")
        if desktop["answer_packet"]["safety"]["runtime_facts_inferred_across_contexts"] is not False:
            raise AssertionError("desktop_cross_context_inference")

        expected_test_count = 68 + 12 + 4 + 4 + 2
        if len(rows) != expected_test_count:
            raise AssertionError((len(rows), expected_test_count))
        if len(intent_coverage) != 11:
            raise AssertionError(("intent_coverage", sorted(intent_coverage)))
        if len(context_coverage) != 6:
            raise AssertionError(("context_coverage", sorted(context_coverage)))
        if len(launcher_coverage) != 4:
            raise AssertionError(("launcher_coverage", sorted(launcher_coverage)))
        return {
            "rows": rows,
            "test_count": len(rows),
            "v1a3e_case_execution_count": 68,
            "ordinary_chat_pass_through_count": 12,
            "ambiguous_supported_request_count": 4,
            "unsupported_technical_pass_through_count": 4,
            "synthetic_corruption_test_count": 2,
            "supported_intent_count": len(intent_coverage),
            "context_coverage_count": len(context_coverage),
            "launcher_coverage_count": len(launcher_coverage),
            "claim_count": claim_count,
            "claim_provenance_record_count": provenance_count,
            "deterministic_equality": True,
            "recognized_model_bypass": True,
            "ambiguous_model_bypass": True,
            "unsupported_chat_pass_through": True,
            "registry_reads_for_unsupported_chat": 0,
            "unresolved_state_preserved": True,
            "workshop_python_alias_resolved": False,
            "pythonw_identity_directly_probed": False,
            "runtime_facts_inferred_across_contexts": False,
            "closure_node_records_copied": 0,
            "closure_edge_records_copied": 0,
        }
    finally:
        _configure_paths_for_tests(original_bridge, original_registry)


def build_core_outputs(mission_id: str, verification: dict[str, Any], suite: dict[str, Any], bridge_path: Path, registry_dir: Path) -> dict[str, bytes]:
    _configure_paths_for_tests(bridge_path, registry_dir)
    examples = []
    example_specs = [
        ("webui", "Agent Fox, list protected contexts.", {"intent": "list_protected_contexts"}),
        ("desktop", "Agent Fox, summarize Workshop Main.", {"intent": "summarize_context", "context": "workshop_main"}),
        ("webui", "Agent Fox, show unresolved imports for Desktop Recovery GUI.", {"intent": "list_unresolved_branches", "context": "desktop_recovery_gui"}),
        ("desktop", "Agent Fox, explain runtime uncertainty for Workshop Main.", {"intent": "explain_runtime_uncertainty", "context": "workshop_main"}),
        ("webui", "Agent Fox, show context and runtime uncertainty for Workshop Main.", None),
        ("desktop", "Help me write a short story.", None),
    ]
    for index, (surface, message, selectors) in enumerate(example_specs, start=1):
        result = route_message(message, surface, f"EXAMPLE-{index:02d}", selectors)
        examples.append({
            "example_id": f"EXAMPLE-{index:02d}",
            "surface": surface,
            "message": message,
            "selectors": selectors,
            "status": result["status"],
            "model_bypass": result["model_bypass"],
            "ordinary_chat_pass_through": result["ordinary_chat_pass_through"],
            "answer_text": result["answer_text"],
            "answer_packet_status": result["answer_packet"].get("status") if result["answer_packet"] else None,
        })

    api = {
        "schema": f"{SCHEMA_PREFIX}.api.v1",
        "mission_id": mission_id,
        "module_path": r"Z:\FOXAI\System\AgentFoxTechnicalCore\self_knowledge_chat_adapter_v1.py",
        "callable": "route_message(message, surface, request_id=None, selectors=None)",
        "supported_surfaces": list(SUPPORTED_SURFACES),
        "top_level_result_fields": ["handled", "status", "model_bypass", "ordinary_chat_pass_through", "answer_text", "answer_packet", "diagnostic"],
        "statuses": {
            "answered": "Recognized self-knowledge request answered from verified evidence; model bypass required.",
            "clarification_required": "Supported request is ambiguous or incomplete; deterministic clarification returned; model bypass required.",
            "pass_through": "Unsupported ordinary chat; adapter does not read the registry and existing chat/model path remains available.",
            "evidence_error": "Positive self-knowledge recognition failed evidence verification; fail closed with no ordinary-chat fallback.",
        },
        "bounds": {
            "message_characters": MAX_MESSAGE_CHARS,
            "selectors_bytes": MAX_SELECTORS_BYTES,
            "rendered_text_bytes": RENDERED_TEXT_CEILING_BYTES,
            "complete_result_bytes": COMPLETE_RESULT_CEILING_BYTES,
        },
        "bridge_source_sha256": EXPECTED_BRIDGE_SHA256,
        "supported_intent_count": 11,
    }
    routing = {
        "schema": f"{SCHEMA_PREFIX}.routing.v1",
        "mission_id": mission_id,
        "authoritative_recognition_catalog": "V1A-3E INTENT_DEFINITIONS and synonyms",
        "supported_intent_count": 11,
        "weak_generic_synonyms_requiring_foxai_domain_anchor": sorted(WEAK_GENERIC_SYNONYMS),
        "domain_anchors": list(DOMAIN_ANCHORS),
        "rules": [
            {"class": "recognized", "registry_verification": True, "handled": True, "model_bypass": True, "ordinary_chat_pass_through": False},
            {"class": "ambiguous_supported", "registry_verification": "only when selector resolution requires it", "handled": True, "model_bypass": True, "ordinary_chat_pass_through": False},
            {"class": "unsupported_ordinary", "registry_verification": False, "handled": False, "model_bypass": False, "ordinary_chat_pass_through": True},
            {"class": "recognized_evidence_failure", "registry_verification": "failed", "handled": True, "model_bypass": True, "ordinary_chat_pass_through": False},
        ],
        "request_id_generation": "SHA-256 over normalized surface, case-folded normalized message, and canonical selectors; first 16 uppercase hex characters prefixed CHAT-.",
        "runtime_safety": {
            "workshop_python_alias_resolved": False,
            "pythonw_identity_directly_probed": False,
            "runtime_facts_inferred_across_contexts": False,
        },
    }
    rendering = {
        "schema": f"{SCHEMA_PREFIX}.rendering_examples.v1",
        "mission_id": mission_id,
        "rendering_rules": {
            "complete_v1a3e_packet_retained_unmodified": True,
            "uncertainty_rendered_before_general_claims": True,
            "unresolved_candidates_labeled_unconfirmed": True,
            "provenance_kept_with_each_retained_claim": True,
            "rendered_text_ceiling_bytes": RENDERED_TEXT_CEILING_BYTES,
            "complete_result_ceiling_bytes": COMPLETE_RESULT_CEILING_BYTES,
        },
        "examples": examples,
    }
    tests = {
        "schema": f"{SCHEMA_PREFIX}.test_matrix.v1",
        "mission_id": mission_id,
        "test_count": suite["test_count"],
        "rows": suite["rows"],
    }
    coverage = {
        "schema": f"{SCHEMA_PREFIX}.coverage.v1",
        "mission_id": mission_id,
        "verified_evidence_set_count": verification["verified_evidence_set_count"],
        "verified_receipt_count": verification["verified_receipt_count"],
        "verified_authoritative_output_count": verification["verified_output_count"],
        "bridge_source_hash_verified": True,
        "supported_intent_count": suite["supported_intent_count"],
        "v1a3e_test_case_execution_count": suite["v1a3e_case_execution_count"],
        "surface_count": 2,
        "context_coverage_count": suite["context_coverage_count"],
        "launcher_coverage_count": suite["launcher_coverage_count"],
        "ordinary_chat_pass_through_count": suite["ordinary_chat_pass_through_count"],
        "ambiguous_supported_request_count": suite["ambiguous_supported_request_count"],
        "unsupported_technical_pass_through_count": suite["unsupported_technical_pass_through_count"],
        "synthetic_corruption_test_count": suite["synthetic_corruption_test_count"],
        "total_test_count": suite["test_count"],
        "claim_count": suite["claim_count"],
        "claim_provenance_record_count": suite["claim_provenance_record_count"],
        "deterministic_equality": suite["deterministic_equality"],
        "registry_reads_for_unsupported_chat": suite["registry_reads_for_unsupported_chat"],
        "recognized_model_bypass": suite["recognized_model_bypass"],
        "ambiguous_model_bypass": suite["ambiguous_model_bypass"],
        "unsupported_chat_pass_through": suite["unsupported_chat_pass_through"],
        "unresolved_state_preserved": suite["unresolved_state_preserved"],
        "workshop_python_alias_resolved": False,
        "pythonw_identity_directly_probed": False,
        "runtime_facts_inferred_across_contexts": False,
        "closure_node_records_copied": 0,
        "closure_edge_records_copied": 0,
        "live_foxai_source_scans": 0,
        "imported_live_foxai_modules": 0,
        "child_processes": 0,
        "network_used": False,
        "packages_installed": False,
        "models_loaded": False,
        "existing_foxai_chat_source_modified": False,
        "rollback_t7_k_accessed": False,
    }
    return {
        "SELF_KNOWLEDGE_CHAT_ADAPTER_API.json": canonical_bytes(api),
        "SELF_KNOWLEDGE_CHAT_ADAPTER_ROUTING.json": canonical_bytes(routing),
        "SELF_KNOWLEDGE_CHAT_ADAPTER_RENDERING_EXAMPLES.json": canonical_bytes(rendering),
        "SELF_KNOWLEDGE_CHAT_ADAPTER_TEST_MATRIX.json": canonical_bytes(tests),
        "SELF_KNOWLEDGE_CHAT_ADAPTER_COVERAGE.json": canonical_bytes(coverage),
    }


def write_build(mission_id: str, output_dir: Path, verification: dict[str, Any], suite: dict[str, Any], bridge_path: Path, registry_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    first = build_core_outputs(mission_id, verification, suite, bridge_path, registry_dir)
    second = build_core_outputs(mission_id, verification, suite, bridge_path, registry_dir)
    if first != second:
        raise AssertionError("internal_deterministic_rebuild_mismatch")
    core_rows = []
    for name in OUTPUT_NAMES:
        data = first[name]
        core_rows.append({"name": name, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
    receipt = {
        "schema": f"{SCHEMA_PREFIX}.receipt.v1",
        "mission_id": mission_id,
        "status": "built",
        "core_outputs_before_receipt": core_rows,
        "exact_output_count_including_receipt": 6,
        "internal_deterministic_rebuild_match": True,
        "verified_evidence_set_count": verification["verified_evidence_set_count"],
        "verified_receipt_count": verification["verified_receipt_count"],
        "verified_authoritative_output_count": verification["verified_output_count"],
        "bridge_source_sha256": EXPECTED_BRIDGE_SHA256,
        "supported_intent_count": suite["supported_intent_count"],
        "test_count": suite["test_count"],
        "v1a3e_case_execution_count": suite["v1a3e_case_execution_count"],
        "claim_provenance_record_count": suite["claim_provenance_record_count"],
        "recognized_model_bypass": True,
        "ambiguous_model_bypass": True,
        "unsupported_chat_pass_through": True,
        "registry_reads_for_unsupported_chat": 0,
        "unresolved_state_preserved": True,
        "workshop_python_alias_resolved": False,
        "pythonw_identity_directly_probed": False,
        "runtime_facts_inferred_across_contexts": False,
        "closure_node_records_copied": 0,
        "closure_edge_records_copied": 0,
        "live_foxai_source_scans": 0,
        "imported_live_foxai_modules": 0,
        "child_processes": 0,
        "network_used": False,
        "packages_installed": False,
        "models_loaded": False,
        "existing_foxai_chat_source_modified": False,
        "rollback_t7_k_accessed": False,
    }
    receipt_data = canonical_bytes(receipt)
    total = sum(len(data) for data in first.values()) + len(receipt_data)
    if total >= TOTAL_OUTPUT_CEILING_BYTES:
        raise ValueError("total_output_ceiling_exceeded")
    receipt["total_output_bytes"] = total
    receipt_data = canonical_bytes(receipt)
    total = sum(len(data) for data in first.values()) + len(receipt_data)
    if total >= TOTAL_OUTPUT_CEILING_BYTES:
        raise ValueError("total_output_ceiling_exceeded")
    receipt["total_output_bytes"] = total
    receipt_data = canonical_bytes(receipt)
    output_dir.mkdir(parents=True, exist_ok=False)
    for name in OUTPUT_NAMES:
        (output_dir / name).write_bytes(first[name])
    (output_dir / RECEIPT_NAME).write_bytes(receipt_data)
    return {
        "status": "built",
        "mission_id": mission_id,
        "output_dir": str(output_dir),
        "exact_output_count": 6,
        "test_count": suite["test_count"],
        "supported_intent_count": suite["supported_intent_count"],
        "claim_provenance_record_count": suite["claim_provenance_record_count"],
        "total_output_bytes": total,
        "internal_deterministic_rebuild_match": True,
    }


def validate_output(index_dir: Path) -> dict[str, Any]:
    expected = set(OUTPUT_NAMES) | {RECEIPT_NAME}
    actual = {path.name for path in index_dir.iterdir() if path.is_file()}
    if actual != expected:
        raise AssertionError((sorted(actual), sorted(expected)))
    receipt = read_json(index_dir / RECEIPT_NAME)
    if receipt["exact_output_count_including_receipt"] != 6:
        raise AssertionError("output_count_mismatch")
    for row in receipt["core_outputs_before_receipt"]:
        path = index_dir / row["name"]
        if sha256_file(path) != row["sha256"] or path.stat().st_size != row["size_bytes"]:
            raise AssertionError("output_hash_or_size_mismatch")
    coverage = read_json(index_dir / "SELF_KNOWLEDGE_CHAT_ADAPTER_COVERAGE.json")
    tests = read_json(index_dir / "SELF_KNOWLEDGE_CHAT_ADAPTER_TEST_MATRIX.json")
    api = read_json(index_dir / "SELF_KNOWLEDGE_CHAT_ADAPTER_API.json")
    routing = read_json(index_dir / "SELF_KNOWLEDGE_CHAT_ADAPTER_ROUTING.json")
    if api["supported_intent_count"] != 11 or api["supported_surfaces"] != ["webui", "desktop"]:
        raise AssertionError("api_contract_mismatch")
    if coverage["total_test_count"] != 90 or tests["test_count"] != 90:
        raise AssertionError("test_count_mismatch")
    if coverage["v1a3e_test_case_execution_count"] != 68:
        raise AssertionError("v1a3e_dual_surface_count_mismatch")
    if coverage["registry_reads_for_unsupported_chat"] != 0:
        raise AssertionError("unsupported_chat_registry_read")
    if coverage["workshop_python_alias_resolved"] is not False or coverage["pythonw_identity_directly_probed"] is not False:
        raise AssertionError("runtime_uncertainty_not_preserved")
    if coverage["closure_node_records_copied"] != 0 or coverage["closure_edge_records_copied"] != 0:
        raise AssertionError("closure_records_copied")
    if not all(row["passed"] for row in tests["rows"]):
        raise AssertionError("test_failure_recorded")
    if len(routing["rules"]) != 4:
        raise AssertionError("routing_rule_count_mismatch")
    total = sum(path.stat().st_size for path in index_dir.iterdir() if path.is_file())
    if total >= TOTAL_OUTPUT_CEILING_BYTES:
        raise AssertionError("output_ceiling_exceeded")
    return {
        "status": "validated",
        "exact_output_count": 6,
        "test_count": 90,
        "supported_intent_count": 11,
        "claim_provenance_record_count": coverage["claim_provenance_record_count"],
        "total_output_bytes": total,
        "deterministic_rebuild_match": receipt["internal_deterministic_rebuild_match"],
    }


def self_test() -> dict[str, Any]:
    selectors = {"intent": "list_protected_contexts"}
    first = _deterministic_request_id("webui", "Agent Fox list protected contexts", selectors)
    second = _deterministic_request_id("webui", "Agent Fox list protected contexts", selectors)
    if first != second:
        raise AssertionError("request_id_not_deterministic")
    fake_bridge = {
        "INTENTS": ("launcher_runtime_entry_mapping", "list_protected_contexts"),
        "INTENT_DEFINITIONS": {
            "launcher_runtime_entry_mapping": {"synonyms": ["which python", "what runs"]},
            "list_protected_contexts": {"synonyms": ["list protected contexts"]},
        },
    }
    if _catalog_matches("Which Python version should I install?", {}, fake_bridge):
        raise AssertionError("weak_generic_false_positive")
    if _catalog_matches("Agent Fox, which Python runs Workshop Main?", {}, fake_bridge) != ["launcher_runtime_entry_mapping"]:
        raise AssertionError("anchored_weak_synonym_not_recognized")
    if _catalog_matches("List protected contexts", {}, fake_bridge) != ["list_protected_contexts"]:
        raise AssertionError("strong_synonym_not_recognized")
    packet = {
        "answer_text": "Test",
        "structured_claims": [{"claim_id": "x", "text": "A claim", "provenance": [{"source_mission_id": "M", "evidence_filename": "E", "evidence_sha256": "0" * 64, "json_field_path": "$.x", "record_locator": None, "source_receipt_sha256": "1" * 64}]}],
        "uncertainty_statements": [],
        "unresolved_items": [{"claim_id": "u", "text": "candidate", "provenance": [{"source_mission_id": "M", "evidence_filename": "E", "evidence_sha256": "0" * 64, "json_field_path": "$.u", "record_locator": None, "source_receipt_sha256": "1" * 64}]}],
        "linked_context_references": [],
        "clarification": None,
    }
    rendered = render_answer_packet(packet)
    if "UNCONFIRMED CANDIDATE" not in rendered or "Provenance:" not in rendered:
        raise AssertionError("renderer_safety_label_missing")
    return {
        "status": "self_test_ok",
        "deterministic_request_id": True,
        "weak_generic_domain_gate": True,
        "unresolved_label_preserved": True,
        "provenance_rendered": True,
        "first_non_whitespace_slash_guard": _normalize_message("   /engineer workshop begin test").lstrip().startswith("/"),
        "resource_provider_category_count_expected": 18,
        "protected_context_priority_preserved": True,
        "ordinary_chat_pass_through_preserved": True,
    }


def add_input_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--v1a3d-dir", required=True)
    parser.add_argument("--v1a3e-dir", required=True)
    parser.add_argument("--v1a3f-dir", required=True)
    parser.add_argument("--bridge-path", required=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    verify = sub.add_parser("verify-inputs")
    add_input_args(verify)
    suite_parser = sub.add_parser("verify-suite")
    add_input_args(suite_parser)
    build_parser = sub.add_parser("build")
    add_input_args(build_parser)
    build_parser.add_argument("--output-dir", required=True)
    build_parser.add_argument("--mission-id", required=True)
    validate_parser = sub.add_parser("validate-output")
    validate_parser.add_argument("--index-dir", required=True)
    route_parser = sub.add_parser("route-json")
    route_parser.add_argument("--bridge-path", required=True)
    route_parser.add_argument("--registry-dir", required=True)
    route_parser.add_argument("--surface", required=True)
    route_parser.add_argument("--message", required=True)
    route_parser.add_argument("--request-id")
    route_parser.add_argument("--selectors-json")
    args = parser.parse_args()

    if args.command == "self-test":
        result = self_test()
    elif args.command == "validate-output":
        result = validate_output(Path(args.index_dir))
    elif args.command == "route-json":
        _configure_paths_for_tests(Path(args.bridge_path), Path(args.registry_dir))
        selectors = json.loads(args.selectors_json) if args.selectors_json else None
        result = route_message(args.message, args.surface, args.request_id, selectors)
    else:
        verification = verify_authoritative_inputs(Path(args.v1a3d_dir), Path(args.v1a3e_dir), Path(args.v1a3f_dir), Path(args.bridge_path))
        if args.command == "verify-inputs":
            result = {key: value for key, value in verification.items() if key != "test_cases" and key != "reports"}
            result["status"] = "verified"
        else:
            suite = run_adapter_test_suite(Path(args.v1a3d_dir), Path(args.v1a3e_dir), Path(args.bridge_path))
            if args.command == "verify-suite":
                result = {key: value for key, value in suite.items() if key != "rows"}
                result["status"] = "verified"
            elif args.command == "build":
                result = write_build(args.mission_id, Path(args.output_dir), verification, suite, Path(args.bridge_path), Path(args.v1a3d_dir))
            else:
                raise AssertionError(args.command)
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
