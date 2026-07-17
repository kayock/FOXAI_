from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import traceback

EXPECTED_BASELINES = {'Config/fleet_registry.json': '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6', 'Config/model_sources.json': 'c17eb3b8b6c93734f7e117522213c95af6c105fe26400d0560768fe586e21c91', 'Launch FOXAI Workshop.bat': '7f974eeeaa66c6fd331b6b3e8cb5f312d25a410761817ad35408ccb47acd4480', 'START_FOXAI_WEB_PORTABLE.bat': '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1', 'core/engineer_agent.py': 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19', 'core/foxai_web.py': 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7', 'core/model_sources.py': 'e00a861265eff8826c4d7eeb89b3765e719b88f349811a2e608525d8a3f91ea2', 'core/security_containment.py': '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24', 'core/server.py': '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81', 'core/service_registry.py': 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b', 'env/python/python314._pth': '48d77ccee161647ef7053cb563d3b37b4053938d5ad92ae64ccedc2165bcd42d', 'tests/test_boundary_watch.py': 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382', 'tests/test_model_sources.py': 'ec94f8b8d90d36f05385db74400dd99b436cd4e488b1b517bcb77442a16fc6f2', 'ui/main_window.py': '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3'}
EXPECTED_SHORTCUTS = {'desktop': {'filename': 'Z:\\Launch FOXAI Workshop.bat - Shortcut.lnk', 'sha256': '2a41fab836312e95e40d5404bc379b050f31b7cd61bd1ac26bb22ce902aeae02'}, 'web': {'filename': 'Z:\\START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk', 'sha256': 'af0f79cfc583c51c4108cb2c1baa86634bf427e2eb881c64ed51a5994f2e40dd'}}
SOURCE_EVIDENCE = {'phase3c_action': 'foxai_pdr_phase3c_quarantined_runtime_acquisition', 'phase3c_state': 'quarantine_acquisition_verified', 'phase3c_verified': True, 'runtime_file_count': 3294, 'runtime_size_bytes': 128353539, 'desktop_package_file_count': 389, 'desktop_package_size_bytes': 18866925, 'desktop_distributions': [{'name': 'customtkinter', 'version': '6.0.0', 'requires': ['darkdetect', 'typing_extensions; python_version <= "3.7"', 'packaging'], 'file_count': 103}, {'name': 'darkdetect', 'version': '0.8.0', 'requires': ['pyobjc-framework-Cocoa ; (platform_system == "Darwin") and extra == \'macos-listener\''], 'file_count': 18}, {'name': 'packaging', 'version': '26.2', 'requires': [], 'file_count': 48}, {'name': 'pillow', 'version': '12.3.0', 'requires': ['furo; extra == "docs"', 'olefile; extra == "docs"', 'sphinx>=8.2; extra == "docs"', 'sphinx-autobuild; extra == "docs"', 'sphinx-copybutton; extra == "docs"', 'sphinx-inline-tabs; extra == "docs"', 'sphinxext-opengraph; extra == "docs"', 'olefile; extra == "fpx"', 'olefile; extra == "mic"', 'arro3-compute; extra == "test-arrow"', 'arro3-core; extra == "test-arrow"', 'nanoarrow; extra == "test-arrow"', 'pyarrow; extra == "test-arrow"', 'coverage>=7.4.2; extra == "tests"', 'defusedxml; extra == "tests"', 'markdown2; extra == "tests"', 'olefile; extra == "tests"', 'packaging; extra == "tests"', 'pytest; extra == "tests"', 'pytest-cov; extra == "tests"', 'pytest-timeout; extra == "tests"', 'pytest-xdist; extra == "tests"', 'setuptools; extra == "tests"', 'trove-classifiers>=2024.10.12; extra == "tests"', 'defusedxml; extra == "xmp"'], 'file_count': 220}], 'verification_checks': {'executable_inside_quarantine': True, 'prefix_inside_quarantine': True, 'base_prefix_inside_quarantine': True, 'user_site_disabled': True, 'user_site_absent_from_sys_path': True, 'all_required_modules_available': True, 'all_module_origins_correct': True, 'dependency_closure_compiles': True}}

def utc_now():
    return dt.datetime.now(dt.timezone.utc)

def sha256_file(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def canonical_hash(value):
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def safe_relative(value):
    posix = PurePosixPath(str(value).replace("\\", "/"))
    if posix.is_absolute() or ".." in posix.parts or not posix.parts:
        raise RuntimeError(f"Unsafe relative path in manifest: {value}")
    return Path(*posix.parts)

def is_ephemeral_python_cache(relative):
    normalized = str(relative).replace("\\", "/").lower()
    parts = PurePosixPath(normalized).parts
    return (
        "__pycache__" in parts
        or normalized.endswith(".pyc")
        or normalized.endswith(".pyo")
    )

def snapshot_baselines(root: Path):
    rows = []
    for relative, expected in sorted(EXPECTED_BASELINES.items()):
        full = root / Path(relative)
        actual = sha256_file(full)
        rows.append({
            "path": relative,
            "exists": full.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })
    return rows

def snapshot_shortcuts(root: Path):
    usb_root = Path(root.anchor)
    rows = {}
    for key, expected in EXPECTED_SHORTCUTS.items():
        full = usb_root / expected["filename"]
        actual = sha256_file(full)
        rows[key] = {
            "path": str(full),
            "exists": full.is_file(),
            "expected_sha256": expected["sha256"],
            "actual_sha256": actual,
            "matches_expected": actual == expected["sha256"],
        }
    return rows

def snapshots_pass(baselines, shortcuts):
    return (
        all(row["matches_expected"] for row in baselines)
        and all(row["matches_expected"] for row in shortcuts.values())
    )

def find_latest_verified_phase3c(root: Path):
    q_root = root / "PDR3C_QUARANTINE" / "Q"
    if not q_root.is_dir():
        raise RuntimeError(f"Phase 3C Q folder was not found: {q_root}")

    candidates = []
    for child in q_root.iterdir():
        if not child.is_dir():
            continue
        receipt_path = child / "UPLOAD_THIS" / "receipt.json"
        manifest_path = child / "UPLOAD_THIS" / "QUARANTINE_FILE_MANIFEST.json"
        verification_path = child / "UPLOAD_THIS" / "QUARANTINE_VERIFICATION.json"
        if not (receipt_path.is_file() and manifest_path.is_file() and verification_path.is_file()):
            continue
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if (
            receipt.get("state") == "quarantine_acquisition_verified"
            and receipt.get("verified") is True
            and receipt.get("after_snapshot_passed") is True
            and (verification.get("verification") or {}).get("verified") is True
        ):
            candidates.append((child.name, child, receipt, manifest, verification))

    if not candidates:
        raise RuntimeError("No verified Phase 3C quarantine run was found.")

    candidates.sort(key=lambda item: item[0], reverse=True)
    name, run_root, receipt, manifest, verification = candidates[0]
    return {
        "name": name,
        "run_root": run_root,
        "receipt_path": run_root / "UPLOAD_THIS" / "receipt.json",
        "manifest_path": run_root / "UPLOAD_THIS" / "QUARANTINE_FILE_MANIFEST.json",
        "verification_path": run_root / "UPLOAD_THIS" / "QUARANTINE_VERIFICATION.json",
        "receipt": receipt,
        "manifest": manifest,
        "verification": verification,
    }

def verify_phase3c_identity(selected):
    receipt = selected["receipt"]
    manifest = selected["manifest"]
    verification = selected["verification"]

    checks = {
        "receipt_action": receipt.get("action") == SOURCE_EVIDENCE["phase3c_action"],
        "receipt_state": receipt.get("state") == SOURCE_EVIDENCE["phase3c_state"],
        "receipt_verified": receipt.get("verified") is SOURCE_EVIDENCE["phase3c_verified"],
        "runtime_file_count": len(manifest.get("runtime_files") or []) == SOURCE_EVIDENCE["runtime_file_count"],
        "runtime_size_bytes": sum(x.get("size_bytes", 0) for x in manifest.get("runtime_files") or []) == SOURCE_EVIDENCE["runtime_size_bytes"],
        "desktop_package_file_count": len(manifest.get("desktop_package_files") or []) == SOURCE_EVIDENCE["desktop_package_file_count"],
        "desktop_package_size_bytes": sum(x.get("size_bytes", 0) for x in manifest.get("desktop_package_files") or []) == SOURCE_EVIDENCE["desktop_package_size_bytes"],
        "verification_true": (verification.get("verification") or {}).get("verified") is True,
    }
    return {"checks": checks, "passed": all(checks.values())}

def planned_file_status(destination: Path, expected_hash: str):
    if not destination.exists():
        return "ADD", None
    if not destination.is_file():
        return "CONFLICT_NON_FILE", None
    actual = sha256_file(destination)
    if actual == expected_hash:
        return "ALREADY_MATCHES", actual
    return "CONFLICT_DIFFERENT_FILE", actual

def verify_quarantine_sources(selected, upload_dir: Path):
    manifest = selected["manifest"]
    run_root = selected["run_root"]
    runtime_source = run_root / "quarantine" / "Runtime" / "Desktop" / "python"
    package_source = run_root / "quarantine" / "Runtime" / "Desktop" / "site-packages"

    entries = []
    excluded_ephemeral = []
    manifest_total = (
        len(manifest.get("runtime_files") or [])
        + len(manifest.get("desktop_package_files") or [])
    )

    for kind, records, source_root in (
        ("runtime", manifest.get("runtime_files") or [], runtime_source),
        ("desktop_package", manifest.get("desktop_package_files") or [], package_source),
    ):
        for item in records:
            relative = safe_relative(item["relative"])
            if is_ephemeral_python_cache(relative):
                excluded_ephemeral.append({
                    "kind": kind,
                    "relative": str(relative).replace("\\", "/"),
                    "reason": "disposable_python_bytecode_cache",
                    "size_bytes": item.get("size_bytes", 0),
                })
                continue

            record = {
                "kind": kind,
                "relative": str(relative).replace("\\", "/"),
                "source": str(source_root / relative),
                "size_bytes": item["size_bytes"],
                "expected_sha256": item["sha256"],
            }
            if kind == "desktop_package":
                record["distribution"] = item.get("distribution")
                record["version"] = item.get("version")
            entries.append(record)

    print(
        f"Stage 1/4: hashing {len(entries)} deterministic source files "
        f"({len(excluded_ephemeral)} cache files excluded)...",
        flush=True,
    )

    failed = []
    for current, item in enumerate(entries, start=1):
        source = Path(item["source"])
        actual = sha256_file(source)
        item["actual_sha256"] = actual
        item["verified"] = source.is_file() and actual == item["expected_sha256"]
        if not item["verified"]:
            failed.append(item)
        if current == 1 or current % 250 == 0 or current == len(entries):
            print(f"  Stable source hash: {current}/{len(entries)}", flush=True)

    summary = {
        "manifest_total": manifest_total,
        "deployable_stable_total": len(entries),
        "excluded_ephemeral_count": len(excluded_ephemeral),
        "excluded_ephemeral_bytes": sum(x["size_bytes"] for x in excluded_ephemeral),
        "excluded_categories": ["__pycache__", ".pyc", ".pyo"],
        "failed_stable_count": len(failed),
        "failed_stable": failed[:100],
        "excluded_ephemeral_sample": excluded_ephemeral[:100],
    }
    (upload_dir / "SOURCE_HASH_SUMMARY.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    if failed:
        raise RuntimeError(
            f"{len(failed)} deterministic quarantined source file(s) failed hash verification."
        )

    return entries, summary

def build_runtime_manifest(selected, source_entries, source_summary):
    manifest = selected["manifest"]
    runtime_entries = [x for x in source_entries if x["kind"] == "runtime"]
    package_entries = [x for x in source_entries if x["kind"] == "desktop_package"]

    distribution_counts = {}
    for item in package_entries:
        key = (item.get("distribution") or "unknown", item.get("version"))
        distribution_counts[key] = distribution_counts.get(key, 0) + 1

    deployable_distributions = [
        {
            "name": name,
            "version": version,
            "deployable_file_count": count,
        }
        for (name, version), count in sorted(
            distribution_counts.items(), key=lambda value: value[0][0].lower()
        )
    ]

    return {
        "format": "foxai_portable_desktop_runtime_manifest_v2",
        "created_from_phase3c": selected["receipt"].get("created"),
        "phase3c_run": selected["name"],
        "python_version": (
            ((selected["receipt"].get("source_selection") or {}).get("runtime_source") or {})
            .get("inspection", {})
            .get("version")
        ),
        "runtime_file_count": len(runtime_entries),
        "desktop_package_file_count": len(package_entries),
        "runtime_size_bytes": sum(x.get("size_bytes", 0) for x in runtime_entries),
        "desktop_package_size_bytes": sum(x.get("size_bytes", 0) for x in package_entries),
        "excluded_ephemeral_cache_count": source_summary["excluded_ephemeral_count"],
        "excluded_ephemeral_cache_bytes": source_summary["excluded_ephemeral_bytes"],
        "bytecode_policy": {
            "ship_pyc_files": False,
            "ship___pycache___directories": False,
            "launcher_sets_PYTHONDONTWRITEBYTECODE": True,
        },
        "desktop_distributions": deployable_distributions,
        "files": [
            {
                "kind": item["kind"],
                "relative": item["relative"],
                "size_bytes": item["size_bytes"],
                "sha256": item["expected_sha256"],
                **(
                    {
                        "distribution": item.get("distribution"),
                        "version": item.get("version"),
                    }
                    if item["kind"] == "desktop_package"
                    else {}
                ),
            }
            for item in source_entries
        ],
    }

def plan_exact_destinations(root: Path, source_entries, proposed_files):
    print("Stage 2/4: checking exact proposed destination paths...", flush=True)
    actions = []
    conflicts = []
    already_matches = []
    add_bytes = 0

    for index, item in enumerate(source_entries, start=1):
        relative = Path(*PurePosixPath(item["relative"]).parts)
        if item["kind"] == "runtime":
            destination = root / "Runtime" / "Desktop" / "python" / relative
        else:
            destination = root / "Runtime" / "Desktop" / "site-packages" / relative

        status, actual = planned_file_status(destination, item["expected_sha256"])
        action = {
            "kind": item["kind"],
            "source": item["source"],
            "destination": str(destination),
            "relative": item["relative"],
            "size_bytes": item["size_bytes"],
            "expected_sha256": item["expected_sha256"],
            "destination_status": status,
            "destination_sha256": actual,
        }
        actions.append(action)
        if status == "ADD":
            add_bytes += item["size_bytes"]
        elif status == "ALREADY_MATCHES":
            already_matches.append(action)
        else:
            conflicts.append(action)

        if index == 1 or index % 500 == 0 or index == len(source_entries):
            print(f"  Destination check: {index}/{len(source_entries)}", flush=True)

    for item in proposed_files:
        status, actual = planned_file_status(item["destination"], item["sha256"])
        action = {
            "kind": item["kind"],
            "source": item["source"],
            "destination": str(item["destination"]),
            "relative": item["relative"],
            "size_bytes": item["size_bytes"],
            "expected_sha256": item["sha256"],
            "destination_status": status,
            "destination_sha256": actual,
        }
        actions.append(action)
        if status == "ADD":
            add_bytes += item["size_bytes"]
        elif status == "ALREADY_MATCHES":
            already_matches.append(action)
        else:
            conflicts.append(action)

    return {
        "actions": actions,
        "conflicts": conflicts,
        "already_matches": already_matches,
        "add_bytes": add_bytes,
    }

def make_report(receipt, plan):
    plan = plan or {}
    counts = plan.get("summary") or receipt.get("plan_summary") or {}
    lines = [
        "# FOXAI Portable Desktop Runtime Phase 3D-P FIX1",
        "## Preview-First Exact Live Apply Plan",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        "- Live apply performed: **False**",
        "- Live files modified: **False**",
        "- Apply capability present: **False**",
        "",
    ]

    if receipt.get("failure"):
        lines += [
            "## Fail-closed result",
            "",
            f"- Failure: `{receipt['failure'].get('message')}`",
            f"- Protected state passed after stop: **{receipt.get('after_snapshot_passed')}**",
            "- No live apply was performed.",
            "",
        ]

    if plan.get("summary"):
        lines += [
            "## Verified Phase 3C source",
            "",
            f"- Quarantine run: `{plan.get('phase3c_run')}`",
            f"- Stable source files hash-verified: **{counts.get('source_file_count')}**",
            f"- Ephemeral bytecode cache files excluded: **{counts.get('excluded_ephemeral_count')}**",
            f"- Runtime files: **{counts.get('runtime_file_count')}**",
            f"- Desktop package files: **{counts.get('desktop_package_file_count')}**",
            "",
            "## Exact proposed additions",
            "",
            f"- Total planned files: **{counts.get('planned_file_count')}**",
            f"- New files to add: **{counts.get('add_count')}**",
            f"- Files already matching: **{counts.get('already_matches_count')}**",
            f"- Conflicts: **{counts.get('conflict_count')}**",
            f"- New bytes: **{counts.get('add_bytes')}**",
            f"- Free bytes on USB: **{counts.get('free_bytes')}**",
            "",
            "### New live paths",
            "",
            "- `Runtime\\Desktop\\python\\**`",
            "- `Runtime\\Desktop\\site-packages\\**`",
            "- `Runtime\\Desktop\\DESKTOP_RUNTIME_MANIFEST.json`",
            "- `System\\PortableRuntime\\verify_desktop_runtime.py`",
            "- `START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat`",
            "",
            "### Explicitly unchanged",
            "",
            "- Both USB-root shortcuts",
            "- `Launch FOXAI Workshop.bat`",
            "- `START_FOXAI_WEB_PORTABLE.bat`",
            "- `foxai.py`",
            "- `ui\\main_window.py`",
            "- `Runtime\\Core\\**`",
            "- ComfyUI, Models, Config, source, and protected baselines",
            "",
            "## Bytecode cache policy",
            "",
            "- `__pycache__`, `.pyc`, and `.pyo` files are not part of the portable runtime.",
            "- The diagnostic and future portable launcher set `PYTHONDONTWRITEBYTECODE=1`.",
            "",
            "## Deferred",
            "",
            "- The normal `START_FOXAI_DESKTOP_PORTABLE.bat` launcher is not part of this apply plan.",
            "- FOXAI will not be launched during Phase 3D apply.",
            "- The diagnostic must pass before a normal portable launcher is considered.",
            "",
            "## Approval",
            "",
            f"- Plan ID: `{plan.get('plan_id')}`",
            f"- Exact approval phrase: **`{plan.get('approval_phrase')}`**",
            "",
            "**No apply package is included. Review and approve this exact plan before Phase 3D-A is created.**",
        ]

        if counts.get("conflict_count"):
            lines += ["", "## Conflicts", ""]
            for item in plan.get("conflicts", [])[:50]:
                lines.append(f"- `{item['destination']}` — {item['destination_status']}")
    else:
        lines += [
            "## Plan status",
            "",
            "No exact apply plan was produced during this run.",
        ]

    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()

    started = utc_now()
    root = Path(args.root).resolve()
    bundle = Path(args.bundle).resolve()
    run_root = bundle / "PREVIEW_OUTPUT" / started.strftime("%Y%m%dT%H%M%SZ")
    upload_dir = run_root / "UPLOAD_THIS"
    proposed_dir = upload_dir / "PROPOSED_FILES_NOT_APPLIED"
    proposed_dir.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_pdr_phase3d_preview_first_exact_apply_plan_fix1",
        "created": started.isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "preview_only": True,
        "apply_capability_present": False,
        "live_apply_performed": False,
        "live_files_modified": False,
        "shortcut_changes": False,
        "launcher_changes": False,
        "runtime_live_changes": False,
        "source_changes": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "desktop_gui_launched": False,
        "comfyui_launched": False,
        "recursive_drive_scan": False,
        "phase3d_apply_authorized": False,
        "writes_limited_to": str(run_root),
    }
    exit_code = 1

    try:
        before_baselines = snapshot_baselines(root)
        before_shortcuts = snapshot_shortcuts(root)
        receipt["protected_baselines_before"] = before_baselines
        receipt["protected_shortcuts_before"] = before_shortcuts
        receipt["before_snapshot_passed"] = snapshots_pass(before_baselines, before_shortcuts)
        if not receipt["before_snapshot_passed"]:
            raise RuntimeError("Protected baseline or shortcut verification failed before preview.")

        selected = find_latest_verified_phase3c(root)
        identity = verify_phase3c_identity(selected)
        receipt["phase3c_identity"] = identity
        if not identity["passed"]:
            failed = [name for name, ok in identity["checks"].items() if not ok]
            raise RuntimeError("Phase 3C source identity failed: " + ", ".join(failed))

        source_entries, source_summary = verify_quarantine_sources(selected, upload_dir)

        runtime_manifest = build_runtime_manifest(selected, source_entries, source_summary)
        runtime_manifest_bytes = json.dumps(
            runtime_manifest, indent=2, ensure_ascii=False
        ).encode("utf-8")

        proposed_manifest_path = proposed_dir / "Runtime" / "Desktop" / "DESKTOP_RUNTIME_MANIFEST.json"
        proposed_verifier_path = proposed_dir / "System" / "PortableRuntime" / "verify_desktop_runtime.py"
        proposed_launcher_path = proposed_dir / "START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat"

        for path in (proposed_manifest_path, proposed_verifier_path, proposed_launcher_path):
            path.parent.mkdir(parents=True, exist_ok=True)

        proposed_manifest_path.write_bytes(runtime_manifest_bytes)
        verifier_source = (bundle / "verify_desktop_runtime.py").read_bytes()
        launcher_source = (bundle / "START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat").read_bytes()
        proposed_verifier_path.write_bytes(verifier_source)
        proposed_launcher_path.write_bytes(launcher_source)

        proposed_files = [
            {
                "kind": "runtime_manifest",
                "source": str(proposed_manifest_path),
                "destination": root / "Runtime" / "Desktop" / "DESKTOP_RUNTIME_MANIFEST.json",
                "relative": "Runtime/Desktop/DESKTOP_RUNTIME_MANIFEST.json",
                "size_bytes": proposed_manifest_path.stat().st_size,
                "sha256": sha256_file(proposed_manifest_path),
            },
            {
                "kind": "diagnostic_verifier",
                "source": str(proposed_verifier_path),
                "destination": root / "System" / "PortableRuntime" / "verify_desktop_runtime.py",
                "relative": "System/PortableRuntime/verify_desktop_runtime.py",
                "size_bytes": proposed_verifier_path.stat().st_size,
                "sha256": sha256_file(proposed_verifier_path),
            },
            {
                "kind": "diagnostic_launcher",
                "source": str(proposed_launcher_path),
                "destination": root / "START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat",
                "relative": "START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat",
                "size_bytes": proposed_launcher_path.stat().st_size,
                "sha256": sha256_file(proposed_launcher_path),
            },
        ]

        destination_plan = plan_exact_destinations(root, source_entries, proposed_files)
        disk = shutil.disk_usage(root)
        required_with_margin = int(destination_plan["add_bytes"] * 1.15) + 50 * 1024 * 1024
        enough_space = disk.free >= required_with_margin

        plan_core = {
            "format": "foxai_pdr_phase3d_exact_apply_plan_v2",
            "created": utc_now().isoformat(),
            "foxai_root": str(root),
            "phase3c_run": selected["name"],
            "phase3c_receipt_sha256": sha256_file(selected["receipt_path"]),
            "phase3c_manifest_sha256": sha256_file(selected["manifest_path"]),
            "phase3c_verification_sha256": sha256_file(selected["verification_path"]),
            "summary": {
                "source_file_count": len(source_entries),
                "excluded_ephemeral_count": source_summary["excluded_ephemeral_count"],
                "excluded_ephemeral_bytes": source_summary["excluded_ephemeral_bytes"],
                "runtime_file_count": sum(1 for x in source_entries if x["kind"] == "runtime"),
                "desktop_package_file_count": sum(1 for x in source_entries if x["kind"] == "desktop_package"),
                "planned_file_count": len(destination_plan["actions"]),
                "add_count": sum(1 for x in destination_plan["actions"] if x["destination_status"] == "ADD"),
                "already_matches_count": len(destination_plan["already_matches"]),
                "conflict_count": len(destination_plan["conflicts"]),
                "add_bytes": destination_plan["add_bytes"],
                "required_bytes_with_margin": required_with_margin,
                "free_bytes": disk.free,
                "enough_free_space": enough_space,
            },
            "actions": destination_plan["actions"],
            "conflicts": destination_plan["conflicts"],
            "already_matches": destination_plan["already_matches"],
            "existing_files_to_modify": [],
            "files_to_delete": [],
            "directories_to_remove": [],
            "protected_shortcuts_to_change": [],
            "existing_launchers_to_change": [],
            "deferred": [
                "START_FOXAI_DESKTOP_PORTABLE.bat",
                "Any shortcut retargeting",
                "Launching FOXAI with the new runtime",
            ],
        }
        plan_id = canonical_hash(plan_core)
        plan_core["plan_id"] = plan_id
        plan_core["approval_phrase"] = f"APPROVE PDR3D {plan_id[:12].upper()}"

        (upload_dir / "EXACT_APPLY_PLAN.json").write_text(
            json.dumps(plan_core, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        print("Stage 3/4: confirming protected live files remain unchanged...", flush=True)
        after_baselines = snapshot_baselines(root)
        after_shortcuts = snapshot_shortcuts(root)
        receipt["protected_baselines_after"] = after_baselines
        receipt["protected_shortcuts_after"] = after_shortcuts
        receipt["after_snapshot_passed"] = snapshots_pass(after_baselines, after_shortcuts)
        if not receipt["after_snapshot_passed"]:
            raise RuntimeError("Protected baseline or shortcut verification failed after preview.")

        no_conflicts = not destination_plan["conflicts"]
        receipt["plan_id"] = plan_id
        receipt["approval_phrase"] = plan_core["approval_phrase"]
        receipt["plan_summary"] = plan_core["summary"]
        receipt["phase3c_run"] = selected["name"]
        receipt["phase3c_source_hashes_verified"] = True
        receipt["destination_conflicts"] = len(destination_plan["conflicts"])
        receipt["enough_free_space"] = enough_space

        if no_conflicts and enough_space:
            receipt["state"] = "preview_verified_ready_for_operator_review"
            receipt["verified"] = True
            exit_code = 0
        elif destination_plan["conflicts"]:
            receipt["state"] = "preview_needs_attention_conflicts"
            raise RuntimeError(
                f"{len(destination_plan['conflicts'])} proposed destination conflict(s) require review."
            )
        else:
            receipt["state"] = "preview_needs_attention_space"
            raise RuntimeError("Insufficient free space for the exact add-only plan and safety margin.")

        print("Stage 4/4: preview complete; no live apply performed.", flush=True)
    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        try:
            receipt["protected_baselines_after"] = snapshot_baselines(root)
            receipt["protected_shortcuts_after"] = snapshot_shortcuts(root)
            receipt["after_snapshot_passed"] = snapshots_pass(
                receipt["protected_baselines_after"],
                receipt["protected_shortcuts_after"],
            )
        except Exception as after_exc:
            receipt["after_snapshot_error"] = f"{type(after_exc).__name__}: {after_exc}"
    finally:
        completed = utc_now()
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = round((completed - started).total_seconds(), 2)

        plan = {}
        plan_path = upload_dir / "EXACT_APPLY_PLAN.json"
        if plan_path.is_file():
            plan = json.loads(plan_path.read_text(encoding="utf-8"))

        (upload_dir / "receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (upload_dir / "report.md").write_text(
            make_report(receipt, plan), encoding="utf-8"
        )
        (upload_dir / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this UPLOAD_THIS folder only. "
            "No live apply has occurred.\n",
            encoding="utf-8",
        )

        print()
        print("Phase 3D preview state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload_dir)
        if receipt.get("approval_phrase"):
            print("Approval phrase:", receipt["approval_phrase"])
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("No apply package is present. Operator review is required.")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
