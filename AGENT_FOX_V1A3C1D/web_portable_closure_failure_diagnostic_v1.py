from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path, PureWindowsPath
from typing import Any

SCHEMA_PREFIX = "foxai.agent_fox.technical_core.v1a3c1d"
PROJECT_ROOT_DEFAULT = r"Z:\FOXAI"
SUBJECT_BUILDER_DEFAULT = r"Z:\FOXAI\AGENT_FOX_V1A3C1\web_portable_dependency_closure_v1.py"
SUBJECT_BUILDER_SHA256 = "da458a9a2eeca42b86d43b13ffb113a8417f182399683e758e56b74d8317f322"
TARGET_LAUNCHER = r"Z:\FOXAI\START_FOXAI_WEB_PORTABLE.bat"
TARGET_SCRIPT = r"Z:\FOXAI\core\foxai_web.py"
TARGET_INTERPRETER = r"Z:\FOXAI\env\python\python.exe"
SOURCE_BUFFER_CEILING_BYTES = 8 * 1024 * 1024
DIAGNOSTIC_OUTPUT_CEILING_BYTES = 1 * 1024 * 1024
NORMAL_OUTPUT_NAMES = {
    "WEB_PORTABLE_CONTEXT.json",
    "WEB_PORTABLE_FIRST_PARTY_CLOSURE.json",
    "WEB_PORTABLE_CONDITIONAL_IMPORTS.json",
    "WEB_PORTABLE_PACKAGE_REQUIREMENTS.json",
    "WEB_PORTABLE_UNRESOLVED_BRANCHES.json",
    "WEB_PORTABLE_COVERAGE.json",
    "WEB_PORTABLE_CLOSURE_RECEIPT.json",
}
DIAGNOSTIC_OUTPUT_NAMES = (
    "V1A3C1_FAILURE_DIAGNOSTIC.json",
    "V1A3C1_FAILURE_TRACEBACK.txt",
    "V1A3C1_DIAGNOSTIC_RECEIPT.json",
)


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def win_case(value: Any) -> str:
    return str(value or "").replace("/", "\\").strip().strip('"').casefold()


def load_subject(subject_path: Path) -> tuple[dict[str, Any], str]:
    if not subject_path.is_file() or subject_path.is_symlink():
        raise FileNotFoundError(subject_path)
    raw = subject_path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != SUBJECT_BUILDER_SHA256:
        raise ValueError(
            f"Exact V1A-3C1 subject hash mismatch: expected {SUBJECT_BUILDER_SHA256}, got {digest}"
        )
    text = raw.decode("utf-8")
    namespace: dict[str, Any] = {
        "__name__": "v1a3c1_diagnostic_subject",
        "__file__": str(subject_path),
        "__package__": None,
    }
    exec(compile(text, str(subject_path), "exec"), namespace, namespace)
    return namespace, digest


def safe_value(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return "<depth-limit>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:2048]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, PureWindowsPath):
        return str(value)
    if isinstance(value, dict):
        allowed = {}
        for key in sorted(value, key=lambda item: str(item))[:40]:
            name = str(key)
            if name.casefold() in {"data", "text", "source", "outputs_a", "outputs_b", "tree"}:
                continue
            allowed[name] = safe_value(value[key], depth + 1)
        return allowed
    if isinstance(value, (list, tuple)):
        return [safe_value(item, depth + 1) for item in value[:20]]
    if isinstance(value, set):
        return [safe_value(item, depth + 1) for item in sorted(value, key=str)[:20]]
    return f"<{value.__class__.__name__}>"


def traceback_diagnostics(exc: BaseException) -> dict[str, Any]:
    current_source_path = None
    current_import_record = None
    counters: dict[str, Any] = {}
    selected_frames: list[dict[str, Any]] = []
    tb = exc.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        local_values = frame.f_locals
        frame_item: dict[str, Any] = {
            "function": frame.f_code.co_name,
            "filename": frame.f_code.co_filename,
            "line": tb.tb_lineno,
        }
        captured: dict[str, Any] = {}
        for name in (
            "source_path", "current", "local_path", "path", "indexed_import", "catalog_record",
            "static_resolution", "record", "edge", "source_module", "module", "name",
        ):
            if name in local_values:
                captured[name] = safe_value(local_values[name])
        if captured:
            frame_item["selected_locals"] = captured
        selected_frames.append(frame_item)
        for name in ("source_path", "current", "local_path"):
            candidate = local_values.get(name)
            if candidate is not None:
                current_source_path = str(candidate)
        for name in ("indexed_import", "catalog_record", "static_resolution", "record", "edge"):
            candidate = local_values.get(name)
            if isinstance(candidate, dict):
                current_import_record = safe_value(candidate)
        for name in ("nodes", "edges", "unresolved", "source_records", "visited", "queue", "read_counts"):
            candidate = local_values.get(name)
            if candidate is not None:
                try:
                    counters[f"{name}_count"] = len(candidate)
                except TypeError:
                    pass
        for name in ("peak_source_bytes", "parsed_import_count"):
            candidate = local_values.get(name)
            if isinstance(candidate, int):
                counters[name] = candidate
        tb = tb.tb_next
    return {
        "current_source_path": current_source_path,
        "current_import_record": current_import_record,
        "traceback_frames": selected_frames,
        "frame_counters": counters,
    }


def mark_stage(stages: list[dict[str, Any]], name: str, status: str, started: float, details: dict[str, Any] | None = None) -> None:
    row = {
        "name": name,
        "status": status,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    if details:
        row["details"] = details
    stages.append(row)


def verify_known_good_without_source_reread(
    subject: dict[str, Any],
    project_root_path: Path,
    project_root_win: str,
    known_good: dict[str, Any],
    parsed: dict[str, Any],
) -> list[dict[str, Any]]:
    cached = {
        win_case(row.get("path")): {
            "sha256": str(row.get("sha256")),
            "size_bytes": int(row.get("size_bytes") or -1),
        }
        for row in parsed.get("source_records", [])
    }
    checks: list[dict[str, Any]] = []
    separately_read: set[str] = set()
    for row in known_good.get("records", []):
        path_text = str(row.get("path"))
        key = win_case(path_text)
        expected = str(row.get("expected_sha256"))
        if key in cached:
            digest = cached[key]["sha256"]
            origin = "reused_reached_source_hash_without_reread"
        else:
            if key in separately_read:
                raise ValueError(f"Known-good file would be read more than once: {path_text}")
            path = subject["source_local_path"](project_root_path, project_root_win, path_text)
            if not path.is_file() or path.is_symlink():
                raise FileNotFoundError(path)
            size = path.stat().st_size
            if size > SOURCE_BUFFER_CEILING_BYTES:
                raise ValueError(f"Known-good buffer ceiling exceeded: {path_text} ({size} bytes)")
            digest = sha256_file(path)
            separately_read.add(key)
            origin = "read_once_for_known_good_verification"
        if digest != expected:
            raise ValueError(f"Protected known-good hash changed: {path_text}")
        checks.append({"path": path_text, "sha256": digest, "status": "match", "verification_origin": origin})
    return checks


def write_diagnostic_outputs(
    output_dir: Path,
    mission_id: str,
    diagnostic: dict[str, Any],
    traceback_text: str,
) -> None:
    if output_dir.exists():
        raise FileExistsError(f"Diagnostic output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    diagnostic_bytes = canonical_json_bytes(diagnostic)
    traceback_bytes = (traceback_text.rstrip() + "\n").encode("utf-8")
    if len(diagnostic_bytes) + len(traceback_bytes) >= DIAGNOSTIC_OUTPUT_CEILING_BYTES:
        raise ValueError("Diagnostic output ceiling exceeded before receipt")
    first_path = output_dir / DIAGNOSTIC_OUTPUT_NAMES[0]
    second_path = output_dir / DIAGNOSTIC_OUTPUT_NAMES[1]
    first_path.write_bytes(diagnostic_bytes)
    second_path.write_bytes(traceback_bytes)
    receipt = {
        "schema": f"{SCHEMA_PREFIX}.diagnostic_receipt.v1",
        "mission_id": mission_id,
        "result": diagnostic.get("result"),
        "diagnostic_command_returned_success_after_recording": True,
        "captured_exception": diagnostic.get("result") == "captured_failure",
        "unexpected_success": diagnostic.get("result") == "unexpected_success",
        "last_successful_stage": diagnostic.get("last_successful_stage"),
        "protected_direct_context_count": diagnostic.get("protected_direct_context_count"),
        "normal_closure_outputs_generated": False,
        "source_or_package_imports_executed": False,
        "foxai_source_or_launcher_executed": False,
        "interpreter_child_processes": 0,
        "shell_child_processes": 0,
        "network_used": False,
        "packages_installed": False,
        "models_loaded": False,
        "raw_source_content_persisted": False,
        "diagnostic_outputs_before_receipt": [
            {"name": first_path.name, "size_bytes": len(diagnostic_bytes), "sha256": sha256_bytes(diagnostic_bytes)},
            {"name": second_path.name, "size_bytes": len(traceback_bytes), "sha256": sha256_bytes(traceback_bytes)},
        ],
    }
    receipt_bytes = canonical_json_bytes(receipt)
    if len(diagnostic_bytes) + len(traceback_bytes) + len(receipt_bytes) >= DIAGNOSTIC_OUTPUT_CEILING_BYTES:
        raise ValueError("Diagnostic output ceiling exceeded including receipt")
    (output_dir / DIAGNOSTIC_OUTPUT_NAMES[2]).write_bytes(receipt_bytes)


def diagnose(
    project_root_path: Path,
    project_root_win: str,
    subject_path: Path,
    v1a2r2_dir: Path,
    v1a3a_r1_dir: Path,
    v1a3b_dir: Path,
    output_dir: Path,
    mission_id: str,
) -> None:
    overall_started = time.perf_counter()
    stages: list[dict[str, Any]] = []
    last_successful_stage = None
    subject: dict[str, Any] | None = None
    source = context = catalogs = closure = parsed = protected_checks = outputs_a = outputs_b = None
    subject_digest = None
    result = "captured_failure"
    exception_info: dict[str, Any] | None = None
    traceback_text = ""
    try:
        started = time.perf_counter()
        subject, subject_digest = load_subject(subject_path)
        mark_stage(stages, "subject_builder_verification_and_load", "completed", started, {"sha256": subject_digest})
        last_successful_stage = "subject_builder_verification_and_load"

        started = time.perf_counter()
        source = subject["load_verified_sources"](v1a2r2_dir, v1a3a_r1_dir, v1a3b_dir)
        mark_stage(stages, "evidence_loading", "completed", started, {
            "source_launcher_record_count": source["v1a3b_coverage"].get("source_launcher_record_count"),
            "source_code_file_count": source["v1a3b_coverage"].get("source_code_file_count"),
        })
        last_successful_stage = "evidence_loading"

        started = time.perf_counter()
        context = subject["select_web_portable_context"](source)
        if win_case(context.get("launcher_path")) != win_case(TARGET_LAUNCHER):
            raise ValueError("Selected launcher is not the protected Web Portable launcher")
        if win_case(context.get("script_path")) != win_case(TARGET_SCRIPT):
            raise ValueError("Selected script is not core\\foxai_web.py")
        if win_case(context.get("resolved_interpreter_path")) != win_case(TARGET_INTERPRETER):
            raise ValueError("Selected interpreter is not env\\python\\python.exe")
        mark_stage(stages, "context_selection", "completed", started, {
            "context_id": context.get("context_id"),
            "path_group_id": context.get("path_group_id"),
        })
        last_successful_stage = "context_selection"

        started = time.perf_counter()
        catalogs = subject["provider_catalogs"](source)
        mark_stage(stages, "provider_catalog_construction", "completed", started, {
            "first_party_provider_count": len(catalogs.get("first_party", [])),
            "third_party_provider_count": len(catalogs.get("tp_by_id", {})),
        })
        last_successful_stage = "provider_catalog_construction"

        started = time.perf_counter()
        closure = subject["preliminary_static_closure"](source, context, catalogs)
        mark_stage(stages, "preliminary_closure_construction", "completed", started, {
            "reached_node_count": len(closure.get("nodes", [])),
            "edge_count": len(closure.get("edges", [])),
            "unresolved_count": len(closure.get("unresolved", [])),
        })
        last_successful_stage = "preliminary_closure_construction"

        started = time.perf_counter()
        parsed = subject["parse_reached_sources_once"](
            project_root_path, project_root_win, source, closure, catalogs
        )
        mark_stage(stages, "reached_source_parsing", "completed", started, {
            "source_read_count": parsed.get("source_files_read_count"),
            "maximum_reads_per_source_file": parsed.get("maximum_reads_per_source_file"),
            "peak_source_bytes": parsed.get("peak_source_bytes_in_memory"),
            "parsed_import_count": parsed.get("parsed_import_count"),
        })
        last_successful_stage = "reached_source_parsing"

        started = time.perf_counter()
        protected_checks = verify_known_good_without_source_reread(
            subject, project_root_path, project_root_win, source["known_good"], parsed
        )
        mark_stage(stages, "protected_known_good_verification", "completed", started, {
            "protected_check_count": len(protected_checks),
        })
        last_successful_stage = "protected_known_good_verification"

        started = time.perf_counter()
        outputs_a = subject["build_core_outputs"](
            mission_id, source, context, closure, parsed, protected_checks
        )
        mark_stage(stages, "core_output_construction_a", "completed", started, {
            "output_count": len(outputs_a),
        })
        last_successful_stage = "core_output_construction_a"

        started = time.perf_counter()
        outputs_b = subject["build_core_outputs"](
            mission_id, source, context, closure, parsed, protected_checks
        )
        mark_stage(stages, "core_output_construction_b", "completed", started, {
            "output_count": len(outputs_b),
        })
        last_successful_stage = "core_output_construction_b"

        started = time.perf_counter()
        output_names = tuple(subject["OUTPUT_NAMES"])
        bytes_a = {name: subject["canonical_json_bytes"](outputs_a[name]) for name in output_names}
        bytes_b = {name: subject["canonical_json_bytes"](outputs_b[name]) for name in output_names}
        if bytes_a != bytes_b:
            raise ValueError("Immutable compact-record deterministic rebuild failed")
        mark_stage(stages, "deterministic_comparison", "completed", started, {
            "compared_output_count": len(output_names),
        })
        last_successful_stage = "deterministic_comparison"

        started = time.perf_counter()
        prepared_sizes = {name: len(bytes_a[name]) for name in output_names}
        prepared_total = sum(prepared_sizes.values())
        if prepared_total >= int(subject["OUTPUT_CEILING_BYTES"]):
            raise ValueError(f"Original closure output ceiling would be exceeded: {prepared_total}")
        mark_stage(stages, "normal_output_preparation_without_write", "completed", started, {
            "prepared_output_count": len(prepared_sizes),
            "prepared_total_bytes": prepared_total,
            "normal_outputs_written": False,
        })
        last_successful_stage = "normal_output_preparation_without_write"
        result = "unexpected_success"
        traceback_text = "The previously failing V1A-3C1 closure path completed unexpectedly during diagnostic reproduction. No normal closure outputs were written.\n"
    except BaseException as exc:
        diagnostic_tb = traceback_diagnostics(exc)
        exception_info = {
            "exception_type": exc.__class__.__name__,
            "message": str(exc),
            **diagnostic_tb,
        }
        traceback_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        stages.append({
            "name": "captured_failure",
            "status": "captured",
            "elapsed_seconds": round(time.perf_counter() - overall_started, 6),
            "details": {
                "exception_type": exc.__class__.__name__,
                "message": str(exc)[:2048],
            },
        })

    closure_counts = {
        "reached_node_count": len(closure.get("nodes", [])) if isinstance(closure, dict) else 0,
        "edge_count": len(closure.get("edges", [])) if isinstance(closure, dict) else 0,
        "unresolved_count": len(closure.get("unresolved", [])) if isinstance(closure, dict) else 0,
    }
    parse_counts = {
        "source_read_count": parsed.get("source_files_read_count", 0) if isinstance(parsed, dict) else 0,
        "maximum_reads_per_source_file": parsed.get("maximum_reads_per_source_file", 0) if isinstance(parsed, dict) else 0,
        "peak_source_bytes": parsed.get("peak_source_bytes_in_memory", 0) if isinstance(parsed, dict) else 0,
        "parsed_import_count": parsed.get("parsed_import_count", 0) if isinstance(parsed, dict) else 0,
    }
    if exception_info:
        frame_counters = exception_info.get("frame_counters", {})
        closure_counts["reached_node_count"] = max(closure_counts["reached_node_count"], int(frame_counters.get("nodes_count", 0)))
        closure_counts["edge_count"] = max(closure_counts["edge_count"], int(frame_counters.get("edges_count", 0)))
        closure_counts["unresolved_count"] = max(closure_counts["unresolved_count"], int(frame_counters.get("unresolved_count", 0)))
        parse_counts["source_read_count"] = max(parse_counts["source_read_count"], int(frame_counters.get("source_records_count", 0)))
        parse_counts["peak_source_bytes"] = max(parse_counts["peak_source_bytes"], int(frame_counters.get("peak_source_bytes", 0)))
        parse_counts["parsed_import_count"] = max(parse_counts["parsed_import_count"], int(frame_counters.get("parsed_import_count", 0)))

    diagnostic = {
        "schema": f"{SCHEMA_PREFIX}.failure_diagnostic.v1",
        "mission_id": mission_id,
        "subject_mission_id": "ENG-20260721-172935-37F095",
        "subject_plan_sha256": "23ec8fc9bcc9e9c6dafb4375430c6f867c612735f157a19c52d6af07f042449a",
        "subject_builder_path": str(subject_path),
        "subject_builder_sha256": subject_digest,
        "result": result,
        "last_successful_stage": last_successful_stage,
        "elapsed_seconds": round(time.perf_counter() - overall_started, 6),
        "protected_direct_context_count": 1 if context else 0,
        "context": {
            "context_id": context.get("context_id") if isinstance(context, dict) else None,
            "path_group_id": context.get("path_group_id") if isinstance(context, dict) else None,
            "launcher_path": context.get("launcher_path") if isinstance(context, dict) else TARGET_LAUNCHER,
            "script_path": context.get("script_path") if isinstance(context, dict) else TARGET_SCRIPT,
            "resolved_interpreter_path": context.get("resolved_interpreter_path") if isinstance(context, dict) else TARGET_INTERPRETER,
        },
        "stage_markers": stages,
        "closure_counters": closure_counts,
        "parse_counters": parse_counts,
        "exception": exception_info,
        "safety": {
            "normal_closure_outputs_written": False,
            "source_or_package_imports_executed": False,
            "foxai_source_or_launcher_executed": False,
            "interpreter_child_processes": 0,
            "shell_child_processes": 0,
            "network_used": False,
            "packages_installed": False,
            "models_loaded": False,
            "raw_source_content_persisted": False,
            "only_verified_evidence_and_reached_first_party_sources_read": True,
            "source_buffer_ceiling_bytes": SOURCE_BUFFER_CEILING_BYTES,
            "diagnostic_output_ceiling_bytes": DIAGNOSTIC_OUTPUT_CEILING_BYTES,
        },
    }
    write_diagnostic_outputs(output_dir, mission_id, diagnostic, traceback_text)
    print(json.dumps({
        "status": "diagnostic_recorded",
        "result": result,
        "last_successful_stage": last_successful_stage,
        "output_dir": str(output_dir),
    }, sort_keys=True))


def verify_inputs(subject_path: Path, v1a2r2_dir: Path, v1a3a_r1_dir: Path, v1a3b_dir: Path) -> None:
    subject, digest = load_subject(subject_path)
    source = subject["load_verified_sources"](v1a2r2_dir, v1a3a_r1_dir, v1a3b_dir)
    context = subject["select_web_portable_context"](source)
    if win_case(context.get("launcher_path")) != win_case(TARGET_LAUNCHER):
        raise ValueError("Wrong launcher selected")
    if win_case(context.get("script_path")) != win_case(TARGET_SCRIPT):
        raise ValueError("Wrong entry script selected")
    if win_case(context.get("resolved_interpreter_path")) != win_case(TARGET_INTERPRETER):
        raise ValueError("Wrong interpreter selected")
    print(json.dumps({
        "status": "verified",
        "subject_builder_sha256": digest,
        "context_id": context.get("context_id"),
        "path_group_id": context.get("path_group_id"),
        "source_launcher_record_count": source["v1a3b_coverage"].get("source_launcher_record_count"),
        "source_code_file_count": source["v1a3b_coverage"].get("source_code_file_count"),
    }, sort_keys=True))


def validate_diagnostic(index_dir: Path) -> None:
    if not index_dir.is_dir():
        raise FileNotFoundError(index_dir)
    present = {path.name for path in index_dir.iterdir() if path.is_file()}
    required = set(DIAGNOSTIC_OUTPUT_NAMES)
    if present != required:
        raise ValueError(f"Diagnostic output set mismatch: expected {sorted(required)}, found {sorted(present)}")
    if present & NORMAL_OUTPUT_NAMES:
        raise ValueError("Normal closure outputs were generated")
    diagnostic = read_json(index_dir / DIAGNOSTIC_OUTPUT_NAMES[0])
    receipt = read_json(index_dir / DIAGNOSTIC_OUTPUT_NAMES[2])
    if diagnostic.get("result") not in {"captured_failure", "unexpected_success"}:
        raise ValueError("Unexpected diagnostic result")
    if receipt.get("diagnostic_command_returned_success_after_recording") is not True:
        raise ValueError("Diagnostic command did not record success-after-capture")
    if receipt.get("normal_closure_outputs_generated") is not False:
        raise ValueError("Receipt claims normal outputs")
    if diagnostic.get("protected_direct_context_count") not in {0, 1}:
        raise ValueError("Invalid protected context count")
    if int(diagnostic.get("parse_counters", {}).get("maximum_reads_per_source_file") or 0) > 1:
        raise ValueError("A reached source was read more than once")
    if int(diagnostic.get("parse_counters", {}).get("peak_source_bytes") or 0) > SOURCE_BUFFER_CEILING_BYTES:
        raise ValueError("Source buffer ceiling exceeded")
    for item in receipt.get("diagnostic_outputs_before_receipt", []):
        path = index_dir / str(item.get("name"))
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != int(item.get("size_bytes") or -1):
            raise ValueError(f"Size mismatch: {path.name}")
        if sha256_file(path) != str(item.get("sha256")):
            raise ValueError(f"Hash mismatch: {path.name}")
    total = sum(path.stat().st_size for path in index_dir.iterdir() if path.is_file())
    if total >= DIAGNOSTIC_OUTPUT_CEILING_BYTES:
        raise ValueError(f"Diagnostic output ceiling exceeded: {total}")
    print(json.dumps({
        "status": "valid",
        "result": diagnostic.get("result"),
        "last_successful_stage": diagnostic.get("last_successful_stage"),
        "exception_type": (diagnostic.get("exception") or {}).get("exception_type"),
        "total_output_bytes": total,
    }, sort_keys=True))


def show_summary(index_dir: Path) -> None:
    diagnostic = read_json(index_dir / DIAGNOSTIC_OUTPUT_NAMES[0])
    print(json.dumps({
        "result": diagnostic.get("result"),
        "last_successful_stage": diagnostic.get("last_successful_stage"),
        "exception": diagnostic.get("exception"),
        "closure_counters": diagnostic.get("closure_counters"),
        "parse_counters": diagnostic.get("parse_counters"),
    }, indent=2, sort_keys=True))


def self_test() -> None:
    def inner() -> None:
        source_path = r"Z:\FOXAI\core\sample.py"
        indexed_import = {"line": 7, "kind": "import", "module": "demo", "name": None}
        nodes = [1, 2]
        edges = [1]
        unresolved = []
        peak_source_bytes = 123
        raise ValueError("diagnostic-self-test")
    try:
        inner()
    except ValueError as exc:
        captured = traceback_diagnostics(exc)
        assert captured.get("current_source_path", "").casefold().endswith(r"core\sample.py")
        assert captured.get("current_import_record", {}).get("module") == "demo"
        assert captured.get("frame_counters", {}).get("nodes_count") == 2
        assert captured.get("frame_counters", {}).get("edges_count") == 1
        assert captured.get("frame_counters", {}).get("peak_source_bytes") == 123
    assert canonical_json_bytes({"b": 2, "a": 1}) == canonical_json_bytes({"a": 1, "b": 2})
    print("V1A3C1D_SELF_TEST_OK")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V1A-3C1 deterministic closure failure diagnostic")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")

    verify = sub.add_parser("verify-inputs")
    verify.add_argument("--subject-builder", default=SUBJECT_BUILDER_DEFAULT)
    verify.add_argument("--v1a2r2-dir", required=True)
    verify.add_argument("--v1a3a-r1-dir", required=True)
    verify.add_argument("--v1a3b-dir", required=True)

    diag = sub.add_parser("diagnose")
    diag.add_argument("--project-root", default=PROJECT_ROOT_DEFAULT)
    diag.add_argument("--project-root-win", default=PROJECT_ROOT_DEFAULT)
    diag.add_argument("--subject-builder", default=SUBJECT_BUILDER_DEFAULT)
    diag.add_argument("--v1a2r2-dir", required=True)
    diag.add_argument("--v1a3a-r1-dir", required=True)
    diag.add_argument("--v1a3b-dir", required=True)
    diag.add_argument("--output-dir", required=True)
    diag.add_argument("--mission-id", required=True)

    validate = sub.add_parser("validate-diagnostic")
    validate.add_argument("--index-dir", required=True)

    summary = sub.add_parser("show-summary")
    summary.add_argument("--index-dir", required=True)

    args = parser.parse_args(argv)
    if args.command == "self-test":
        self_test()
    elif args.command == "verify-inputs":
        verify_inputs(Path(args.subject_builder), Path(args.v1a2r2_dir), Path(args.v1a3a_r1_dir), Path(args.v1a3b_dir))
    elif args.command == "diagnose":
        diagnose(
            Path(args.project_root), args.project_root_win, Path(args.subject_builder),
            Path(args.v1a2r2_dir), Path(args.v1a3a_r1_dir), Path(args.v1a3b_dir),
            Path(args.output_dir), args.mission_id,
        )
    elif args.command == "validate-diagnostic":
        validate_diagnostic(Path(args.index_dir))
    elif args.command == "show-summary":
        show_summary(Path(args.index_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
