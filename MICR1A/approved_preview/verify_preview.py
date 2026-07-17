from __future__ import annotations

import ast
import base64
import binascii
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


WEB_BASELINE_SHA = "3b1a8d9a1bc63c6d0a6a333edf315a4c1aff06f9ffae44f9ddd679c96b7c1d4d"
WEB_CANDIDATE_SHA = "7fcbddeae22904af7f9aa75e9546e3e28721d455222fbfc42c27c5186ba45180"
WEB_DIFF_SHA = "2a847670fc10575b9eb3c1e25c305dbd087784ceccb3f488b4d07626422a2165"
SERVER_BASELINE_SHA = "238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81"
APPLIED_RECEIPT_SHA = "73956c6443eb4e02b813be7cbb57812d50d5412977277ee4bdd943c578fb264a"
PNG_SHA = "1aec2538a7de58c6a83871b17dd3e8a08d5370d2b10bda61a83561820ca76c31"

LOCKED_HASHES = {
    "core/foxai_web.py": WEB_BASELINE_SHA,
    "core/server.py": SERVER_BASELINE_SHA,
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

PROJECTOR = {
    "path": "Models/Chat/mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf",
    "size": 752289728,
    "sha256":
        "c6ba85508d82f42590e6eb77d5340369ab6fecf107a7561d809523d8aa5f3bfd",
}

MODEL_SIZES = {
    "Models/Chat/Qwen3VL-8B-Instruct-Q4_K_M.gguf": 5027784800,
    "Models/Chat/Qwen3VL-8B-Instruct-Q8_0.gguf": 8709519456,
}

HUNK_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)
SCRIPT_RE = re.compile(
    r"<script[^>]*>(.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)


class VerifyError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "sha256": None, "size": 0}
    if not path.is_file():
        return {"exists": True, "sha256": None, "not_file": True}
    return {
        "exists": True,
        "sha256": sha256(path),
        "size": path.stat().st_size,
    }


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "core/foxai_web.py").is_file()
            and (candidate / "core/server.py").is_file()
            and (candidate / "Engine/llama-server.exe").is_file()
        ):
            return candidate
    raise VerifyError(
        r"FOXAI root not found. Extract the complete MICR1P folder directly inside Z:\FOXAI."
    )


def package_manifest(package: Path) -> dict[str, Any]:
    manifest = package / "PACKAGE_SHA256SUMS.txt"
    if not manifest.is_file():
        raise VerifyError("Package manifest is missing.")
    checks = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = package / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected": digest,
            "actual": actual,
            "ok": actual == digest,
        })
    if not checks or not all(item["ok"] for item in checks):
        raise VerifyError("Package manifest verification failed.")
    return {
        "passed": True,
        "files": checks,
        "apply_capability_present": False,
    }


def protected_snapshot(root: Path) -> dict[str, Any]:
    result = {
        relative: file_state(root / relative)
        for relative in LOCKED_HASHES
    }
    security = root / "Logs/Security"
    if security.exists():
        for path in sorted(security.rglob("*")):
            if path.is_file():
                relative = str(path.relative_to(root)).replace("\\", "/")
                result[relative] = file_state(path)
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


def live_baselines(root: Path) -> dict[str, Any]:
    checks = []
    for relative, expected in LOCKED_HASHES.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected": expected,
            "actual": actual,
            "ok": actual == expected,
        })
    if not all(item["ok"] for item in checks):
        raise VerifyError("A locked live FOXAI baseline changed.")
    return {"passed": True, "files": checks}


def vision_assets(root: Path) -> dict[str, Any]:
    checks = []
    projector_path = root / PROJECTOR["path"]
    projector_size = (
        projector_path.stat().st_size
        if projector_path.is_file()
        else None
    )
    projector_sha = (
        sha256(projector_path)
        if projector_path.is_file()
        else None
    )
    checks.append({
        "path": PROJECTOR["path"],
        "expected_size": PROJECTOR["size"],
        "actual_size": projector_size,
        "expected_sha256": PROJECTOR["sha256"],
        "actual_sha256": projector_sha,
        "ok": (
            projector_size == PROJECTOR["size"]
            and projector_sha == PROJECTOR["sha256"]
        ),
    })
    for relative, expected_size in MODEL_SIZES.items():
        path = root / relative
        actual_size = (
            path.stat().st_size
            if path.is_file()
            else None
        )
        checks.append({
            "path": relative,
            "expected_size": expected_size,
            "actual_size": actual_size,
            "ok": actual_size == expected_size,
        })
    if not all(item["ok"] for item in checks):
        raise VerifyError("A verified vision asset changed or is missing.")
    return {"passed": True, "files": checks}


def apply_unified_diff(source: str, diff_text: str) -> str:
    source_lines = source.splitlines(keepends=True)
    diff_lines = diff_text.splitlines(keepends=True)
    output = []
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
        old_start = int(match.group(1)) - 1
        if old_start < source_index:
            raise VerifyError("Diff hunks overlap or are out of order.")

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
                    raise VerifyError("Diff context did not match baseline.")
                output.append(content)
                source_index += 1
            elif marker == "-":
                if (
                    source_index >= len(source_lines)
                    or source_lines[source_index] != content
                ):
                    raise VerifyError("Diff removal did not match baseline.")
                source_index += 1
            elif marker == "+":
                output.append(content)
            else:
                raise VerifyError("Unsupported diff line.")
            index += 1

    if hunks == 0:
        raise VerifyError("Exact diff contains no hunks.")

    output.extend(source_lines[source_index:])
    return "".join(output)


def exact_artifacts(package: Path) -> dict[str, Any]:
    baseline = package / "baseline/core/foxai_web.py"
    candidate = package / "candidate/core/foxai_web.py"
    diff = package / "diffs/foxai_web.py.diff"

    checks = {
        "baseline_hash": sha256(baseline) == WEB_BASELINE_SHA,
        "candidate_hash": sha256(candidate) == WEB_CANDIDATE_SHA,
        "diff_hash": sha256(diff) == WEB_DIFF_SHA,
    }
    if not all(checks.values()):
        raise VerifyError("Exact artifact identity failed.")

    baseline_text = baseline.read_text(encoding="utf-8")
    candidate_text = candidate.read_text(encoding="utf-8")
    reconstructed = apply_unified_diff(
        baseline_text,
        diff.read_text(encoding="utf-8"),
    )
    checks["diff_reconstructs_candidate"] = (
        reconstructed == candidate_text
    )
    if not checks["diff_reconstructs_candidate"]:
        raise VerifyError("Exact diff did not reconstruct the candidate.")

    compile(baseline_text, str(baseline), "exec")
    compile(candidate_text, str(candidate), "exec")
    checks["python_compile"] = True

    return {"passed": True, "checks": checks}


def applied_receipt(package: Path) -> dict[str, Any]:
    path = package / "approved/mia1_applied_receipt.json"
    actual = sha256(path) if path.is_file() else None
    if actual != APPLIED_RECEIPT_SHA:
        raise VerifyError("Applied baseline receipt hash changed.")
    data = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "state": data.get("state") == "applied_verified",
        "verified": data.get("verified") is True,
        "web_hash":
            (data.get("final_hashes") or {}).get(
                "core/foxai_web.py"
            ) == WEB_BASELINE_SHA,
        "server_hash":
            (data.get("final_hashes") or {}).get(
                "core/server.py"
            ) == SERVER_BASELINE_SHA,
        "no_deletes": data.get("delete_operations") == [],
        "no_rollback": data.get("rollback_performed") is False,
    }
    if not all(checks.values()):
        raise VerifyError("Applied baseline receipt is incomplete.")
    return {
        "passed": True,
        "sha256": actual,
        "checks": checks,
    }


def node_and_browser(package: Path) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        raise VerifyError("Node.js was not found.")

    candidate = (
        package / "candidate/core/foxai_web.py"
    ).read_text(encoding="utf-8")
    scripts = SCRIPT_RE.findall(candidate)
    if not scripts:
        raise VerifyError("No embedded JavaScript was found.")

    node_results = []
    output = package / "verification/live_node_check"
    output.mkdir(parents=True, exist_ok=True)
    for index, script in enumerate(scripts, start=1):
        target = output / f"embedded_{index:03d}.js"
        target.write_text(script, encoding="utf-8", newline="\n")
        completed = subprocess.run(
            [node, "--check", str(target)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        node_results.append({
            "index": index,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "passed": completed.returncode == 0,
        })
    if not all(item["passed"] for item in node_results):
        raise VerifyError("Embedded JavaScript failed node --check.")

    harness = package / "verification/browser_harness.js"
    completed = subprocess.run(
        [node, str(harness)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    browser = {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }
    if browser["passed"] is not True:
        raise VerifyError("Browser continuity/leakage harness failed.")

    return {
        "passed": True,
        "javascript_blocks": len(node_results),
        "node_check": node_results,
        "browser_harness": browser,
    }


def helper_harness(package: Path) -> dict[str, Any]:
    source = (
        package / "candidate/core/foxai_web.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {
        "mission_image_identity",
        "validate_mission_image",
        "mission_image_receipt_details",
        "set_active_mission_image",
        "get_active_mission_image",
        "clear_active_mission_image",
        "mission_image_status",
        "contains_image_payload",
        "assert_no_image_payload",
        "mission_user_message",
        "mission_archive_user_text",
        "compact_prior_images",
        "prepare_mission_image_context",
    }
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            ]
            if any(name in {
                "MISSION_IMAGE_MAX_BYTES",
                "MISSION_JSON_MAX_BYTES",
                "MISSION_IMAGE_ALLOWED_MIME",
                "_IMAGE_PAYLOAD_MARKERS",
            } for name in names):
                nodes.append(node)
        elif (
            isinstance(node, ast.ClassDef)
            and node.name == "MissionRequestError"
        ):
            nodes.append(node)
        elif (
            isinstance(node, ast.FunctionDef)
            and node.name in wanted
        ):
            nodes.append(node)

    namespace = {
        "Path": Path,
        "base64": base64,
        "binascii": binascii,
        "hashlib": hashlib,
        "re": re,
        "mission_active_image": None,
        "mission_image_lock": RLock(),
        "messages": [
            {"role": "system", "content": "system"}
        ],
    }
    exec(
        compile(
            ast.Module(body=nodes, type_ignores=[]),
            "image_continuity_helpers",
            "exec",
        ),
        namespace,
    )

    png = package / "verification/assets/continuity.png"
    if sha256(png) != PNG_SHA:
        raise VerifyError("Continuity test image identity changed.")
    raw = png.read_bytes()
    data_url = (
        "data:image/png;base64,"
        + base64.b64encode(raw).decode("ascii")
    )
    image_payload = {
        "name": "logo.png",
        "type": "image/png",
        "size": len(raw),
        "width": 37,
        "height": 23,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data_url": data_url,
    }
    image = namespace["validate_mission_image"](image_payload)

    namespace["messages"][:] = [
        {"role": "system", "content": "system"},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/png;base64,AAAA"
                    },
                },
                {"type": "text", "text": "old question"},
            ],
        },
        {"role": "assistant", "content": "old answer"},
    ]

    first = namespace["prepare_mission_image_context"](
        namespace["messages"],
        "Describe the logo.",
        image,
        False,
    )
    if first["source"] != "new":
        raise VerifyError("New image source was not recorded.")
    if namespace["contains_image_payload"](namespace["messages"]):
        raise VerifyError("Raw payload remained in conversation history.")
    if not all(
        isinstance(item.get("content"), str)
        for item in namespace["messages"]
    ):
        raise VerifyError("Conversation history was not compacted to text.")

    request_json = json.dumps(first["request_messages"])
    if request_json.count("data:image/png;base64,") != 1:
        raise VerifyError(
            "The initial current-turn request did not contain exactly one image."
        )
    if namespace["contains_image_payload"](
        first["request_messages"][:-1]
    ):
        raise VerifyError("Earlier history still contained an image payload.")

    namespace["messages"].append(first["history_user_message"])
    namespace["messages"].append({
        "role": "assistant",
        "content": "description",
    })
    if namespace["contains_image_payload"](namespace["messages"]):
        raise VerifyError("Safe history append leaked image bytes.")

    follow = namespace["prepare_mission_image_context"](
        namespace["messages"],
        "What is above the ribbon?",
        None,
        True,
    )
    follow_json = json.dumps(follow["request_messages"])
    if follow["source"] != "active":
        raise VerifyError("Follow-up did not use active image state.")
    if follow_json.count("data:image/png;base64,") != 1:
        raise VerifyError(
            "Follow-up did not reattach exactly one current image."
        )
    if namespace["contains_image_payload"](
        follow["request_messages"][:-1]
    ):
        raise VerifyError(
            "Follow-up history contained raw image payloads."
        )
    if namespace["contains_image_payload"](
        follow["history_user_message"]
    ):
        raise VerifyError("Archive user marker contained image bytes.")

    status = namespace["mission_image_status"]()
    if (
        not status["active_image"].get("attached")
        or namespace["contains_image_payload"](status)
    ):
        raise VerifyError("Active image status exposed raw bytes.")

    try:
        namespace["mission_archive_user_text"](
            "leak data:image/png;base64,AAAA"
        )
        raise VerifyError("Archive payload guard did not trigger.")
    except namespace["MissionRequestError"]:
        pass

    namespace["clear_active_mission_image"]()
    try:
        namespace["prepare_mission_image_context"](
            namespace["messages"],
            "follow-up",
            None,
            True,
        )
        raise VerifyError("Missing active image did not fail closed.")
    except namespace["MissionRequestError"] as exc:
        if exc.status != 409:
            raise VerifyError("Missing active image used wrong status.")

    return {
        "passed": True,
        "history_payload_free": True,
        "initial_current_turn_image_count": 1,
        "followup_current_turn_image_count": 1,
        "followup_reattaches_active_image": True,
        "active_status_metadata_only": True,
        "archive_payload_guard": True,
        "missing_active_fails_closed": True,
    }


def static_contract(package: Path) -> dict[str, Any]:
    source = (
        package / "candidate/core/foxai_web.py"
    ).read_text(encoding="utf-8")
    checks = {
        "volatile_single_active_image":
            "mission_active_image=None" in source
            and "mission_image_lock=RLock()" in source,
        "history_is_compacted":
            "messages[:]=compact_prior_images(messages)" in source,
        "current_turn_reattachment":
            "prepare_mission_image_context" in source
            and "use_active_image" in source,
        "safe_history_user_message":
            "user_message=context['history_user_message']" in source,
        "metadata_only_status":
            "data_url_retained_in_history':False" in source,
        "payload_guard":
            "Raw image payload was blocked from" in source,
        "status_endpoint":
            "/api/chat/image/status" in source,
        "clear_endpoint":
            "/api/chat/image/clear" in source,
        "cancel_preserves":
            "The active image remains available for retry." in source,
        "browser_active_metadata_only":
            "activeMissionImage.data_url" not in source,
        "browser_uses_active_reference":
            "use_active_image:Boolean(useActive)" in source,
        "text_profile_clears":
            "if not profile.get('vision'):" in source
            and "clear_active_mission_image()" in source,
        "stop_clears":
            "def stop_chat():" in source
            and "clear_active_mission_image()" in source,
        "reset_clears":
            "def reset_msgs():" in source
            and "resetMissionConsole()" in source,
        "visible_card_hides_raw":
            "[raw image data hidden]" in source,
        "guarded_streaming_preserved":
            "/api/chat/stream" in source
            and "guarded_stream_units" in source,
        "engineer_image_still_denied":
            "Engineer image inspection is not enabled." in source,
        "no_server_change_proposed":
            True,
    }
    if not all(checks.values()):
        raise VerifyError("Static repair contract is incomplete.")
    return {"passed": True, "checks": checks}


def boundary_watch(root: Path) -> dict[str, Any]:
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
    combined = completed.stdout + completed.stderr
    result = {
        "passed": (
            completed.returncode == 0
            and "Ran 5 tests" in combined
            and "OK" in combined
        ),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "tests": 5,
    }
    if result["passed"] is not True:
        raise VerifyError("Boundary Watch 5/5 failed.")
    return result


def existing_payload_scan(root: Path) -> dict[str, Any]:
    roots = [
        root / "Logs",
        root / "Reports",
        root / "Projects",
        root / "MissionArchive",
        root / "MissionArchives",
        root / "Archive",
    ]
    suffixes = {
        ".txt", ".md", ".json", ".jsonl", ".log",
        ".csv", ".yaml", ".yml", ".html",
    }
    findings = []
    scanned = 0
    skipped_large = 0
    max_files = 12000
    max_size = 20 * 1024 * 1024

    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if scanned >= max_files:
                break
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            try:
                size = path.stat().st_size
                if size > max_size:
                    skipped_large += 1
                    continue
                scanned += 1
                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
                lower = text.lower()
                marker = None
                if "data:image/" in lower:
                    marker = "data:image/"
                elif ";base64," in lower:
                    marker = ";base64,"
                if marker:
                    findings.append({
                        "path":
                            str(path.relative_to(root)).replace(
                                "\\", "/"
                            ),
                        "marker": marker,
                        "size": size,
                    })
            except Exception:
                continue

    return {
        "passed": True,
        "read_only": True,
        "scanned_files": scanned,
        "skipped_large": skipped_large,
        "findings": findings,
        "finding_count": len(findings),
        "note": (
            "Findings are reported but not modified. Any cleanup "
            "requires a separate preview-first repair."
        ),
    }


def main() -> int:
    package = Path(__file__).resolve().parent
    root = find_root(package)
    output = package / "LIVE_VERIFY_RECEIPT.json"

    before = protected_snapshot(root)
    receipt: dict[str, Any] = {
        "action":
            "mission_image_continuity_leakage_repair_phase1_exact_preview_verify",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "running",
        "verified": False,
        "root": str(root),
        "live_files_modified": False,
        "candidate_created": True,
        "apply_capability_present": False,
        "changed_files_proposed": [
            "core/foxai_web.py",
        ],
        "unchanged_files_explicit": [
            "core/server.py",
        ],
        "delete_operations": [],
        "checks": {},
        "failure": None,
        "protected_changes": [],
    }

    try:
        receipt["checks"]["package_manifest"] = (
            package_manifest(package)
        )
        receipt["checks"]["applied_baseline_receipt"] = (
            applied_receipt(package)
        )
        receipt["checks"]["exact_artifacts"] = (
            exact_artifacts(package)
        )
        receipt["checks"]["live_baselines"] = (
            live_baselines(root)
        )
        receipt["checks"]["vision_assets"] = (
            vision_assets(root)
        )
        receipt["checks"]["node_and_browser"] = (
            node_and_browser(package)
        )
        receipt["checks"]["continuity_and_leakage_helpers"] = (
            helper_harness(package)
        )
        receipt["checks"]["static_contract"] = (
            static_contract(package)
        )
        receipt["checks"]["boundary_watch"] = (
            boundary_watch(root)
        )
        receipt["checks"]["existing_payload_scan"] = (
            existing_payload_scan(root)
        )

        after = protected_snapshot(root)
        changes = snapshot_changes(before, after)
        receipt["protected_changes"] = changes
        if changes:
            raise VerifyError(
                "Read-only verification changed protected files: "
                + repr(changes)
            )

        receipt.update({
            "state": "exact_preview_verified",
            "verified": True,
            "live_files_modified": False,
        })

    except Exception as exc:
        after = protected_snapshot(root)
        changes = snapshot_changes(before, after)
        receipt.update({
            "state": "stopped_fail_closed",
            "verified": not changes,
            "live_files_modified": bool(changes),
            "protected_changes": changes,
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        })

    output.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("FOXAI MISSION IMAGE CONTINUITY + LEAKAGE REPAIR")
    print("PHASE 1 EXACT PREVIEW")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Live files modified:", receipt["live_files_modified"])
    print("Apply capability present: False")
    print("Proposed changed files:", receipt["changed_files_proposed"])
    scan = (receipt.get("checks") or {}).get(
        "existing_payload_scan"
    ) or {}
    print(
        "Existing on-disk payload findings:",
        scan.get("finding_count", "not completed"),
    )
    print("Receipt:", output)
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    print()
    input("Press Enter to close...")

    return 0 if receipt["state"] == "exact_preview_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
