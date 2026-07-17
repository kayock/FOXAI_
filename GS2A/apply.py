from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APPROVAL_PHRASE = "APPROVE GUARDED STREAMING PHASE 2 APPLY"

TARGET = "core/foxai_web.py"
BASELINE_SHA256 = "b94ac8e3b3a01b86cf34a509a64178e5efe047f38ac48e8ab5d08306ddf7ea48"
CANDIDATE_SHA256 = "e4d5811f14ae3ffb0b3f8b59369bee5c0a1218d19459f2decc875589540d04fb"
DIFF_SHA256 = "33da716cd9e6065a8d4b8eaec21253e15a75d4b1c7f39cf4a5a45aebf4662123"
PREVIEW_RECEIPT_SHA256 = "eb6299623c8c4a3877f946eae9536f998a4f965e7b25ae1cbbd43d40b60eac33"

LOCKED_HASHES = {
    "core/server.py":
        "9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07",
    "core/security_containment.py":
        "9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24",
    "core/engineer_agent.py":
        "f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19",
    "ui/main_window.py":
        "2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3",
    "tests/test_boundary_watch.py":
        "b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382",
    "Config/FoxAI.ini":
        "677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41",
    "Engine/llama-server.exe":
        "936cfb77f011911f879a5af715013eb12141115547c1f731114d8e9c20ebd89e",
}

PORTS_REQUIRED_CLOSED = {
    8765: "FOXAI WebUI",
    8080: "Chat Engine",
    8099: "Benchmark engine",
}

SCRIPT_RE = re.compile(
    r"<script[^>]*>(.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)
HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)


class ApplyError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "sha256": None, "size_bytes": 0}
    if not path.is_file():
        return {"exists": True, "sha256": None, "not_file": True}
    return {
        "exists": True,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / TARGET).is_file()
            and (candidate / "core/security_containment.py").is_file()
        ):
            return candidate
    raise ApplyError(
        r"FOXAI root not found. Extract the complete GS2A folder directly inside Z:\FOXAI."
    )


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def package_manifest_check(package_dir: Path) -> dict[str, Any]:
    manifest_path = package_dir / "sums.txt"
    if not manifest_path.is_file():
        raise ApplyError("Package manifest is missing.")

    checks = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = package_dir / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected_sha256": digest,
            "actual_sha256": actual,
            "ok": actual == digest,
        })

    if not checks or not all(item["ok"] for item in checks):
        raise ApplyError("Package manifest verification failed.")
    return {"passed": True, "files": checks}


def security_snapshot(root: Path) -> dict[str, Any]:
    result = {}
    security = root / "Logs/Security"
    if security.exists():
        for path in sorted(security.rglob("*")):
            if path.is_file():
                relative = str(path.relative_to(root)).replace("\\", "/")
                result[relative] = state(path)
    return result


def non_target_snapshot(root: Path) -> dict[str, Any]:
    result = {
        relative: state(root / relative)
        for relative in LOCKED_HASHES
    }
    result.update(security_snapshot(root))
    return result


def snapshot_changes(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[str]:
    return [
        key
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]


def verify_live_baselines(root: Path) -> dict[str, Any]:
    checks = [{
        "path": TARGET,
        "expected_sha256": BASELINE_SHA256,
        "actual_sha256": (
            sha256(root / TARGET)
            if (root / TARGET).is_file()
            else None
        ),
    }]
    checks[0]["ok"] = (
        checks[0]["actual_sha256"] == checks[0]["expected_sha256"]
    )

    for relative, expected in LOCKED_HASHES.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "ok": actual == expected,
        })

    if not all(item["ok"] for item in checks):
        raise ApplyError(
            "A locked live baseline changed. No apply occurred."
        )
    return {"passed": True, "files": checks}


def apply_unified_diff(source: str, diff_text: str) -> str:
    source_lines = source.splitlines(keepends=True)
    diff_lines = diff_text.splitlines(keepends=True)
    output: list[str] = []
    source_index = 0
    index = 0
    hunks = 0

    while index < len(diff_lines):
        line = diff_lines[index]
        if line.startswith(("--- ", "+++ ")):
            index += 1
            continue

        match = HUNK_RE.match(line.rstrip("\r\n"))
        if not match:
            index += 1
            continue

        hunks += 1
        old_start = int(match.group("old_start")) - 1
        if old_start < source_index:
            raise ApplyError("Diff hunks overlap or are out of order.")

        output.extend(source_lines[source_index:old_start])
        source_index = old_start
        index += 1

        while index < len(diff_lines):
            patch_line = diff_lines[index]
            if HUNK_RE.match(patch_line.rstrip("\r\n")):
                break
            if patch_line.startswith(("--- ", "+++ ")):
                break
            if patch_line.startswith("\\ No newline at end of file"):
                index += 1
                continue
            if not patch_line:
                index += 1
                continue

            marker = patch_line[0]
            content = patch_line[1:]
            if marker == " ":
                if (
                    source_index >= len(source_lines)
                    or source_lines[source_index] != content
                ):
                    raise ApplyError("Diff context did not match baseline.")
                output.append(content)
                source_index += 1
            elif marker == "-":
                if (
                    source_index >= len(source_lines)
                    or source_lines[source_index] != content
                ):
                    raise ApplyError("Diff removal did not match baseline.")
                source_index += 1
            elif marker == "+":
                output.append(content)
            else:
                raise ApplyError("Unsupported unified-diff line.")
            index += 1

    if hunks == 0:
        raise ApplyError("Approved diff contains no hunks.")

    output.extend(source_lines[source_index:])
    return "".join(output)


def verify_approved_preview(package_dir: Path) -> dict[str, Any]:
    receipt_path = package_dir / "approved/r.json"
    actual_receipt_hash = (
        sha256(receipt_path)
        if receipt_path.is_file()
        else None
    )
    if actual_receipt_hash != PREVIEW_RECEIPT_SHA256:
        raise ApplyError("Approved preview receipt hash changed.")

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected_checks = {
        "candidate_python_compile",
        "all_embedded_javascript_node_check",
        "browser_fragmented_ndjson_harness",
        "guard_before_exposure_helper_harness",
        "verified_nonstreaming_route_byte_identical",
        "boundary_watch_5_of_5",
        "raw_tokens_not_exposed_by_candidate",
        "final_full_answer_guarded_before_archive",
        "engineer_commands_use_nonstreaming_fallback",
        "cancel_path_does_not_commit_partial_turn",
        "creative_profile_evidence_updated",
    }
    receipt_checks = {
        "state": receipt.get("state") == "exact_preview_ready",
        "verified": receipt.get("verified") is True,
        "live_files_unmodified":
            receipt.get("live_files_modified") is False,
        "candidate_created": receipt.get("candidate_created") is True,
        "apply_capability_absent":
            receipt.get("apply_capability_present") is False,
        "one_file_scope":
            receipt.get("changed_files") == [TARGET],
        "no_deletes":
            receipt.get("delete_operations") == [],
        "baseline_hash":
            receipt.get("baseline_sha256") == BASELINE_SHA256,
        "candidate_hash":
            receipt.get("candidate_sha256") == CANDIDATE_SHA256,
        "diff_hash":
            receipt.get("diff_sha256") == DIFF_SHA256,
        "all_expected_checks_present_and_true":
            expected_checks.issubset(set((receipt.get("checks") or {}).keys()))
            and all(
                (receipt.get("checks") or {}).get(key) is True
                for key in expected_checks
            ),
    }
    if not all(receipt_checks.values()):
        raise ApplyError("Approved preview receipt is incomplete.")
    return {
        "passed": True,
        "receipt_sha256": actual_receipt_hash,
        "checks": receipt_checks,
    }


def verify_exact_scope(package_dir: Path) -> dict[str, Any]:
    baseline_path = package_dir / "approved/base.py"
    candidate_path = package_dir / "payload/foxai_web.py"
    diff_path = package_dir / "payload/change.diff"

    checks = {
        "baseline_sha256": sha256(baseline_path) == BASELINE_SHA256,
        "candidate_sha256": sha256(candidate_path) == CANDIDATE_SHA256,
        "diff_sha256": sha256(diff_path) == DIFF_SHA256,
    }
    if not all(checks.values()):
        raise ApplyError("Bundled baseline, candidate, or diff hash changed.")

    baseline = baseline_path.read_text(encoding="utf-8")
    candidate = candidate_path.read_text(encoding="utf-8")
    diff_text = diff_path.read_text(encoding="utf-8")
    reconstructed = apply_unified_diff(baseline, diff_text)
    checks["diff_reconstructs_candidate"] = reconstructed == candidate
    if not checks["diff_reconstructs_candidate"]:
        raise ApplyError(
            "Approved diff did not reconstruct the exact candidate."
        )
    return {"passed": True, "checks": checks}


def extract_scripts(source: str) -> list[str]:
    scripts = SCRIPT_RE.findall(source)
    if not scripts:
        raise ApplyError("No embedded JavaScript was found.")
    return scripts


def node_check(
    source: str,
    output: Path,
    label: str,
) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        raise ApplyError("Node.js was not found.")

    output.mkdir(parents=True, exist_ok=True)
    results = []
    for index, script in enumerate(extract_scripts(source), 1):
        target = output / f"{label}_{index:03d}.js"
        target.write_text(script, encoding="utf-8", newline="\n")
        completed = subprocess.run(
            [node, "--check", str(target)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        results.append({
            "file": target.name,
            "sha256": sha256(target),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "passed": completed.returncode == 0,
        })

    if any(item["passed"] is not True for item in results):
        raise ApplyError(f"{label} JavaScript failed node --check.")
    return {
        "passed": True,
        "javascript_blocks": len(results),
        "results": results,
    }


def helper_harness(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    helper_nodes = []
    for item in tree.body:
        if isinstance(item, ast.Assign):
            if any(
                isinstance(target, ast.Name)
                and target.id == "_GUARDED_STREAM_BOUNDARY"
                for target in item.targets
            ):
                helper_nodes.append(item)
        elif (
            isinstance(item, ast.FunctionDef)
            and item.name in {
                "guarded_stream_units",
                "guarded_stream_piece",
            }
        ):
            helper_nodes.append(item)

    namespace = {
        "re": re,
        "guard_model_action_claims": lambda value: {
            "text": (
                "[UNVERIFIED ACTION CLAIM]\n" + value
                if re.search(
                    r"(?i)\bI\s+(?:have\s+)?"
                    r"(?:successfully\s+)?deleted\b",
                    value,
                )
                else value
            ),
            "flagged": bool(
                re.search(
                    r"(?i)\bI\s+(?:have\s+)?"
                    r"(?:successfully\s+)?deleted\b",
                    value,
                )
            ),
        },
    }
    exec(
        compile(
            ast.Module(body=helper_nodes, type_ignores=[]),
            "guarded_stream_helpers",
            "exec",
        ),
        namespace,
    )

    units, tail = namespace["guarded_stream_units"](
        "First sentence. I have successfully deleted the file. Tail",
        final=False,
    )
    guarded = [
        namespace["guarded_stream_piece"](unit)
        for unit in units
    ]
    final_units, final_tail = namespace["guarded_stream_units"](
        tail,
        final=True,
    )
    passed = (
        units == [
            "First sentence. ",
            "I have successfully deleted the file. ",
        ]
        and tail == "Tail"
        and guarded[0]["flagged"] is False
        and guarded[1]["flagged"] is True
        and guarded[1]["text"].startswith(
            "[UNVERIFIED ACTION CLAIM]"
        )
        and final_units == ["Tail"]
        and final_tail == ""
    )
    if not passed:
        raise ApplyError("Guard-before-exposure helper harness failed.")
    return {
        "passed": True,
        "complete_units": units,
        "retained_tail": tail,
        "claim_guard_triggered_before_exposure":
            guarded[1]["flagged"],
    }


def browser_harness(
    package_dir: Path,
    output: Path,
) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        raise ApplyError("Node.js was not found.")
    output.mkdir(parents=True, exist_ok=True)

    source = package_dir / "approved/browser.js"
    target = output / "browser.js"
    shutil.copy2(source, target)
    completed = subprocess.run(
        [node, str(target)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    result = {
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "sha256": sha256(target),
    }
    if result["passed"] is not True:
        raise ApplyError("Fragmented NDJSON browser harness failed.")
    return result


def chat_send_segment(source: str) -> str:
    start = source.index("        if path=='/api/chat/send':\n")
    end = source.index(
        "        self.send_response(404); self.end_headers()",
        start,
    )
    return source[start:end]


def nonstreaming_fallback_check(
    baseline: str,
    candidate: str,
) -> dict[str, Any]:
    baseline_hash = hashlib.sha256(
        chat_send_segment(baseline).encode("utf-8")
    ).hexdigest()
    candidate_hash = hashlib.sha256(
        chat_send_segment(candidate).encode("utf-8")
    ).hexdigest()
    if baseline_hash != candidate_hash:
        raise ApplyError(
            "Verified non-streaming fallback route changed."
        )
    return {
        "passed": True,
        "baseline_segment_sha256": baseline_hash,
        "candidate_segment_sha256": candidate_hash,
        "byte_identical": True,
    }


def static_contract_check(source: str) -> dict[str, Any]:
    checks = {
        "helper_markers":
            "# GUARDED_STREAMING_PHASE2_HELPERS_START" in source
            and "# GUARDED_STREAMING_PHASE2_HELPERS_END" in source,
        "browser_markers":
            "/* GUARDED_STREAMING_PHASE2_BROWSER_START */" in source
            and "/* GUARDED_STREAMING_PHASE2_BROWSER_END */" in source,
        "route_markers":
            "# GUARDED_STREAMING_PHASE2_ROUTE_START" in source
            and "# GUARDED_STREAMING_PHASE2_ROUTE_END" in source,
        "stream_endpoint": "/api/chat/stream" in source,
        "cancel_button": "Cancel Generation" in source,
        "first_guarded_chunk_timing":
            "first_guarded_chunk_ms" in source,
        "creative_evidence_label":
            "BRAINSTORMING SUPPORTED • LONG-FORM PENDING"
            in source,
        "final_guard_before_archive":
            "claim_guard=guard_model_action_claims(raw_ans)"
            in source,
    }
    if not all(checks.values()):
        raise ApplyError("Guarded streaming static contract is incomplete.")
    return {"passed": True, "checks": checks}


def run_boundary_watch(root: Path) -> dict[str, Any]:
    code = (
        "import sys,unittest;"
        f"sys.path.insert(0,{str(root)!r});"
        "suite=unittest.defaultTestLoader.loadTestsFromName("
        "'tests.test_boundary_watch');"
        "result=unittest.TextTestRunner(verbosity=2).run(suite);"
        "raise SystemExit(0 if result.wasSuccessful() else 1)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    result = {
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "expected_tests": 5,
    }
    combined = completed.stdout + completed.stderr
    result["five_tests_observed"] = (
        "Ran 5 tests" in combined
        and "OK" in combined
    )
    if not result["passed"] or not result["five_tests_observed"]:
        raise ApplyError("Boundary Watch 5/5 failed.")
    return result


def source_verification(
    root: Path,
    package_dir: Path,
    source: str,
    output: Path,
    label: str,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    baseline = (
        package_dir / "approved/base.py"
    ).read_text(encoding="utf-8")

    compile(source, f"{label}_core_foxai_web.py", "exec")
    javascript = node_check(
        source,
        output / "js",
        label,
    )
    helper = helper_harness(source)
    browser = browser_harness(
        package_dir,
        output / "browser",
    )
    fallback = nonstreaming_fallback_check(
        baseline,
        source,
    )
    static_contract = static_contract_check(source)
    boundary = run_boundary_watch(root)

    result = {
        "passed": True,
        "python_compile": True,
        "javascript": javascript,
        "helper_harness": helper,
        "browser_harness": browser,
        "nonstreaming_fallback": fallback,
        "static_contract": static_contract,
        "boundary_watch": boundary,
    }
    (output / "result.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    return result


def copy_with_fsync(source: Path, target: Path) -> None:
    data = source.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def verified_backup(
    root: Path,
    timestamp: str,
) -> tuple[Path, dict[str, Any]]:
    backup_root = (
        root
        / "Backups/SecurityMilestone"
        / f"GS2_{timestamp}"
        / "core"
    )
    backup_root.mkdir(parents=True, exist_ok=False)
    backup_path = backup_root / "foxai_web.py"
    shutil.copy2(root / TARGET, backup_path)
    actual = sha256(backup_path)
    if actual != BASELINE_SHA256:
        raise ApplyError("Backup verification failed.")
    return backup_root.parent, {
        "verified": True,
        "path": str(backup_path),
        "expected_sha256": BASELINE_SHA256,
        "actual_sha256": actual,
    }


def install_candidate(
    root: Path,
    package_dir: Path,
) -> None:
    source = package_dir / "payload/foxai_web.py"
    stage = (
        root
        / "core"
        / f".foxai_web.py.gs2.{os.getpid()}.new"
    )
    try:
        copy_with_fsync(source, stage)
        if sha256(stage) != CANDIDATE_SHA256:
            raise ApplyError("Staged candidate hash failed.")
        os.replace(stage, root / TARGET)
    finally:
        try:
            stage.unlink(missing_ok=True)
        except Exception:
            pass


def rollback(
    root: Path,
    backup: dict[str, Any],
) -> dict[str, Any]:
    result = {
        "attempted": True,
        "succeeded": False,
        "final_sha256": None,
        "boundary_watch": None,
        "failure": None,
    }
    stage = (
        root
        / "core"
        / f".foxai_web.py.gs2.rollback.{os.getpid()}"
    )
    try:
        backup_path = Path(backup["path"])
        copy_with_fsync(backup_path, stage)
        if sha256(stage) != BASELINE_SHA256:
            raise ApplyError("Rollback stage hash failed.")
        os.replace(stage, root / TARGET)
        result["final_sha256"] = sha256(root / TARGET)
        if result["final_sha256"] != BASELINE_SHA256:
            raise ApplyError("Rollback live hash failed.")
        compile(
            (root / TARGET).read_text(encoding="utf-8"),
            str(root / TARGET),
            "exec",
        )
        result["boundary_watch"] = run_boundary_watch(root)
        result["succeeded"] = True
    except Exception as exc:
        result["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        try:
            stage.unlink(missing_ok=True)
        except Exception:
            pass
    return result


def write_report(
    output: Path,
    receipt: dict[str, Any],
) -> None:
    report = [
        "# FOXAI Guarded Streaming Phase 2 — Transactional Apply",
        "",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Operator approved: **{receipt['operator_approved']}**",
        f"- Changed files: **{receipt['changed_files']}**",
        f"- Delete operations: **{receipt['delete_operations']}**",
        f"- Rollback performed: **{receipt['rollback_performed']}**",
        f"- Final live SHA-256: `{receipt.get('final_live_sha256')}`",
        f"- Failure: **{receipt.get('failure')}**",
        "",
        "Only `core/foxai_web.py` is an allowed live target.",
        "",
        "Success requires `State: applied_verified` and `Verified: True`.",
    ]
    (output / "report.md").write_text(
        "\n".join(report),
        encoding="utf-8",
    )


def checkpoint(
    output: Path,
    receipt: dict[str, Any],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "receipt.json").write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )


def zip_output(output: Path) -> Path:
    target = output.with_suffix(".zip")
    target.unlink(missing_ok=True)
    with zipfile.ZipFile(
        target,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for file in sorted(output.rglob("*")):
            if file.is_file():
                archive.write(
                    file,
                    arcname=f"{output.name}/{file.relative_to(output)}",
                )
    return target


def main() -> int:
    package_dir = Path(__file__).resolve().parent
    root = find_root(package_dir)
    created = datetime.now(timezone.utc)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    output = package_dir / f"GS2_{stamp}"
    output.mkdir(parents=True, exist_ok=False)

    receipt: dict[str, Any] = {
        "action": "guarded_streaming_phase2_transactional_apply",
        "created": created.isoformat(),
        "root": str(root),
        "state": "running",
        "verified": False,
        "operator_approved": False,
        "approval_phrase_required": APPROVAL_PHRASE,
        "allowed_target": TARGET,
        "changed_files": [],
        "delete_operations": [],
        "rollback_performed": False,
        "rollback": None,
        "live_files_modified": False,
        "backup": None,
        "final_live_sha256": (
            sha256(root / TARGET)
            if (root / TARGET).is_file()
            else None
        ),
        "checks": {},
        "failure": None,
    }
    checkpoint(output, receipt)

    before_non_target = non_target_snapshot(root)
    original_target = state(root / TARGET)
    candidate_installed = False
    backup_info = None

    try:
        receipt["checks"]["package_manifest"] = (
            package_manifest_check(package_dir)
        )
        checkpoint(output, receipt)

        active_ports = [
            {"port": port, "label": label}
            for port, label in PORTS_REQUIRED_CLOSED.items()
            if port_open(port)
        ]
        if active_ports:
            raise ApplyError(
                "Close FOXAI WebUI, Chat Engine, and benchmark servers "
                f"before applying: {active_ports}"
            )
        receipt["checks"]["ports_closed"] = {
            "passed": True,
            "ports": PORTS_REQUIRED_CLOSED,
        }

        receipt["checks"]["live_baselines"] = (
            verify_live_baselines(root)
        )
        receipt["checks"]["approved_preview"] = (
            verify_approved_preview(package_dir)
        )
        receipt["checks"]["exact_scope"] = (
            verify_exact_scope(package_dir)
        )

        candidate_source = (
            package_dir / "payload/foxai_web.py"
        ).read_text(encoding="utf-8")
        receipt["checks"]["preflight"] = source_verification(
            root,
            package_dir,
            candidate_source,
            output / "pre",
            "candidate",
        )
        checkpoint(output, receipt)

        print()
        print("=" * 72)
        print("FOXAI GUARDED STREAMING PHASE 2")
        print("TRANSACTIONAL APPLY")
        print("=" * 72)
        print()
        print("Preflight verified.")
        print("Allowed live target:", TARGET)
        print("Delete operations: none")
        print("Verified backup and automatic rollback are mandatory.")
        print()
        print("Enter the exact approval phrase:")
        print(APPROVAL_PHRASE)
        print()
        entered = input("> ").strip()

        if entered != APPROVAL_PHRASE:
            receipt.update({
                "state": "stopped_not_approved",
                "verified": True,
                "operator_approved": False,
                "live_files_modified": False,
                "final_live_sha256": sha256(root / TARGET),
            })
            checkpoint(output, receipt)
        else:
            receipt["operator_approved"] = True
            backup_root, backup_info = verified_backup(root, stamp)
            receipt["backup"] = {
                **backup_info,
                "root": str(backup_root),
            }
            checkpoint(output, receipt)

            install_candidate(root, package_dir)
            candidate_installed = True
            receipt["changed_files"] = [TARGET]
            receipt["live_files_modified"] = True
            receipt["final_live_sha256"] = sha256(root / TARGET)
            checkpoint(output, receipt)

            if receipt["final_live_sha256"] != CANDIDATE_SHA256:
                raise ApplyError("Installed candidate hash failed.")

            live_source = (
                root / TARGET
            ).read_text(encoding="utf-8")
            receipt["checks"]["postflight"] = source_verification(
                root,
                package_dir,
                live_source,
                output / "post",
                "live",
            )

            final_non_target = non_target_snapshot(root)
            non_target_changes = snapshot_changes(
                before_non_target,
                final_non_target,
            )
            receipt["checks"]["non_target_immutability"] = {
                "passed": not non_target_changes,
                "changed": non_target_changes,
            }
            if non_target_changes:
                raise ApplyError(
                    "A protected non-target or security log changed: "
                    + repr(non_target_changes)
                )

            receipt.update({
                "state": "applied_verified",
                "verified": True,
                "changed_files": [TARGET],
                "delete_operations": [],
                "rollback_performed": False,
                "live_files_modified": True,
                "final_live_sha256": sha256(root / TARGET),
            })
            checkpoint(output, receipt)

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

        if candidate_installed and backup_info is not None:
            rollback_result = rollback(root, backup_info)
            receipt["rollback_performed"] = True
            receipt["rollback"] = rollback_result
            if rollback_result["succeeded"]:
                receipt.update({
                    "state": "rolled_back_verified",
                    "verified": True,
                    "changed_files": [],
                    "live_files_modified": False,
                    "final_live_sha256": sha256(root / TARGET),
                })
            else:
                receipt.update({
                    "state": "rollback_failed",
                    "verified": False,
                    "final_live_sha256": (
                        sha256(root / TARGET)
                        if (root / TARGET).is_file()
                        else None
                    ),
                })
        else:
            final_target = state(root / TARGET)
            final_non_target = non_target_snapshot(root)
            protected_changes = snapshot_changes(
                before_non_target,
                final_non_target,
            )
            target_unchanged = final_target == original_target
            receipt.update({
                "state": "stopped_fail_closed",
                "verified": (
                    target_unchanged
                    and not protected_changes
                ),
                "changed_files": [],
                "live_files_modified": not target_unchanged,
                "final_live_sha256": final_target.get("sha256"),
            })
            receipt["checks"]["fail_closed_final_state"] = {
                "target_unchanged": target_unchanged,
                "protected_non_targets_unchanged":
                    not protected_changes,
                "protected_changes": protected_changes,
            }
        checkpoint(output, receipt)

    write_report(output, receipt)
    checkpoint(output, receipt)
    output_zip = zip_output(output)

    print()
    print("=" * 72)
    print("FOXAI GUARDED STREAMING PHASE 2")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Operator approved:", receipt["operator_approved"])
    print("Changed files:", receipt["changed_files"])
    print("Delete operations:", receipt["delete_operations"])
    print("Rollback performed:", receipt["rollback_performed"])
    print("Final live SHA-256:", receipt["final_live_sha256"])
    print("Output ZIP:", output_zip)
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    print()
    print("Nothing is considered installed unless the receipt says:")
    print("  State: applied_verified")
    print("  Verified: True")
    print()
    input("Press Enter to close...")

    return 0 if receipt["state"] == "applied_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
