from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import phase3_verifier as verifier


APPROVAL_PHRASE = "APPLY MODEL PROFILE SELECTOR RUNTIME PHASE 3"

BASELINE_HASHES = {
    "core/foxai_web.py": "8b1ea52ac61a7d1dcf44a94cc64b6643ea0e74a6ca93ec734edb5f0f4d82e513",
    "core/server.py": "6d2b43616d6130469c057da070f8c4cf7ee3a965b563d1f704b0cc8ce6a49505",
    "core/security_containment.py": "9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24",
    "core/engineer_agent.py": "f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19",
    "ui/main_window.py": "2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3",
    "tests/test_boundary_watch.py": "b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382",
    "Config/FoxAI.ini": "677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41",
    "Engine/llama-server.exe": "936cfb77f011911f879a5af715013eb12141115547c1f731114d8e9c20ebd89e",
}

CANDIDATE_HASHES = {
    "core/foxai_web.py": "b94ac8e3b3a01b86cf34a509a64178e5efe047f38ac48e8ab5d08306ddf7ea48",
    "core/server.py": "9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07",
}

DIFF_HASHES = {
    "core/foxai_web.py": "565c21a8f3fd1589398586810bb2de7c0d4091228f93d25f7c89c07cf174b7a5",
    "core/server.py": "613d595f9495946b2775f6cadac31ee1e79a5a2ef7bd3b4a092acc299a3129ad",
}

APPROVED_ARTIFACT_HASHES = {
    "r.json":
        "ea989539a4b6bebfc465de4f015995c1497dd13c5ea310249cb0d588dbf082fb",
    "v.json":
        "8810b67f549f998bf95575b443456c6dbd7dde16b645165e94a8bb192eabaaf8",
    "p.md":
        "68d6af52ae6be15cd9c96de50ca33c96a674044548dc9b15fef22ee608cf25c7",
    "c.json":
        "74a3187775504d3ba33f4271e0a51e94d378950f735fed092b0cb8cc81e770bd",
}

TARGETS = ["core/server.py", "core/foxai_web.py"]
PORTS_REQUIRED_CLOSED = {
    8765: "FOXAI WebUI",
    8080: "Chat Engine",
    8099: "Benchmark engine",
}


class ApplyError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def package_manifest_check(package_dir: Path) -> dict[str, Any]:
    manifest_path = package_dir / "sums.txt"
    if not manifest_path.is_file():
        raise ApplyError("Package manifest is missing.")
    results = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = package_dir / relative
        actual = sha256(path) if path.is_file() else None
        results.append({
            "path": relative,
            "expected_sha256": digest,
            "actual_sha256": actual,
            "ok": actual == digest,
        })
    if not results or not all(item["ok"] for item in results):
        raise ApplyError("Package manifest verification failed.")
    return {"passed": True, "files": results}


def non_target_snapshot(root: Path) -> dict[str, Any]:
    result = {}
    for relative in BASELINE_HASHES:
        if relative not in TARGETS:
            result[relative] = state(root / relative)
    security = root / "Logs" / "Security"
    if security.exists():
        for path in sorted(security.rglob("*")):
            if path.is_file():
                relative = str(path.relative_to(root)).replace("\\", "/")
                result[relative] = state(path)
    return result


def snapshot_changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return [
        key for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]


def verify_baselines(root: Path) -> list[dict[str, Any]]:
    checks = []
    for relative, expected in BASELINE_HASHES.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "ok": actual == expected,
        })
    if not all(item["ok"] for item in checks):
        raise ApplyError("A locked live baseline changed. No apply occurred.")
    return checks


def verify_approved_preview(package_dir: Path) -> dict[str, Any]:
    preview_dir = package_dir / "approved_preview"
    hash_checks = []
    for name, expected in APPROVED_ARTIFACT_HASHES.items():
        path = preview_dir / name
        actual = sha256(path) if path.is_file() else None
        hash_checks.append({
            "path": name,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "ok": actual == expected,
        })
    if not all(item["ok"] for item in hash_checks):
        raise ApplyError("Approved preview artifact hash changed.")

    receipt = json.loads(
        (preview_dir / "r.json")
        .read_text(encoding="utf-8")
    )
    validation = json.loads(
        (preview_dir / "v.json")
        .read_text(encoding="utf-8")
    )
    contract = json.loads(
        (preview_dir / "c.json").read_text(encoding="utf-8")
    )

    receipt_checks = {
        "state": receipt.get("state") == "combined_exact_preview_ready",
        "verified": receipt.get("verified") is True,
        "apply_capability_absent":
            receipt.get("apply_capability_present") is False,
        "live_files_unmodified": receipt.get("live_files_modified") is False,
        "proposed_files_exact":
            receipt.get("proposed_files") == [
                "core/foxai_web.py", "core/server.py"
            ],
        "no_deletes": receipt.get("delete_operations") == [],
        "candidate_hashes": receipt.get("candidate_hashes") == CANDIDATE_HASHES,
        "diff_hashes": receipt.get("diff_hashes") == DIFF_HASHES,
        "all_checks_passed": all(
            item.get("ok") is True for item in receipt.get("checks", [])
        ),
    }
    if not all(receipt_checks.values()):
        raise ApplyError("Approved preview receipt is not fully verified.")

    validation_checks = {
        "proposed_files_exact":
            validation.get("proposed_files") == [
                "core/foxai_web.py", "core/server.py"
            ],
        "no_deletes": validation.get("delete_operations") == [],
        "profile_cards": validation.get("profile_cards") == 5,
        "raw_fallback":
            validation.get("raw_gguf_fallback_preserved") is True,
        "browser_flags_blocked":
            validation.get("browser_arbitrary_engine_flags_allowed") is False,
        "profile_mismatch_fails":
            validation.get("profile_model_mismatch_fails_closed") is True,
        "external_runtime_fails":
            validation.get(
                "unverified_external_profile_runtime_fails_closed"
            ) is True,
        "selection_only":
            validation.get("selection_only_until_explicit_start") is True,
        "boundary_watch":
            (validation.get("boundary_watch") or {}).get("passed") is True,
    }
    if not all(validation_checks.values()):
        raise ApplyError("Approved preview validation contract is incomplete.")

    contract_checks = {
        "proposed_files":
            contract.get("proposed_files") == [
                "core/foxai_web.py", "core/server.py"
            ],
        "no_deletes": contract.get("delete_operations") == [],
        "selection_only":
            (contract.get("operator_control") or {}).get(
                "selection_only"
            ) is True,
        "explicit_start":
            (contract.get("operator_control") or {}).get(
                "explicit_start_required"
            ) is True,
        "silent_switch_blocked":
            (contract.get("operator_control") or {}).get(
                "silent_auto_switch"
            ) is False,
    }
    if not all(contract_checks.values()):
        raise ApplyError("Approved patch contract is incomplete.")

    return {
        "hash_checks": hash_checks,
        "receipt_checks": receipt_checks,
        "validation_checks": validation_checks,
        "contract_checks": contract_checks,
    }


def verify_payload_and_diffs(
    package_dir: Path,
    root: Path,
) -> dict[str, Any]:
    candidate_web = package_dir / "payload/candidate/core/foxai_web.py"
    candidate_server = package_dir / "payload/candidate/core/server.py"
    web_diff = package_dir / "payload/diffs/core_foxai_web.py.diff"
    server_diff = package_dir / "payload/diffs/core_server.py.diff"

    paths = {
        "core/foxai_web.py": candidate_web,
        "core/server.py": candidate_server,
    }
    candidate_checks = []
    for relative, path in paths.items():
        actual = sha256(path)
        candidate_checks.append({
            "path": relative,
            "expected_sha256": CANDIDATE_HASHES[relative],
            "actual_sha256": actual,
            "ok": actual == CANDIDATE_HASHES[relative],
        })

    diff_paths = {
        "core/foxai_web.py": web_diff,
        "core/server.py": server_diff,
    }
    diff_checks = []
    for relative, path in diff_paths.items():
        actual = sha256(path)
        diff_checks.append({
            "path": relative + ".diff",
            "expected_sha256": DIFF_HASHES[relative],
            "actual_sha256": actual,
            "ok": actual == DIFF_HASHES[relative],
        })

    if not all(item["ok"] for item in candidate_checks + diff_checks):
        raise ApplyError("Candidate or diff payload hash changed.")

    live_web = (root / "core/foxai_web.py").read_text(encoding="utf-8")
    live_server = (root / "core/server.py").read_text(encoding="utf-8")
    candidate_web_source = candidate_web.read_text(encoding="utf-8")
    candidate_server_source = candidate_server.read_text(encoding="utf-8")

    expected_web_diff = verifier.expected_diff(
        live_web, candidate_web_source, "core/foxai_web.py"
    )
    expected_server_diff = verifier.expected_diff(
        live_server, candidate_server_source, "core/server.py"
    )
    if expected_web_diff != web_diff.read_text(encoding="utf-8"):
        raise ApplyError("WebUI exact diff does not reconstruct the candidate.")
    if expected_server_diff != server_diff.read_text(encoding="utf-8"):
        raise ApplyError("Server exact diff does not reconstruct the candidate.")

    return {
        "candidate_checks": candidate_checks,
        "diff_checks": diff_checks,
        "exact_diff_reconstruction": True,
        "candidate_web": candidate_web,
        "candidate_server": candidate_server,
        "candidate_web_source": candidate_web_source,
        "candidate_server_source": candidate_server_source,
    }


def candidate_preflight(
    root: Path,
    payload: dict[str, Any],
    output: Path,
    label: str,
) -> dict[str, Any]:
    live_web_source = (root / "core/foxai_web.py").read_text(encoding="utf-8")
    live_server_source = (root / "core/server.py").read_text(encoding="utf-8")
    candidate_web_source = payload["candidate_web_source"]
    candidate_server_source = payload["candidate_server_source"]

    compile(live_web_source, str(root / "core/foxai_web.py"), "exec")
    compile(live_server_source, str(root / "core/server.py"), "exec")
    compile(candidate_web_source, "candidate_core_foxai_web.py", "exec")
    compile(candidate_server_source, "candidate_core_server.py", "exec")

    baseline_js_dir = output / f"{label}_baseline_javascript"
    candidate_js_dir = output / f"{label}_candidate_javascript"
    js_harness_dir = output / f"{label}_javascript_harness"
    backend_harness_dir = output / f"{label}_backend_harness"
    server_harness_dir = output / f"{label}_server_harness"

    for directory in (
        baseline_js_dir,
        candidate_js_dir,
        js_harness_dir,
        backend_harness_dir,
        server_harness_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    baseline_js = verifier.node_check(
        verifier.extract_scripts(live_web_source),
        baseline_js_dir,
        f"{label}_baseline",
    )
    candidate_scripts = verifier.extract_scripts(candidate_web_source)
    candidate_js = verifier.node_check(
        candidate_scripts,
        candidate_js_dir,
        f"{label}_candidate",
    )
    js_harness = verifier.run_js_behavior_harness(
        candidate_scripts,
        js_harness_dir,
    )
    backend_harness = verifier.run_web_backend_registry_harness(
        candidate_web_source,
        backend_harness_dir,
    )
    server_harness = verifier.run_server_runtime_harness(
        candidate_server_source,
        server_harness_dir,
    )
    boundary = verifier.run_boundary_watch(root)
    if not boundary["passed"]:
        raise ApplyError(
            "Boundary Watch failed: "
            + boundary.get("stdout", "")
            + boundary.get("stderr", "")
        )
    return {
        "python_compile": True,
        "baseline_javascript": baseline_js,
        "candidate_javascript": candidate_js,
        "javascript_harness": js_harness,
        "backend_harness": backend_harness,
        "server_harness": server_harness,
        "boundary_watch": boundary,
    }


def live_postflight(root: Path, output: Path) -> dict[str, Any]:
    web_path = root / "core/foxai_web.py"
    server_path = root / "core/server.py"
    web_source = web_path.read_text(encoding="utf-8")
    server_source = server_path.read_text(encoding="utf-8")

    compile(web_source, str(web_path), "exec")
    compile(server_source, str(server_path), "exec")

    actual_hashes = {
        "core/foxai_web.py": sha256(web_path),
        "core/server.py": sha256(server_path),
    }
    if actual_hashes != CANDIDATE_HASHES:
        raise ApplyError("Postflight live candidate hashes do not match.")

    javascript_dir = output / "postflight_javascript"
    js_harness_dir = output / "postflight_javascript_harness"
    backend_harness_dir = output / "postflight_backend_harness"
    server_harness_dir = output / "postflight_server_harness"

    for directory in (
        javascript_dir,
        js_harness_dir,
        backend_harness_dir,
        server_harness_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    scripts = verifier.extract_scripts(web_source)
    js_check = verifier.node_check(
        scripts,
        javascript_dir,
        "postflight",
    )
    js_harness = verifier.run_js_behavior_harness(
        scripts,
        js_harness_dir,
    )
    backend_harness = verifier.run_web_backend_registry_harness(
        web_source,
        backend_harness_dir,
    )
    server_harness = verifier.run_server_runtime_harness(
        server_source,
        server_harness_dir,
    )
    boundary = verifier.run_boundary_watch(root)
    if not boundary["passed"]:
        raise ApplyError(
            "Postflight Boundary Watch failed: "
            + boundary.get("stdout", "")
            + boundary.get("stderr", "")
        )

    return {
        "actual_hashes": actual_hashes,
        "python_compile": True,
        "javascript": js_check,
        "javascript_harness": js_harness,
        "backend_harness": backend_harness,
        "server_harness": server_harness,
        "boundary_watch": boundary,
    }


def copy_with_fsync(source: Path, target: Path) -> None:
    data = source.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def verified_backup(root: Path, timestamp: str) -> tuple[Path, dict[str, Any]]:
    backup_root = (
        root
        / "Backups"
        / "SecurityMilestone"
        / f"MPS3_{timestamp}"
        / "core"
    )
    backup_root.mkdir(parents=True, exist_ok=False)

    backup_files = {
        "core/foxai_web.py": backup_root / "foxai_web.py",
        "core/server.py": backup_root / "server.py",
    }
    checks = []
    for relative, backup_path in backup_files.items():
        shutil.copy2(root / relative, backup_path)
        actual = sha256(backup_path)
        checks.append({
            "path": str(backup_path),
            "expected_sha256": BASELINE_HASHES[relative],
            "actual_sha256": actual,
            "ok": actual == BASELINE_HASHES[relative],
        })
    if not all(item["ok"] for item in checks):
        raise ApplyError("Backup verification failed.")
    return backup_root.parent, {
        "verified": True,
        "files": checks,
        "paths": {
            relative: str(path)
            for relative, path in backup_files.items()
        },
    }


def install_candidates(
    root: Path,
    package_dir: Path,
) -> list[str]:
    stage_paths = {
        "core/server.py": root / "core" / f".server.py.phase3.{os.getpid()}.new",
        "core/foxai_web.py":
            root / "core" / f".foxai_web.py.phase3.{os.getpid()}.new",
    }
    source_paths = {
        "core/server.py": package_dir / "payload/candidate/core/server.py",
        "core/foxai_web.py":
            package_dir / "payload/candidate/core/foxai_web.py",
    }
    replaced = []
    try:
        for relative in TARGETS:
            copy_with_fsync(source_paths[relative], stage_paths[relative])
            if sha256(stage_paths[relative]) != CANDIDATE_HASHES[relative]:
                raise ApplyError(f"Staged candidate hash failed: {relative}")

        # Services are required closed. Replace server first, then WebUI.
        for relative in TARGETS:
            os.replace(stage_paths[relative], root / relative)
            replaced.append(relative)
        return replaced
    finally:
        for path in stage_paths.values():
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass


def rollback(
    root: Path,
    backup_info: dict[str, Any],
    output: Path,
) -> dict[str, Any]:
    result = {
        "attempted": True,
        "succeeded": False,
        "restored_hashes": {},
        "boundary_watch": None,
        "failure": None,
    }
    try:
        backup_paths = {
            relative: Path(path)
            for relative, path in backup_info["paths"].items()
        }
        stage_paths = {
            "core/server.py":
                root / "core" / f".server.py.phase3.rollback.{os.getpid()}",
            "core/foxai_web.py":
                root / "core" / f".foxai_web.py.phase3.rollback.{os.getpid()}",
        }
        try:
            for relative in TARGETS:
                copy_with_fsync(backup_paths[relative], stage_paths[relative])
                if sha256(stage_paths[relative]) != BASELINE_HASHES[relative]:
                    raise ApplyError(
                        f"Rollback stage hash failed: {relative}"
                    )
            for relative in TARGETS:
                os.replace(stage_paths[relative], root / relative)
        finally:
            for path in stage_paths.values():
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass

        restored = {
            relative: sha256(root / relative)
            for relative in TARGETS
        }
        result["restored_hashes"] = restored
        if any(
            restored[relative] != BASELINE_HASHES[relative]
            for relative in TARGETS
        ):
            raise ApplyError("Rollback live hashes do not match baseline.")

        compile(
            (root / "core/foxai_web.py").read_text(encoding="utf-8"),
            str(root / "core/foxai_web.py"),
            "exec",
        )
        compile(
            (root / "core/server.py").read_text(encoding="utf-8"),
            str(root / "core/server.py"),
            "exec",
        )
        boundary = verifier.run_boundary_watch(root)
        result["boundary_watch"] = boundary
        if not boundary["passed"]:
            raise ApplyError("Rollback Boundary Watch failed.")
        result["succeeded"] = True
    except Exception as exc:
        result["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    return result


def write_report(output: Path, receipt: dict[str, Any]) -> None:
    lines = [
        "# FOXAI Model Profile Selector + Verified Runtime — Apply Report",
        "",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Operator approved: **{receipt['operator_approved']}**",
        f"- Changed files: **{receipt['changed_files']}**",
        f"- Delete operations: **{receipt['delete_operations']}**",
        f"- Rollback performed: **{receipt['rollback_performed']}**",
        f"- Live files modified: **{receipt['live_files_modified']}**",
        "",
    ]
    if receipt.get("backup"):
        lines.extend([
            "## Backup",
            "",
            f"- Location: `{receipt['backup'].get('root')}`",
            f"- Verified: **{receipt['backup'].get('verified')}**",
            "",
        ])
    if receipt.get("final_hashes"):
        lines.extend([
            "## Final hashes",
            "",
            f"- `core/foxai_web.py`: `{receipt['final_hashes'].get('core/foxai_web.py')}`",
            f"- `core/server.py`: `{receipt['final_hashes'].get('core/server.py')}`",
            "",
        ])
    if receipt.get("failure"):
        lines.extend([
            "## Failure",
            "",
            f"- Type: `{receipt['failure'].get('type')}`",
            f"- Message: {receipt['failure'].get('message')}",
            "",
        ])
    if receipt.get("rollback"):
        lines.extend([
            "## Rollback",
            "",
            f"- Attempted: **{receipt['rollback'].get('attempted')}**",
            f"- Succeeded: **{receipt['rollback'].get('succeeded')}**",
            "",
        ])
    lines.extend([
        "## Locked behavior",
        "",
        "- Profile-card selection remains pending-only.",
        "- Starting remains an explicit operator action.",
        "- Text profiles use reasoning off with budget 0.",
        "- Vision profiles preserve current engine reasoning behavior.",
        "- Raw exact-GGUF fallback remains.",
        "- Chat Timing, claim guard, Mission Archive, receipts, Navigation Focus, accordion behavior, and Fox Sentry remain verified.",
        "",
    ])
    (output / "report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def zip_output(output: Path) -> Path:
    zip_target = output.with_suffix(".zip")
    zip_target.unlink(missing_ok=True)
    with zipfile.ZipFile(
        zip_target,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for file in sorted(output.rglob("*")):
            if file.is_file():
                archive.write(file, arcname=f"{output.name}/{file.relative_to(output)}")
    return zip_target


def main() -> int:
    package_dir = Path(__file__).resolve().parent
    root = verifier.find_root(package_dir)
    created = datetime.now(timezone.utc)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    output = package_dir / f"MPS3_{stamp}"
    output.mkdir(parents=True, exist_ok=False)

    receipt: dict[str, Any] = {
        "action": "model_profile_selector_runtime_phase3_transactional_apply",
        "created": created.isoformat(),
        "root": str(root),
        "state": "running",
        "verified": False,
        "operator_approved": False,
        "changed_files": [],
        "delete_operations": [],
        "live_files_modified": False,
        "configuration_modified": False,
        "default_model_changed": False,
        "engine_started": False,
        "model_loaded": False,
        "rollback_performed": False,
        "backup": None,
        "failure": None,
        "rollback": None,
        "checks": [],
    }

    backup_info = None
    replacement_started = False
    non_target_before = non_target_snapshot(root)

    try:
        active_ports = [
            {"port": port, "label": label}
            for port, label in PORTS_REQUIRED_CLOSED.items()
            if port_open(port)
        ]
        if active_ports:
            raise ApplyError(
                "Required local ports are active. Close WebUI, Chat Engine, "
                "and benchmark servers before applying: "
                + repr(active_ports)
            )

        manifest = package_manifest_check(package_dir)
        baselines = verify_baselines(root)
        approved = verify_approved_preview(package_dir)
        payload = verify_payload_and_diffs(package_dir, root)
        preflight = candidate_preflight(
            root, payload, output / "preflight", "preflight"
        )

        receipt["checks"].extend([
            {"id": "package_manifest", "ok": True, "detail": manifest},
            {"id": "locked_baselines", "ok": True, "detail": baselines},
            {"id": "approved_preview", "ok": True, "detail": approved},
            {"id": "payload_and_exact_diffs", "ok": True, "detail": {
                "candidate_checks": payload["candidate_checks"],
                "diff_checks": payload["diff_checks"],
                "exact_diff_reconstruction":
                    payload["exact_diff_reconstruction"],
            }},
            {"id": "candidate_preflight", "ok": True, "detail": preflight},
            {"id": "ports_closed", "ok": True, "detail": PORTS_REQUIRED_CLOSED},
        ])

        print()
        print("PREVIEW AND PREFLIGHT VERIFIED.")
        print()
        print("Proposed live files:")
        print("  core/foxai_web.py")
        print("  core/server.py")
        print()
        print("No files will be deleted.")
        print("A verified backup and automatic rollback are required.")
        print()
        approval = input(
            "Type the exact approval phrase to apply:\n"
            f"{APPROVAL_PHRASE}\n> "
        ).strip()
        if approval != APPROVAL_PHRASE:
            raise ApplyError("Approval phrase did not match. No apply occurred.")
        receipt["operator_approved"] = True

        backup_root, backup_checks = verified_backup(root, stamp)
        backup_info = backup_checks
        receipt["backup"] = {
            "root": str(backup_root),
            "verified": backup_checks["verified"],
            "files": backup_checks["files"],
        }

        replacement_started = True
        replaced = install_candidates(root, package_dir)
        receipt["changed_files"] = replaced
        receipt["live_files_modified"] = bool(replaced)

        postflight = live_postflight(root, output / "postflight")
        non_target_after = non_target_snapshot(root)
        non_target_changes = snapshot_changes(
            non_target_before, non_target_after
        )
        if non_target_changes:
            raise ApplyError(
                "A locked dependency or security log changed: "
                + repr(non_target_changes)
            )

        receipt.update({
            "state": "applied_verified",
            "verified": True,
            "changed_files": ["core/server.py", "core/foxai_web.py"],
            "live_files_modified": True,
            "final_hashes": postflight["actual_hashes"],
            "checks": receipt["checks"] + [
                {
                    "id": "verified_backup",
                    "ok": True,
                    "detail": receipt["backup"],
                },
                {
                    "id": "transactional_two_file_replace",
                    "ok": True,
                    "detail": ["core/server.py", "core/foxai_web.py"],
                },
                {
                    "id": "postflight",
                    "ok": True,
                    "detail": postflight,
                },
                {
                    "id": "locked_dependencies_and_security_logs_unchanged",
                    "ok": True,
                    "detail": non_target_changes,
                },
                {
                    "id": "no_delete_operations",
                    "ok": True,
                    "detail": [],
                },
            ],
        })

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

        if replacement_started and backup_info is not None:
            receipt["rollback_performed"] = True
            rollback_result = rollback(
                root, backup_info, output / "rollback"
            )
            receipt["rollback"] = rollback_result
            receipt["live_files_modified"] = not rollback_result["succeeded"]
            receipt["state"] = (
                "rolled_back_fail_closed"
                if rollback_result["succeeded"]
                else "rollback_failed"
            )
            receipt["verified"] = rollback_result["succeeded"]
            if rollback_result["succeeded"]:
                receipt["changed_files"] = []
        else:
            receipt["state"] = "stopped_fail_closed"
            receipt["verified"] = True
            receipt["changed_files"] = []
            receipt["live_files_modified"] = False

    receipt_path = output / "receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )
    write_report(output, receipt)
    output_zip = zip_output(output)

    print()
    print("=" * 72)
    print("FOXAI MODEL PROFILE SELECTOR + VERIFIED RUNTIME")
    print("PHASE 3 TRANSACTIONAL APPLY")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Operator approved:", receipt["operator_approved"])
    print("Changed files:", receipt["changed_files"])
    print("Delete operations:", receipt["delete_operations"])
    print("Rollback performed:", receipt["rollback_performed"])
    print("Output ZIP:", output_zip)
    if receipt.get("final_hashes"):
        print("WebUI SHA-256:", receipt["final_hashes"].get("core/foxai_web.py"))
        print("Server SHA-256:", receipt["final_hashes"].get("core/server.py"))
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    print()
    input("Press Enter to close...")

    return 0 if receipt["state"] == "applied_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
