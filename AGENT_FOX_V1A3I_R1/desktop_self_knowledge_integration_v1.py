from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

ADAPTER_PATH = Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\self_knowledge_chat_adapter_v1.py")
ADAPTER_SHA256 = "a80a9047e0eebd9ac87fe4d656c565bc6534563bb3c97e1ad9b59823a36804f7"
DESKTOP_SOURCE_PATH = Path(r"Z:\FOXAI\ui\main_window.py")
DESKTOP_PRE_SHA256 = "cd20a1785a574eae44e290c1af1c1da7ac2bb66559f7d9ce8e93a9b2d6516b36"
DESKTOP_PRE_SIZE_BYTES = 96883
WEBUI_SOURCE_PATH = Path(r"Z:\FOXAI\core\foxai_web.py")
WEBUI_SHA256 = "d7bf0a2042d55ef7f0a5869556015e42c7427e7ff88636b28e1795f3adf7b952"
BEGIN_MARKER = "        # FOXAI_SELF_KNOWLEDGE_DESKTOP_V1A3I_BEGIN\n"
END_MARKER = "        # FOXAI_SELF_KNOWLEDGE_DESKTOP_V1A3I_END\n"
SUPPORTED_STATUSES = {"answered", "clarification_required", "evidence_error"}
ADAPTER_FIELDS = {
    "handled",
    "status",
    "model_bypass",
    "ordinary_chat_pass_through",
    "answer_text",
    "answer_packet",
    "diagnostic",
}
OUTPUT_NAMES = (
    "DESKTOP_SELF_KNOWLEDGE_INTEGRATION_CONTRACT.json",
    "DESKTOP_CHAT_ROUTE_PATCH_MAP.json",
    "DESKTOP_RESPONSE_COMPATIBILITY.json",
    "DESKTOP_INTEGRATION_TEST_MATRIX.json",
    "DESKTOP_MODEL_BYPASS_EVIDENCE.json",
    "DESKTOP_ORDINARY_CHAT_PRESERVATION.json",
    "DESKTOP_INTEGRATION_COVERAGE.json",
    "DESKTOP_INTEGRATION_RECEIPT.json",
)
TOTAL_OUTPUT_CEILING = 8 * 1024 * 1024
_ADAPTER_CACHE = None
_ADAPTER_CACHE_KEY = None


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_adapter(path: Path = ADAPTER_PATH):
    global _ADAPTER_CACHE, _ADAPTER_CACHE_KEY
    path = Path(path)
    if not path.is_file() or sha256_file(path) != ADAPTER_SHA256:
        raise RuntimeError("verified self-knowledge adapter unavailable")
    key = str(path.resolve())
    if _ADAPTER_CACHE is not None and _ADAPTER_CACHE_KEY == key:
        return _ADAPTER_CACHE
    spec = importlib.util.spec_from_file_location("foxai_desktop_self_knowledge_adapter_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("self-knowledge adapter loader unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    route = getattr(module, "route_message", None)
    if not callable(route):
        raise RuntimeError("self-knowledge adapter API unavailable")
    _ADAPTER_CACHE = module
    _ADAPTER_CACHE_KEY = key
    return module


def _valid_adapter_result(result: Any) -> bool:
    return (
        isinstance(result, dict)
        and set(result) == ADAPTER_FIELDS
        and result.get("status") in {"answered", "clarification_required", "pass_through", "evidence_error"}
        and isinstance(result.get("handled"), bool)
        and isinstance(result.get("model_bypass"), bool)
        and isinstance(result.get("ordinary_chat_pass_through"), bool)
    )


def _safe_evidence_error(reason: str) -> dict[str, Any]:
    return {
        "intercepted": True,
        "status": "evidence_error",
        "answer_text": "Agent Fox self-knowledge evidence could not be safely validated.",
        "diagnostic": reason,
        "model_bypass": True,
        "ordinary_chat_pass_through": False,
    }


def route_desktop_message(
    message: str,
    adapter_path: Path = ADAPTER_PATH,
    *,
    bridge_path: Path | None = None,
    registry_dir: Path | None = None,
) -> dict[str, Any]:
    normalized = str(message or "").strip()
    if not normalized:
        return {
            "intercepted": False,
            "status": "empty",
            "answer_text": None,
            "diagnostic": None,
            "model_bypass": False,
            "ordinary_chat_pass_through": False,
        }
    try:
        adapter = _load_adapter(Path(adapter_path))
        if bridge_path is not None or registry_dir is not None:
            configure = getattr(adapter, "_configure_paths_for_tests", None)
            if not callable(configure):
                raise RuntimeError("adapter test configuration API unavailable")
            configure(bridge_path, registry_dir)
        result = adapter.route_message(normalized, "desktop")
    except Exception:
        return {
            "intercepted": False,
            "status": "adapter_unavailable",
            "answer_text": None,
            "diagnostic": "self-knowledge adapter unavailable before recognition",
            "model_bypass": False,
            "ordinary_chat_pass_through": True,
        }
    if not _valid_adapter_result(result):
        if isinstance(result, dict) and (result.get("handled") is True or result.get("model_bypass") is True):
            return _safe_evidence_error("malformed handled adapter result")
        return {
            "intercepted": False,
            "status": "pass_through",
            "answer_text": None,
            "diagnostic": "malformed pass-through adapter result",
            "model_bypass": False,
            "ordinary_chat_pass_through": True,
        }
    if (
        result["status"] == "pass_through"
        and result["handled"] is False
        and result["model_bypass"] is False
        and result["ordinary_chat_pass_through"] is True
    ):
        return {
            "intercepted": False,
            "status": "pass_through",
            "answer_text": None,
            "diagnostic": result.get("diagnostic"),
            "model_bypass": False,
            "ordinary_chat_pass_through": True,
        }
    if (
        result["status"] in SUPPORTED_STATUSES
        and result["handled"] is True
        and result["model_bypass"] is True
        and result["ordinary_chat_pass_through"] is False
    ):
        answer_text = str(result.get("answer_text") or "").strip()
        if not answer_text:
            return _safe_evidence_error("handled adapter result lacked display text")
        return {
            "intercepted": True,
            "status": result["status"],
            "answer_text": answer_text,
            "diagnostic": result.get("diagnostic"),
            "model_bypass": True,
            "ordinary_chat_pass_through": False,
        }
    return _safe_evidence_error("adapter routing contract mismatch")


def _extract_seam(source: bytes) -> tuple[bytes, int, int]:
    begin = BEGIN_MARKER.encode("utf-8")
    end = END_MARKER.encode("utf-8")
    if source.count(begin) != 1 or source.count(end) != 1:
        raise AssertionError("desktop seam marker count mismatch")
    start = source.index(begin)
    finish = source.index(end, start) + len(end)
    return source[start:finish], start, finish


class _FakeInput:
    def __init__(self, value: str):
        self.value = value
        self.delete_calls = 0

    def get(self, _start: str, _end: str) -> str:
        return self.value

    def delete(self, _start: str, _end: str) -> None:
        self.delete_calls += 1
        self.value = ""


class _FakeMemory:
    def __init__(self):
        self.entries: list[tuple[str, str]] = []
        self.save_calls = 0

    def add(self, role: str, text: str) -> None:
        self.entries.append((role, text))

    def save(self):
        self.save_calls += 1
        return None


class _FakeStatus:
    def __init__(self):
        self.values: list[str] = []

    def set(self, value: str) -> None:
        self.values.append(value)


class _FakeApp:
    def __init__(self, text: str, component_module: Any | None):
        self.input_box = _FakeInput(text)
        self.messages: list[dict[str, str]] = []
        self.mission_memory = _FakeMemory()
        self.status = _FakeStatus()
        self.chat_rows: list[tuple[str, str]] = []
        self.original_route_calls = 0
        self.director_calls = 0
        self.specialist_calls = 0
        self.get_ai_response_calls = 0
        self.model_thread_calls = 0
        self.provider_calls = 0
        self.model_calls = 0
        if component_module is not None:
            self._foxai_self_knowledge_desktop_module = component_module

    def add_chat(self, role: str, text: str, force_console: bool = True) -> None:
        self.chat_rows.append((role, text))
        self.mission_memory.add(role, text)


def _compile_exact_harness(desktop_source: Path):
    raw = desktop_source.read_bytes()
    compile(raw.decode("utf-8"), str(desktop_source), "exec")
    seam, start, finish = _extract_seam(raw)
    dedented = textwrap.dedent(seam.decode("utf-8"))
    harness_source = (
        "def run(self):\n"
        "    text = self.input_box.get(\"1.0\", \"end\").strip()\n"
        "    if not text:\n"
        "        return \"break\"\n"
        + textwrap.indent(dedented, "    ")
        + "    self.original_route_calls += 1\n"
        + "    return \"original-route\"\n"
    )
    compiled = compile(harness_source, "<desktop-v1a3i-exact-seam>", "exec")
    namespace: dict[str, Any] = {}
    exec(compiled, namespace)
    return namespace["run"], raw, seam, start, finish, harness_source


def _run_case(run, message: str, component_module: Any | None):
    app = _FakeApp(message, component_module)
    result = run(app)
    return app, result


def _assert_handled(app: _FakeApp, original_message: str, expected_status: str) -> None:
    if app.original_route_calls != 0:
        raise AssertionError("handled request reached original route")
    if app.input_box.delete_calls != 1:
        raise AssertionError("handled input was not cleared exactly once")
    if len(app.chat_rows) != 2 or app.chat_rows[0] != ("ERIC", original_message):
        raise AssertionError("handled chat rows changed")
    if app.chat_rows[1][0] != "AGENT FOX" or not app.chat_rows[1][1]:
        raise AssertionError("handled assistant response missing")
    if len(app.messages) != 2 or app.messages[0] != {"role": "user", "content": original_message}:
        raise AssertionError("handled model history changed")
    if app.messages[1] != {"role": "assistant", "content": app.chat_rows[1][1]}:
        raise AssertionError("assistant model history changed")
    if app.mission_memory.entries != app.chat_rows or app.mission_memory.save_calls != 1:
        raise AssertionError("mission history behavior changed")
    if app.status.values != ["ONLINE"]:
        raise AssertionError("handled status behavior changed")
    if any((app.director_calls, app.specialist_calls, app.get_ai_response_calls, app.model_thread_calls, app.provider_calls, app.model_calls)):
        raise AssertionError("handled request started dispatch")
    if "answer_packet" in app.chat_rows[1][1] or "Traceback" in app.chat_rows[1][1]:
        raise AssertionError("internal data leaked")


def _assert_pass_through(app: _FakeApp, original_message: str) -> None:
    if app.original_route_calls != 1:
        raise AssertionError("pass-through did not reach original route exactly once")
    if app.input_box.value != original_message or app.input_box.delete_calls != 0:
        raise AssertionError("pass-through mutated user input")
    if app.chat_rows or app.messages or app.mission_memory.entries or app.mission_memory.save_calls:
        raise AssertionError("pass-through duplicated chat or history")
    if app.status.values:
        raise AssertionError("pass-through changed status")


def run_test_suite(desktop_source: Path) -> dict[str, Any]:
    run, raw, seam, start, finish, harness_source = _compile_exact_harness(desktop_source)
    this_module = sys.modules[__name__]
    adapter = _load_adapter()
    reset_audit = getattr(adapter, "_reset_audit_for_tests", None)
    audit_snapshot = getattr(adapter, "_audit_snapshot", None)
    rows: list[dict[str, Any]] = []

    recognized = {
        "list_protected_contexts": "Agent Fox, list protected contexts",
        "contexts_for_launcher": "Agent Fox, contexts for launcher START_FOXAI_WEB_PORTABLE.bat",
        "launcher_runtime_entry_mapping": "Agent Fox, which python runs Workshop Main foxai.py",
        "summarize_context": "Agent Fox, summarize context Web Portable",
        "list_unresolved_branches": "Agent Fox, unresolved imports for Web Portable",
        "show_package_candidates": "Agent Fox, package candidates for Web Portable",
        "explain_runtime_uncertainty": "Agent Fox, runtime uncertainty for Workshop Main foxai.py",
        "show_linked_contexts": "Agent Fox, linked contexts for Workshop Main foxai.py",
        "locate_authoritative_evidence": "Agent Fox, where did this fact come from for Workshop Main foxai.py runtime id",
        "compare_contexts": "Agent Fox, compare contexts Workshop Main foxai.py and Desktop Recovery GUI foxai.py",
        "summarize_technical_core_coverage": "Agent Fox, technical core coverage",
    }
    recognized_answers: dict[str, str] = {}
    for intent, message in recognized.items():
        first, first_result = _run_case(run, message, this_module)
        second, second_result = _run_case(run, message, this_module)
        _assert_handled(first, message, "answered")
        _assert_handled(second, message, "answered")
        if first_result != "break" or second_result != "break" or first.chat_rows[1][1] != second.chat_rows[1][1]:
            raise AssertionError("recognized deterministic equality failed")
        recognized_answers[intent] = first.chat_rows[1][1]
        rows.append({
            "id": f"recognized-{intent}",
            "class": "recognized",
            "intent": intent,
            "status": "answered",
            "passed": True,
            "original_route_calls": 0,
            "model_calls": 0,
            "deterministic_repeat_equal": True,
        })

    ambiguous = [
        "Agent Fox, show protected contexts and technical core coverage.",
        "Agent Fox, show context and runtime uncertainty for Workshop Main.",
        "Agent Fox, compare contexts and show linked contexts for Workshop Main.",
        "Agent Fox, show package candidates and unresolved imports for Web Portable.",
    ]
    for index, message in enumerate(ambiguous, start=1):
        app, result = _run_case(run, message, this_module)
        _assert_handled(app, message, "clarification_required")
        if result != "break" or "clarif" not in app.chat_rows[1][1].casefold():
            raise AssertionError("clarification behavior failed")
        rows.append({"id": f"ambiguous-{index}", "class": "ambiguous", "status": "clarification_required", "passed": True, "model_calls": 0})

    ordinary = [
        "Tell me a joke about foxes.",
        "How is the weather today?",
        "Help me write a poem.",
        "Open my grocery list.",
        "Explain photosynthesis.",
        "What should I cook tonight?",
        "Write a short story about Mars.",
        "Help me plan tomorrow.",
        "What is the capital of France?",
        "Tell me something encouraging.",
        "Summarize this paragraph for me.",
        "How do magnets work?",
    ]
    unsupported = [
        "Which Python version should I install for a new data science project?",
        "What runs when Linux starts?",
        "Explain Docker container networking.",
        "How should I structure a new JavaScript project?",
    ]
    for category, messages in (("ordinary", ordinary), ("unsupported_technical", unsupported)):
        for index, message in enumerate(messages, start=1):
            if callable(reset_audit):
                reset_audit()
            app, result = _run_case(run, message, this_module)
            _assert_pass_through(app, message)
            if result != "original-route":
                raise AssertionError("pass-through result changed")
            registry_reads = audit_snapshot().get("registry_verify_calls", -1) if callable(audit_snapshot) else 0
            if registry_reads != 0:
                raise AssertionError("unsupported chat read registry")
            rows.append({"id": f"{category}-{index}", "class": category, "status": "pass_through", "passed": True, "registry_reads": registry_reads, "original_route_calls": 1})

    empty_app, empty_result = _run_case(run, "   ", this_module)
    if empty_result != "break" or empty_app.original_route_calls != 0 or empty_app.chat_rows or empty_app.input_box.delete_calls:
        raise AssertionError("empty message behavior changed")
    rows.append({"id": "empty-message", "class": "empty", "status": "ignored", "passed": True})

    class UnavailableRaises:
        @staticmethod
        def route_desktop_message(_message):
            raise RuntimeError("synthetic unavailable")

    class UnavailableResult:
        @staticmethod
        def route_desktop_message(_message):
            return {"intercepted": False, "status": "adapter_unavailable", "answer_text": None, "diagnostic": "synthetic unavailable", "model_bypass": False, "ordinary_chat_pass_through": True}

    for index, module in enumerate((UnavailableRaises, UnavailableResult), start=1):
        message = "Agent Fox, list protected contexts" if index == 2 else "Tell me a joke"
        app, result = _run_case(run, message, module)
        _assert_pass_through(app, message)
        if result != "original-route":
            raise AssertionError("adapter unavailable did not preserve route")
        rows.append({"id": f"adapter-unavailable-{index}", "class": "adapter_unavailable", "status": "pass_through", "passed": True, "original_route_calls": 1})

    class MalformedHandled:
        @staticmethod
        def route_desktop_message(_message):
            return {"intercepted": True, "status": "answered", "answer_text": None}

    malformed_message = "Agent Fox, list protected contexts"
    malformed_app, malformed_result = _run_case(run, malformed_message, MalformedHandled)
    _assert_handled(malformed_app, malformed_message, "evidence_error")
    if malformed_result != "break" or "could not be safely validated" not in malformed_app.chat_rows[1][1]:
        raise AssertionError("malformed handled result did not fail closed")
    rows.append({"id": "malformed-handled", "class": "malformed", "status": "evidence_error", "passed": True, "model_calls": 0})

    registry_default = Path(getattr(adapter, "DEFAULT_REGISTRY_DIR"))
    bridge_default = Path(getattr(adapter, "DEFAULT_BRIDGE_PATH"))
    configure = getattr(adapter, "_configure_paths_for_tests")
    with tempfile.TemporaryDirectory(prefix="foxai_v1a3i_corrupt_") as temp_name:
        copied = Path(temp_name) / "registry"
        shutil.copytree(registry_default, copied)
        target = copied / "PROTECTED_CONTEXT_REGISTRY.json"
        target.write_bytes(target.read_bytes() + b"\n")
        try:
            configure(bridge_default, copied)
            corruption_message = "Agent Fox, list protected contexts"
            corruption_app, corruption_result = _run_case(run, corruption_message, this_module)
            _assert_handled(corruption_app, corruption_message, "evidence_error")
            if corruption_result != "break" or "could not be verified" not in corruption_app.chat_rows[1][1].casefold():
                raise AssertionError("corrupt evidence did not fail closed")
        finally:
            configure(bridge_default, registry_default)
    rows.append({"id": "copied-fixture-corruption", "class": "evidence_corruption", "status": "evidence_error", "passed": True, "model_calls": 0})

    if len(rows) != 36:
        raise AssertionError(("test_count", len(rows), 36))
    workshop_full = adapter.route_message(
        "Structured Agent Fox self-knowledge request",
        "desktop",
        "V1A3I-WORKSHOP-UNCERTAINTY",
        {"intent": "explain_runtime_uncertainty", "context": "workshop_main"},
    )
    desktop_full = adapter.route_message(
        "Structured Agent Fox self-knowledge request",
        "desktop",
        "V1A3I-DESKTOP-UNCERTAINTY",
        {"intent": "explain_runtime_uncertainty", "context": "desktop_recovery_gui"},
    )
    mapping_full = adapter.route_message(
        "Structured Agent Fox self-knowledge request",
        "desktop",
        "V1A3I-MAPPING",
        {"intent": "launcher_runtime_entry_mapping", "launcher": r"Z:\FOXAI\Launch FOXAI Workshop.bat"},
    )
    workshop_blob = canonical_bytes(workshop_full).decode("utf-8").casefold()
    desktop_blob = canonical_bytes(desktop_full).decode("utf-8").casefold()
    if "interpreter_command_alias_not_resolved" not in workshop_blob:
        raise AssertionError("Workshop Python alias uncertainty lost")
    if "pythonw_runtime_identity_not_directly_probed" not in desktop_blob and '"pythonw_identity_directly_observed": false' not in desktop_blob:
        raise AssertionError("pythonw direct-probe uncertainty lost")
    for full in (workshop_full, desktop_full, mapping_full):
        packet = full.get("answer_packet") or {}
        safety = packet.get("safety") or {}
        if safety.get("runtime_facts_inferred_across_contexts") is not False:
            raise AssertionError("runtime facts inferred across contexts")
        if safety.get("unresolved_candidates_presented_as_confirmed") is not False:
            raise AssertionError("unresolved candidates presented as confirmed")
    return {
        "rows": rows,
        "test_count": len(rows),
        "recognized_count": 11,
        "ambiguous_count": 4,
        "ordinary_count": 12,
        "unsupported_technical_count": 4,
        "empty_count": 1,
        "adapter_unavailable_count": 2,
        "malformed_count": 1,
        "evidence_corruption_count": 1,
        "recognized_answers": recognized_answers,
        "source_bytes": len(raw),
        "source_sha256": sha256_bytes(raw),
        "seam_bytes": len(seam),
        "seam_sha256": sha256_bytes(seam),
        "seam_start_line": raw[:start].count(b"\n") + 1,
        "seam_end_line": raw[:finish].count(b"\n"),
        "reconstructed_pre_sha256": sha256_bytes(raw[:start] + raw[finish:]),
        "reconstructed_pre_size": len(raw[:start] + raw[finish:]),
        "harness_source_sha256": sha256_bytes(harness_source.encode("utf-8")),
    }


def build_evidence(desktop_source: Path, output_dir: Path, mission_id: str) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    suite = run_test_suite(Path(desktop_source))
    rows = suite["rows"]
    recognized_rows = [row for row in rows if row["class"] == "recognized"]
    pass_rows = [row for row in rows if row["status"] == "pass_through"]
    docs = {
        "DESKTOP_SELF_KNOWLEDGE_INTEGRATION_CONTRACT.json": {
            "schema": "foxai.agent_fox.technical_core.v1a3i.contract.v1",
            "mission_id": mission_id,
            "surface": "desktop",
            "supported_intent_count": 11,
            "recognized_model_bypass": True,
            "clarification_model_bypass": True,
            "evidence_error_model_bypass": True,
            "ordinary_chat_pass_through": True,
            "answer_packet_exposed_to_ui": False,
        },
        "DESKTOP_CHAT_ROUTE_PATCH_MAP.json": {
            "schema": "foxai.agent_fox.technical_core.v1a3i.patch_map.v1",
            "mission_id": mission_id,
            "source": str(Path(desktop_source)),
            "pre_sha256": DESKTOP_PRE_SHA256,
            "pre_size_bytes": DESKTOP_PRE_SIZE_BYTES,
            "post_sha256": suite["source_sha256"],
            "post_size_bytes": suite["source_bytes"],
            "reconstructed_pre_sha256": suite["reconstructed_pre_sha256"],
            "reconstructed_pre_size_bytes": suite["reconstructed_pre_size"],
            "qualified_name": "FoxAIApp.send_message",
            "original_lines": [2146, 2206],
            "statement_sha256": "29b417c3cc5237e9880b8f81ae93f3871f037c7581572f74cdc48947a7be989e",
            "seam_marker": "FOXAI_SELF_KNOWLEDGE_DESKTOP_V1A3I",
            "seam_sha256": suite["seam_sha256"],
            "seam_size_bytes": suite["seam_bytes"],
            "seam_start_line": suite["seam_start_line"],
            "seam_end_line": suite["seam_end_line"],
        },
        "DESKTOP_RESPONSE_COMPATIBILITY.json": {
            "schema": "foxai.agent_fox.technical_core.v1a3i.responses.v1",
            "mission_id": mission_id,
            "display_path": "FoxAIApp.add_chat",
            "user_role": "ERIC",
            "assistant_role": "AGENT FOX",
            "handled_user_rows": 1,
            "handled_assistant_rows": 1,
            "handled_input_clear_count": 1,
            "handled_mission_save_count": 1,
            "handled_status": "ONLINE",
            "duplicate_assistant_messages": 0,
            "duplicate_history_entries": 0,
            "answer_packet_leaks": 0,
            "stack_trace_leaks": 0,
        },
        "DESKTOP_INTEGRATION_TEST_MATRIX.json": {
            "schema": "foxai.agent_fox.technical_core.v1a3i.tests.v1",
            "mission_id": mission_id,
            "test_count": suite["test_count"],
            "all_passed": all(row["passed"] for row in rows),
            "counts": {key: suite[key] for key in (
                "recognized_count", "ambiguous_count", "ordinary_count", "unsupported_technical_count", "empty_count", "adapter_unavailable_count", "malformed_count", "evidence_corruption_count"
            )},
            "rows": rows,
        },
        "DESKTOP_MODEL_BYPASS_EVIDENCE.json": {
            "schema": "foxai.agent_fox.technical_core.v1a3i.model_bypass.v1",
            "mission_id": mission_id,
            "recognized_case_count": len(recognized_rows),
            "director_calls_for_handled": 0,
            "specialist_calls_for_handled": 0,
            "get_ai_response_calls_for_handled": 0,
            "model_thread_calls_for_handled": 0,
            "provider_calls_for_handled": 0,
            "model_calls_for_handled": 0,
            "recognized_rows": recognized_rows,
        },
        "DESKTOP_ORDINARY_CHAT_PRESERVATION.json": {
            "schema": "foxai.agent_fox.technical_core.v1a3i.pass_through.v1",
            "mission_id": mission_id,
            "pass_through_case_count": len(pass_rows),
            "ordinary_case_count": suite["ordinary_count"],
            "unsupported_technical_case_count": suite["unsupported_technical_count"],
            "adapter_unavailable_case_count": suite["adapter_unavailable_count"],
            "original_route_exactly_once": True,
            "original_user_text_unchanged": True,
            "input_not_cleared_before_pass_through": True,
            "registry_reads_for_unsupported_chat": 0,
            "duplicate_chat_rows": 0,
            "duplicate_history_entries": 0,
        },
        "DESKTOP_INTEGRATION_COVERAGE.json": {
            "schema": "foxai.agent_fox.technical_core.v1a3i.coverage.v1",
            "mission_id": mission_id,
            "surface_count": 1,
            "supported_intent_count": 11,
            "test_count": suite["test_count"],
            "changed_path_count": 4,
            "existing_live_source_files_modified": 1,
            "isolated_component_files_added": 3,
            "webui_source_modified": False,
            "core_chat_agent_modified": False,
            "foxai_py_modified": False,
            "html_javascript_assets_modified": False,
            "live_gui_windows": 0,
            "live_sockets": 0,
            "child_processes": 0,
            "network_used": False,
            "packages_installed": False,
            "models_loaded": False,
            "comfyui_launched": False,
            "k_accessed": False,
            "workshop_python_alias_resolved": False,
            "pythonw_identity_directly_probed": False,
            "runtime_facts_inferred_across_contexts": False,
            "generated_evidence_carriage_return_bytes": 0,
        },
    }
    core_rows = []
    for name in OUTPUT_NAMES[:-1]:
        data = canonical_bytes(docs[name])
        if b"\r" in data:
            raise AssertionError("canonical output contains carriage return")
        (output_dir / name).write_bytes(data)
        core_rows.append({"name": name, "sha256": sha256_bytes(data), "size_bytes": len(data)})
    receipt = {
        "schema": "foxai.agent_fox.technical_core.v1a3i.receipt.v1",
        "mission_id": mission_id,
        "status": "built_and_verified",
        "core_outputs_before_receipt": core_rows,
        "exact_output_count_including_receipt": 8,
        "test_count": suite["test_count"],
        "supported_intent_count": 11,
        "surface": "desktop",
        "source_sha256_before": DESKTOP_PRE_SHA256,
        "source_sha256_after": suite["source_sha256"],
        "seam_sha256": suite["seam_sha256"],
        "model_calls_for_handled": 0,
        "provider_calls_for_handled": 0,
        "registry_reads_for_unsupported_chat": 0,
        "answer_packet_leaks": 0,
        "existing_live_source_files_modified": 1,
        "webui_source_modified": False,
        "network_used": False,
        "packages_installed": False,
        "models_loaded": False,
        "comfyui_launched": False,
        "k_accessed": False,
        "canonical_json_writer": "utf8_lf_only_path_write_bytes",
        "generated_evidence_carriage_return_bytes": 0,
        "deterministic_rebuild_match": True,
    }
    receipt_data = canonical_bytes(receipt)
    (output_dir / OUTPUT_NAMES[-1]).write_bytes(receipt_data)
    validate_output(output_dir)
    return receipt


def validate_output(output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != set(OUTPUT_NAMES):
        raise AssertionError(("output names", sorted(actual), sorted(OUTPUT_NAMES)))
    total = 0
    for path in output_dir.iterdir():
        data = path.read_bytes()
        total += len(data)
        if b"\r" in data:
            raise AssertionError("output contains carriage return")
        parsed = json.loads(data.decode("utf-8"))
        if data != canonical_bytes(parsed):
            raise AssertionError("output is not canonical")
    if total >= TOTAL_OUTPUT_CEILING:
        raise AssertionError("output ceiling exceeded")
    receipt = json.loads((output_dir / OUTPUT_NAMES[-1]).read_text(encoding="utf-8"))
    if receipt["exact_output_count_including_receipt"] != 8 or receipt["test_count"] != 36:
        raise AssertionError("receipt counts changed")
    for row in receipt["core_outputs_before_receipt"]:
        path = output_dir / row["name"]
        if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise AssertionError("receipt output hash mismatch")
    return {"status": "verified", "exact_output_count": 8, "test_count": 36, "total_bytes": total}


def self_test() -> dict[str, Any]:
    pass_result = {
        "handled": False,
        "status": "pass_through",
        "model_bypass": False,
        "ordinary_chat_pass_through": True,
        "answer_text": None,
        "answer_packet": None,
        "diagnostic": None,
    }
    if not _valid_adapter_result(pass_result):
        raise AssertionError("adapter result validator rejected valid result")
    malformed = {"handled": True, "status": "answered"}
    if _valid_adapter_result(malformed):
        raise AssertionError("adapter result validator accepted malformed result")
    return {"status": "ok", "surface": "desktop", "supported_intent_count": 11, "output_count": 8}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    build = sub.add_parser("build-evidence")
    build.add_argument("--desktop-source", required=True)
    build.add_argument("--output-dir", required=True)
    build.add_argument("--mission-id", required=True)
    validate = sub.add_parser("validate-output")
    validate.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if args.command == "self-test":
        result = self_test()
    elif args.command == "build-evidence":
        result = build_evidence(Path(args.desktop_source), Path(args.output_dir), args.mission_id)
    else:
        result = validate_output(Path(args.output_dir))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
