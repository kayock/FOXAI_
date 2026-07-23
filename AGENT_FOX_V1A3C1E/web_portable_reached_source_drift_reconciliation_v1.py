from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import sys
import time
from collections import Counter
from pathlib import Path, PureWindowsPath
from typing import Any

SCHEMA_PREFIX = "foxai.agent_fox.technical_core.v1a3c1e"
SUBJECT_BUILDER_SHA256 = "da458a9a2eeca42b86d43b13ffb113a8417f182399683e758e56b74d8317f322"
TARGET_LAUNCHER = "Z:/FOXAI/START_FOXAI_WEB_PORTABLE.bat"
TARGET_SCRIPT = "Z:/FOXAI/core/foxai_web.py"
TARGET_INTERPRETER = "Z:/FOXAI/env/python/python.exe"
TARGET_CORE_INIT = "Z:/FOXAI/core/__init__.py"
EXPECTED_REACHED_NODES = 57
EXPECTED_EDGES = 165
EXPECTED_UNRESOLVED = 1
HASH_CHUNK_BYTES = 1024 * 1024
SOURCE_BUFFER_CEILING_BYTES = 8 * 1024 * 1024
OUTPUT_CEILING_BYTES = 2 * 1024 * 1024
OUTPUT_NAMES = (
    "WEB_PORTABLE_REACHED_SOURCE_DRIFT_REPORT.json",
    "WEB_PORTABLE_Z_K_COMPARISON.json",
    "WEB_PORTABLE_EVIDENCE_RECONCILIATION_SUMMARY.md",
    "WEB_PORTABLE_EVIDENCE_RECONCILIATION_RECEIPT.json",
)
CLASSIFICATIONS = (
    "unchanged",
    "active-and-rollback-match-but-evidence-stale",
    "active-differs-from-rollback",
    "missing-on-active",
    "missing-on-rollback",
    "rollback-only",
    "evidence-record-missing",
)


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def win_norm(value: Any) -> str:
    text = str(value or "").strip().strip('"').replace("/", "\\")
    return ntpath.normpath(text) if text else ""


def win_case(value: Any) -> str:
    return win_norm(value).casefold()


def load_subject(subject_path: Path) -> tuple[dict[str, Any], str]:
    if not subject_path.is_file() or subject_path.is_symlink():
        raise FileNotFoundError(subject_path)
    raw = subject_path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != SUBJECT_BUILDER_SHA256:
        raise ValueError(
            f"Exact V1A-3C1 subject hash mismatch: expected {SUBJECT_BUILDER_SHA256}, got {digest}"
        )
    namespace: dict[str, Any] = {
        "__name__": "v1a3c1e_subject",
        "__file__": str(subject_path),
        "__package__": None,
    }
    exec(compile(raw.decode("utf-8"), str(subject_path), "exec"), namespace, namespace)
    return namespace, digest


def relative_parts(source_path: str, project_root_win: str) -> tuple[str, ...]:
    source = PureWindowsPath(win_norm(source_path))
    root = PureWindowsPath(win_norm(project_root_win))
    try:
        relative = source.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Reached source is outside protected project root: {source_path}") from exc
    return relative.parts


def local_path(root_path: Path, source_path: str, project_root_win: str) -> Path:
    return root_path.joinpath(*relative_parts(source_path, project_root_win))


def observe_file(path: Path) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "path": str(path),
        "exists": False,
        "is_file": False,
        "is_symlink": False,
        "size_bytes": None,
        "sha256": None,
        "read_count": 0,
        "bytes_read": 0,
        "peak_buffer_bytes": 0,
    }
    if path.is_symlink():
        observation["exists"] = True
        observation["is_symlink"] = True
        return observation
    if not path.is_file():
        observation["exists"] = path.exists()
        return observation
    observation["exists"] = True
    observation["is_file"] = True
    digest = hashlib.sha256()
    total = 0
    peak = 0
    with path.open("rb") as handle:
        observation["read_count"] = 1
        while True:
            chunk = handle.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            if len(chunk) > SOURCE_BUFFER_CEILING_BYTES:
                raise ValueError(f"Source buffer ceiling exceeded while hashing: {path}")
            peak = max(peak, len(chunk))
            total += len(chunk)
            digest.update(chunk)
    observation["size_bytes"] = total
    observation["bytes_read"] = total
    observation["peak_buffer_bytes"] = peak
    observation["sha256"] = digest.hexdigest()
    return observation


def evidence_present(node: dict[str, Any] | None) -> bool:
    if not isinstance(node, dict):
        return False
    digest = str(node.get("expected_sha256") or "")
    size = node.get("expected_size_bytes")
    return len(digest) == 64 and isinstance(size, int) and size >= 0


def matches_evidence(observation: dict[str, Any], node: dict[str, Any]) -> bool:
    return bool(
        observation.get("is_file")
        and observation.get("sha256") == str(node.get("expected_sha256"))
        and observation.get("size_bytes") == int(node.get("expected_size_bytes"))
    )


def observations_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return bool(
        left.get("is_file")
        and right.get("is_file")
        and left.get("size_bytes") == right.get("size_bytes")
        and left.get("sha256") == right.get("sha256")
    )


def classify_record(
    node: dict[str, Any] | None,
    active: dict[str, Any],
    rollback: dict[str, Any],
) -> str:
    if not evidence_present(node):
        return "evidence-record-missing"
    if not active.get("is_file") and rollback.get("is_file"):
        return "rollback-only"
    if not active.get("is_file"):
        return "missing-on-active"
    if not rollback.get("is_file"):
        return "missing-on-rollback"
    if not observations_match(active, rollback):
        return "active-differs-from-rollback"
    if matches_evidence(active, node) and matches_evidence(rollback, node):
        return "unchanged"
    return "active-and-rollback-match-but-evidence-stale"


def verify_retained_diagnostic(diagnostic_dir: Path) -> dict[str, Any]:
    required = {
        "V1A3C1_FAILURE_DIAGNOSTIC.json",
        "V1A3C1_FAILURE_TRACEBACK.txt",
        "V1A3C1_DIAGNOSTIC_RECEIPT.json",
    }
    if not diagnostic_dir.is_dir():
        raise FileNotFoundError(diagnostic_dir)
    present = {path.name for path in diagnostic_dir.iterdir() if path.is_file()}
    if present != required:
        raise ValueError(f"Retained diagnostic file set mismatch: {sorted(present)}")
    diagnostic = read_json(diagnostic_dir / "V1A3C1_FAILURE_DIAGNOSTIC.json")
    receipt = read_json(diagnostic_dir / "V1A3C1_DIAGNOSTIC_RECEIPT.json")
    for item in receipt.get("diagnostic_outputs_before_receipt", []):
        path = diagnostic_dir / str(item.get("name"))
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != int(item.get("size_bytes") or -1):
            raise ValueError(f"Retained diagnostic size mismatch: {path.name}")
        if sha256_file(path) != str(item.get("sha256")):
            raise ValueError(f"Retained diagnostic hash mismatch: {path.name}")
    if diagnostic.get("mission_id") != "ENG-20260721-215227-E95BEF":
        raise ValueError("Wrong retained diagnostic mission")
    if diagnostic.get("result") != "captured_failure":
        raise ValueError("Retained diagnostic does not record captured failure")
    context = diagnostic.get("context", {})
    if win_case(context.get("launcher_path")) != win_case(TARGET_LAUNCHER):
        raise ValueError("Retained diagnostic launcher mismatch")
    if win_case(context.get("script_path")) != win_case(TARGET_SCRIPT):
        raise ValueError("Retained diagnostic script mismatch")
    if win_case(context.get("resolved_interpreter_path")) != win_case(TARGET_INTERPRETER):
        raise ValueError("Retained diagnostic interpreter mismatch")
    counts = diagnostic.get("closure_counters", {})
    if int(counts.get("reached_node_count") or -1) != EXPECTED_REACHED_NODES:
        raise ValueError("Retained diagnostic reached-node count mismatch")
    if int(counts.get("edge_count") or -1) != EXPECTED_EDGES:
        raise ValueError("Retained diagnostic edge count mismatch")
    if int(counts.get("unresolved_count") or -1) != EXPECTED_UNRESOLVED:
        raise ValueError("Retained diagnostic unresolved count mismatch")
    return {
        "diagnostic": diagnostic,
        "receipt": receipt,
        "diagnostic_sha256": sha256_file(diagnostic_dir / "V1A3C1_FAILURE_DIAGNOSTIC.json"),
        "traceback_sha256": sha256_file(diagnostic_dir / "V1A3C1_FAILURE_TRACEBACK.txt"),
        "receipt_sha256": sha256_file(diagnostic_dir / "V1A3C1_DIAGNOSTIC_RECEIPT.json"),
    }


def reconstruct_closure(
    subject_path: Path,
    v1a2r2_dir: Path,
    v1a3a_r1_dir: Path,
    v1a3b_dir: Path,
    diagnostic_dir: Path,
) -> dict[str, Any]:
    subject, subject_digest = load_subject(subject_path)
    source = subject["load_verified_sources"](v1a2r2_dir, v1a3a_r1_dir, v1a3b_dir)
    context = subject["select_web_portable_context"](source)
    if win_case(context.get("launcher_path")) != win_case(TARGET_LAUNCHER):
        raise ValueError("Selected launcher mismatch")
    if win_case(context.get("script_path")) != win_case(TARGET_SCRIPT):
        raise ValueError("Selected entry script mismatch")
    if win_case(context.get("resolved_interpreter_path")) != win_case(TARGET_INTERPRETER):
        raise ValueError("Selected interpreter mismatch")
    catalogs = subject["provider_catalogs"](source)
    closure = subject["preliminary_static_closure"](source, context, catalogs)
    if len(closure.get("nodes", [])) != EXPECTED_REACHED_NODES:
        raise ValueError(f"Expected {EXPECTED_REACHED_NODES} reached nodes")
    if len(closure.get("edges", [])) != EXPECTED_EDGES:
        raise ValueError(f"Expected {EXPECTED_EDGES} closure edges")
    if len(closure.get("unresolved", [])) != EXPECTED_UNRESOLVED:
        raise ValueError(f"Expected {EXPECTED_UNRESOLVED} unresolved branch")
    if len(closure.get("reached_paths", [])) != EXPECTED_REACHED_NODES:
        raise ValueError("Reached path count differs from reached-node count")
    retained = verify_retained_diagnostic(diagnostic_dir)
    return {
        "subject": subject,
        "subject_digest": subject_digest,
        "source": source,
        "context": context,
        "closure": closure,
        "retained": retained,
    }


def compare_reached_sources(
    reconstructed: dict[str, Any],
    active_root: Path,
    rollback_root: Path,
    project_root_win: str,
) -> dict[str, Any]:
    closure = reconstructed["closure"]
    nodes_by_key = {win_case(row.get("path")): row for row in closure.get("nodes", [])}
    records: list[dict[str, Any]] = []
    max_buffer = 0
    active_reads = 0
    rollback_reads = 0
    active_bytes = 0
    rollback_bytes = 0

    for source_path in closure.get("reached_paths", []):
        node = nodes_by_key.get(win_case(source_path))
        active_path = local_path(active_root, source_path, project_root_win)
        rollback_path = local_path(rollback_root, source_path, project_root_win)
        active = observe_file(active_path)
        rollback = observe_file(rollback_path)
        active_reads += int(active.get("read_count") or 0)
        rollback_reads += int(rollback.get("read_count") or 0)
        active_bytes += int(active.get("bytes_read") or 0)
        rollback_bytes += int(rollback.get("bytes_read") or 0)
        max_buffer = max(
            max_buffer,
            int(active.get("peak_buffer_bytes") or 0),
            int(rollback.get("peak_buffer_bytes") or 0),
        )
        classification = classify_record(node, active, rollback)
        record = {
            "source_path": source_path,
            "relative_path": str(PureWindowsPath(*relative_parts(source_path, project_root_win))),
            "evidence": {
                "present": evidence_present(node),
                "status": node.get("status") if isinstance(node, dict) else None,
                "expected_size_bytes": node.get("expected_size_bytes") if isinstance(node, dict) else None,
                "expected_sha256": node.get("expected_sha256") if isinstance(node, dict) else None,
                "indexed_import_count": node.get("indexed_import_count") if isinstance(node, dict) else None,
            },
            "active": active,
            "rollback": rollback,
            "comparison": {
                "active_matches_evidence": matches_evidence(active, node) if evidence_present(node) else None,
                "rollback_matches_evidence": matches_evidence(rollback, node) if evidence_present(node) else None,
                "active_matches_rollback": observations_match(active, rollback),
            },
            "classification": classification,
        }
        records.append(record)

    records.sort(key=lambda row: win_case(row.get("source_path")))
    counts = Counter(str(row.get("classification")) for row in records)
    classification_counts = {name: int(counts.get(name, 0)) for name in CLASSIFICATIONS}
    core_matches = [row for row in records if win_case(row.get("source_path")) == win_case(TARGET_CORE_INIT)]
    if len(core_matches) != 1:
        raise ValueError(f"Expected exactly one core/__init__.py record, found {len(core_matches)}")
    if max_buffer > SOURCE_BUFFER_CEILING_BYTES:
        raise ValueError(f"Source buffer ceiling exceeded: {max_buffer}")
    if any(int(row[side].get("read_count") or 0) > 1 for row in records for side in ("active", "rollback")):
        raise ValueError("A compared source was read more than once on one drive")
    return {
        "records": records,
        "classification_counts": classification_counts,
        "core_init_record": core_matches[0],
        "io": {
            "active_source_read_count": active_reads,
            "rollback_source_read_count": rollback_reads,
            "active_bytes_read": active_bytes,
            "rollback_bytes_read": rollback_bytes,
            "maximum_reads_per_source_per_drive": max(
                [int(row[side].get("read_count") or 0) for row in records for side in ("active", "rollback")]
                or [0]
            ),
            "peak_buffer_bytes": max_buffer,
            "hash_chunk_bytes": HASH_CHUNK_BYTES,
        },
    }


def markdown_summary(report: dict[str, Any]) -> str:
    counts = report["classification_counts"]
    core = report["core_init_record"]
    lines = [
        "# Web Portable Reached-Source Drift Reconciliation",
        "",
        f"Mission: `{report['mission_id']}`",
        "",
        "## Protected context",
        "",
        f"- Launcher: `{report['context']['launcher_path']}`",
        f"- Runtime: `{report['context']['resolved_interpreter_path']}`",
        f"- Entry script: `{report['context']['script_path']}`",
        "",
        "## Closure",
        "",
        f"- Reached sources: **{report['closure_counts']['reached_node_count']}**",
        f"- Dependency edges: **{report['closure_counts']['edge_count']}**",
        f"- Unresolved branches: **{report['closure_counts']['unresolved_count']}**",
        "",
        "## Classification counts",
        "",
    ]
    for name in CLASSIFICATIONS:
        lines.append(f"- `{name}`: **{counts.get(name, 0)}**")
    lines.extend([
        "",
        "## Exact core/__init__.py comparison",
        "",
        f"- Classification: `{core['classification']}`",
        f"- Evidence size: `{core['evidence']['expected_size_bytes']}`",
        f"- Evidence SHA-256: `{core['evidence']['expected_sha256']}`",
        f"- Active Z size: `{core['active']['size_bytes']}`",
        f"- Active Z SHA-256: `{core['active']['sha256']}`",
        f"- Rollback K size: `{core['rollback']['size_bytes']}`",
        f"- Rollback K SHA-256: `{core['rollback']['sha256']}`",
        "",
        "No evidence, source, launcher, runtime, Hanger Bay, database, or rollback-drive files were modified.",
        "",
    ])
    return "\n".join(lines)


def write_outputs(output_dir: Path, mission_id: str, reconstructed: dict[str, Any], comparison: dict[str, Any], active_root: Path, rollback_root: Path) -> None:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    context = reconstructed["context"]
    closure = reconstructed["closure"]
    report = {
        "schema": f"{SCHEMA_PREFIX}.reached_source_drift_report.v1",
        "mission_id": mission_id,
        "source_missions": [
            "ENG-20260721-063725-BFCAB9",
            "ENG-20260721-152146-C4F8D5",
            "ENG-20260721-154935-FF96C4",
            "ENG-20260721-215227-E95BEF",
        ],
        "subject_builder_sha256": reconstructed["subject_digest"],
        "active_root": str(active_root),
        "rollback_root": str(rollback_root),
        "rollback_root_access": "read_only",
        "context": {
            "context_id": context.get("context_id"),
            "path_group_id": context.get("path_group_id"),
            "launcher_path": context.get("launcher_path"),
            "script_path": context.get("script_path"),
            "resolved_interpreter_path": context.get("resolved_interpreter_path"),
        },
        "closure_counts": {
            "reached_node_count": len(closure.get("nodes", [])),
            "edge_count": len(closure.get("edges", [])),
            "unresolved_count": len(closure.get("unresolved", [])),
        },
        "classification_counts": comparison["classification_counts"],
        "records": comparison["records"],
        "core_init_record": comparison["core_init_record"],
        "io": comparison["io"],
        "safety": {
            "source_or_launcher_execution": False,
            "source_or_package_imports_executed": False,
            "normal_closure_outputs_generated": False,
            "interpreter_child_processes": 0,
            "shell_child_processes": 0,
            "network_used": False,
            "packages_installed": False,
            "models_loaded": False,
            "active_source_files_modified": False,
            "rollback_source_files_modified": False,
            "hanger_bay_modified": False,
            "maximum_reads_per_source_per_drive": comparison["io"]["maximum_reads_per_source_per_drive"],
            "source_buffer_ceiling_bytes": SOURCE_BUFFER_CEILING_BYTES,
        },
    }
    zk = {
        "schema": f"{SCHEMA_PREFIX}.z_k_comparison.v1",
        "mission_id": mission_id,
        "active_drive": "Z:",
        "rollback_drive": "K:",
        "compared_source_count": len(comparison["records"]),
        "classification_counts": comparison["classification_counts"],
        "records": [
            {
                "source_path": row["source_path"],
                "classification": row["classification"],
                "active_size_bytes": row["active"]["size_bytes"],
                "active_sha256": row["active"]["sha256"],
                "rollback_size_bytes": row["rollback"]["size_bytes"],
                "rollback_sha256": row["rollback"]["sha256"],
                "active_matches_rollback": row["comparison"]["active_matches_rollback"],
                "active_matches_evidence": row["comparison"]["active_matches_evidence"],
                "rollback_matches_evidence": row["comparison"]["rollback_matches_evidence"],
            }
            for row in comparison["records"]
        ],
        "rollback_write_operations": 0,
    }
    report_path = output_dir / OUTPUT_NAMES[0]
    zk_path = output_dir / OUTPUT_NAMES[1]
    summary_path = output_dir / OUTPUT_NAMES[2]
    report_path.write_bytes(canonical_json_bytes(report))
    zk_path.write_bytes(canonical_json_bytes(zk))
    summary_path.write_text(markdown_summary(report), encoding="utf-8", newline="\n")
    receipt = {
        "schema": f"{SCHEMA_PREFIX}.reconciliation_receipt.v1",
        "mission_id": mission_id,
        "result": "comparison_recorded",
        "compared_source_count": len(comparison["records"]),
        "classification_counts": comparison["classification_counts"],
        "core_init_classification": comparison["core_init_record"]["classification"],
        "active_source_read_count": comparison["io"]["active_source_read_count"],
        "rollback_source_read_count": comparison["io"]["rollback_source_read_count"],
        "maximum_reads_per_source_per_drive": comparison["io"]["maximum_reads_per_source_per_drive"],
        "peak_buffer_bytes": comparison["io"]["peak_buffer_bytes"],
        "rollback_write_operations": 0,
        "active_source_write_operations": 0,
        "source_or_launcher_execution": False,
        "source_or_package_imports_executed": False,
        "interpreter_child_processes": 0,
        "shell_child_processes": 0,
        "network_used": False,
        "packages_installed": False,
        "models_loaded": False,
        "normal_closure_outputs_generated": False,
        "outputs_before_receipt": [
            {"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in (report_path, zk_path, summary_path)
        ],
    }
    receipt_path = output_dir / OUTPUT_NAMES[3]
    receipt_path.write_bytes(canonical_json_bytes(receipt))
    total = sum(path.stat().st_size for path in output_dir.iterdir() if path.is_file())
    if total >= OUTPUT_CEILING_BYTES:
        raise ValueError(f"Reconciliation output ceiling exceeded: {total}")


def verify_inputs(args: argparse.Namespace) -> None:
    reconstructed = reconstruct_closure(
        Path(args.subject_builder), Path(args.v1a2r2_dir), Path(args.v1a3a_r1_dir),
        Path(args.v1a3b_dir), Path(args.diagnostic_dir),
    )
    context = reconstructed["context"]
    closure = reconstructed["closure"]
    print(json.dumps({
        "status": "verified",
        "subject_builder_sha256": reconstructed["subject_digest"],
        "context_id": context.get("context_id"),
        "path_group_id": context.get("path_group_id"),
        "reached_node_count": len(closure.get("nodes", [])),
        "edge_count": len(closure.get("edges", [])),
        "unresolved_count": len(closure.get("unresolved", [])),
    }, sort_keys=True))


def reconcile(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    reconstructed = reconstruct_closure(
        Path(args.subject_builder), Path(args.v1a2r2_dir), Path(args.v1a3a_r1_dir),
        Path(args.v1a3b_dir), Path(args.diagnostic_dir),
    )
    comparison = compare_reached_sources(
        reconstructed, Path(args.active_root), Path(args.rollback_root), args.project_root_win,
    )
    write_outputs(
        Path(args.output_dir), args.mission_id, reconstructed, comparison,
        Path(args.active_root), Path(args.rollback_root),
    )
    print(json.dumps({
        "status": "comparison_recorded",
        "mission_id": args.mission_id,
        "reached_source_count": len(comparison["records"]),
        "classification_counts": comparison["classification_counts"],
        "core_init_classification": comparison["core_init_record"]["classification"],
        "maximum_reads_per_source_per_drive": comparison["io"]["maximum_reads_per_source_per_drive"],
        "peak_buffer_bytes": comparison["io"]["peak_buffer_bytes"],
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "output_dir": args.output_dir,
    }, sort_keys=True))


def validate_outputs(index_dir: Path) -> None:
    if not index_dir.is_dir():
        raise FileNotFoundError(index_dir)
    present = {path.name for path in index_dir.iterdir() if path.is_file()}
    if present != set(OUTPUT_NAMES):
        raise ValueError(f"Output set mismatch: {sorted(present)}")
    report = read_json(index_dir / OUTPUT_NAMES[0])
    zk = read_json(index_dir / OUTPUT_NAMES[1])
    receipt = read_json(index_dir / OUTPUT_NAMES[3])
    if int(report.get("closure_counts", {}).get("reached_node_count") or -1) != EXPECTED_REACHED_NODES:
        raise ValueError("Reached-node count mismatch")
    if int(report.get("closure_counts", {}).get("edge_count") or -1) != EXPECTED_EDGES:
        raise ValueError("Edge count mismatch")
    if int(report.get("closure_counts", {}).get("unresolved_count") or -1) != EXPECTED_UNRESOLVED:
        raise ValueError("Unresolved count mismatch")
    records = report.get("records", [])
    if len(records) != EXPECTED_REACHED_NODES:
        raise ValueError("Record count mismatch")
    if len(zk.get("records", [])) != EXPECTED_REACHED_NODES:
        raise ValueError("Z/K record count mismatch")
    counts = report.get("classification_counts", {})
    if sum(int(counts.get(name) or 0) for name in CLASSIFICATIONS) != EXPECTED_REACHED_NODES:
        raise ValueError("Classification counts do not sum to reached source count")
    if any(str(row.get("classification")) not in CLASSIFICATIONS for row in records):
        raise ValueError("Unknown classification")
    core = report.get("core_init_record", {})
    if win_case(core.get("source_path")) != win_case(TARGET_CORE_INIT):
        raise ValueError("Exact core/__init__.py record missing")
    maximum_reads = int(report.get("io", {}).get("maximum_reads_per_source_per_drive") or 0)
    if maximum_reads > 1:
        raise ValueError("Source read ceiling exceeded")
    if int(report.get("io", {}).get("peak_buffer_bytes") or 0) > SOURCE_BUFFER_CEILING_BYTES:
        raise ValueError("Source buffer ceiling exceeded")
    if receipt.get("rollback_write_operations") != 0 or receipt.get("active_source_write_operations") != 0:
        raise ValueError("Receipt records a source-drive write")
    if receipt.get("normal_closure_outputs_generated") is not False:
        raise ValueError("Receipt claims normal closure outputs")
    for item in receipt.get("outputs_before_receipt", []):
        path = index_dir / str(item.get("name"))
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != int(item.get("size_bytes") or -1):
            raise ValueError(f"Output size mismatch: {path.name}")
        if sha256_file(path) != str(item.get("sha256")):
            raise ValueError(f"Output hash mismatch: {path.name}")
    total = sum(path.stat().st_size for path in index_dir.iterdir() if path.is_file())
    if total >= OUTPUT_CEILING_BYTES:
        raise ValueError(f"Output ceiling exceeded: {total}")
    print(json.dumps({
        "status": "valid",
        "reached_source_count": len(records),
        "classification_counts": counts,
        "core_init_classification": core.get("classification"),
        "total_output_bytes": total,
    }, sort_keys=True))


def show_summary(index_dir: Path) -> None:
    report = read_json(index_dir / OUTPUT_NAMES[0])
    core = report["core_init_record"]
    print(json.dumps({
        "mission_id": report.get("mission_id"),
        "classification_counts": report.get("classification_counts"),
        "core_init": {
            "classification": core.get("classification"),
            "expected_size_bytes": core.get("evidence", {}).get("expected_size_bytes"),
            "expected_sha256": core.get("evidence", {}).get("expected_sha256"),
            "active_size_bytes": core.get("active", {}).get("size_bytes"),
            "active_sha256": core.get("active", {}).get("sha256"),
            "rollback_size_bytes": core.get("rollback", {}).get("size_bytes"),
            "rollback_sha256": core.get("rollback", {}).get("sha256"),
        },
        "io": report.get("io"),
    }, sort_keys=True))


def self_test() -> None:
    evidence = {"expected_sha256": "a" * 64, "expected_size_bytes": 1}
    missing = {"is_file": False, "sha256": None, "size_bytes": None}
    a = {"is_file": True, "sha256": "a" * 64, "size_bytes": 1}
    b = {"is_file": True, "sha256": "b" * 64, "size_bytes": 1}
    stale = {"is_file": True, "sha256": "c" * 64, "size_bytes": 1}
    assert classify_record(evidence, a, a) == "unchanged"
    assert classify_record(evidence, stale, stale) == "active-and-rollback-match-but-evidence-stale"
    assert classify_record(evidence, a, b) == "active-differs-from-rollback"
    assert classify_record(evidence, missing, missing) == "missing-on-active"
    assert classify_record(evidence, a, missing) == "missing-on-rollback"
    assert classify_record(evidence, missing, a) == "rollback-only"
    assert classify_record(None, a, a) == "evidence-record-missing"
    assert win_case("Z:/FOXAI/core/__init__.py") == win_case(r"Z:\FOXAI\core\__init__.py")
    print("V1A3C1E_SELF_TEST_OK")


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser()
    sub = top.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    verify = sub.add_parser("verify-inputs")
    run = sub.add_parser("reconcile")
    for target in (verify, run):
        target.add_argument("--subject-builder", required=True)
        target.add_argument("--v1a2r2-dir", required=True)
        target.add_argument("--v1a3a-r1-dir", required=True)
        target.add_argument("--v1a3b-dir", required=True)
        target.add_argument("--diagnostic-dir", required=True)
    run.add_argument("--active-root", required=True)
    run.add_argument("--rollback-root", required=True)
    run.add_argument("--project-root-win", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--mission-id", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--index-dir", required=True)
    summary = sub.add_parser("show-summary")
    summary.add_argument("--index-dir", required=True)
    return top


def main() -> None:
    args = parser().parse_args()
    if args.command == "self-test":
        self_test()
    elif args.command == "verify-inputs":
        verify_inputs(args)
    elif args.command == "reconcile":
        reconcile(args)
    elif args.command == "validate":
        validate_outputs(Path(args.index_dir))
    elif args.command == "show-summary":
        show_summary(Path(args.index_dir))
    else:
        raise ValueError(args.command)


if __name__ == "__main__":
    main()
