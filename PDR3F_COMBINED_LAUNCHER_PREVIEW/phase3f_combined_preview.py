from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import traceback

EXPECTED_BASELINES = {'Config/fleet_registry.json': '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6', 'Config/model_sources.json': 'c17eb3b8b6c93734f7e117522213c95af6c105fe26400d0560768fe586e21c91', 'Launch FOXAI Workshop.bat': '7f974eeeaa66c6fd331b6b3e8cb5f312d25a410761817ad35408ccb47acd4480', 'START_FOXAI_WEB_PORTABLE.bat': '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1', 'core/engineer_agent.py': 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19', 'core/foxai_web.py': 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7', 'core/model_sources.py': 'e00a861265eff8826c4d7eeb89b3765e719b88f349811a2e608525d8a3f91ea2', 'core/security_containment.py': '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24', 'core/server.py': '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81', 'core/service_registry.py': 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b', 'env/python/python314._pth': '48d77ccee161647ef7053cb563d3b37b4053938d5ad92ae64ccedc2165bcd42d', 'tests/test_boundary_watch.py': 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382', 'tests/test_model_sources.py': 'ec94f8b8d90d36f05385db74400dd99b436cd4e488b1b517bcb77442a16fc6f2', 'ui/main_window.py': '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3'}
EXPECTED_SHORTCUTS = {'desktop': {'filename': 'Z:\\Launch FOXAI Workshop.bat - Shortcut.lnk', 'sha256': '2a41fab836312e95e40d5404bc379b050f31b7cd61bd1ac26bb22ce902aeae02'}, 'web': {'filename': 'Z:\\START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk', 'sha256': 'af0f79cfc583c51c4108cb2c1baa86634bf427e2eb881c64ed51a5994f2e40dd'}}
EXPECTED_EVIDENCE_HASHES = {'receipt.json': '5923eb9945135d87a03a33c7d6e12c7c9fe079acbcb8c84def0a65005138a430', 'launch_chain.json': '2ff574b6c44a3f8a0dfb044163014dc597060ac1afd49da862a6df93316b1060', 'shortcut_details.json': '8f8b8ae904a5e7d3495d9e96619a224e46dbe9b3814b5cf926a31c93544d2cb7'}

EXPECTED_FILES = {
    "Launch FOXAI Workshop.bat": "7f974eeeaa66c6fd331b6b3e8cb5f312d25a410761817ad35408ccb47acd4480",
    "START_FOXAI_DESKTOP_PORTABLE.bat": "89e906d805f99392b4ecc2ea85aa688577517a26e577de3542159a1f5eaf046c",
    "ComfyUI/main.py": "d2580be49e7abb3218b1e7056844b2c72a2e7d8711268849429ad3b418c38bc9",
    "foxai.py": "423bb098170dbaad2b96c6b07e31beee171904d286b8364457ce6357551c33d0",
    "System/PortableRuntime/verify_desktop_runtime.py": "3743657d9249c00cf11f891b3e703743eca206301f9a48807b17d568a440939e",
}
DESTINATION_NAME = "START_FOXAI_WORKSHOP_PORTABLE.bat"

def utc_now():
    return dt.datetime.now(dt.timezone.utc)

def sha256_file(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def canonical_hash(value):
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def snapshot_protected(root: Path):
    baselines = []
    for relative, expected in sorted(EXPECTED_BASELINES.items()):
        path = root / Path(relative)
        actual = sha256_file(path)
        baselines.append({
            "path": relative,
            "exists": path.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })

    usb_root = Path(root.anchor)
    shortcuts = {}
    for key, item in EXPECTED_SHORTCUTS.items():
        path = usb_root / item["filename"]
        actual = sha256_file(path)
        shortcuts[key] = {
            "path": str(path),
            "exists": path.is_file(),
            "expected_sha256": item["sha256"],
            "actual_sha256": actual,
            "matches_expected": actual == item["sha256"],
        }

    return {
        "baselines": baselines,
        "shortcuts": shortcuts,
        "passed": (
            all(item["matches_expected"] for item in baselines)
            and all(item["matches_expected"] for item in shortcuts.values())
        ),
    }

def verify_bundled_evidence(bundle: Path):
    results = {}
    passed = True
    evidence = bundle / "DISCOVERY_EVIDENCE"
    for name, expected in EXPECTED_EVIDENCE_HASHES.items():
        path = evidence / name
        actual = sha256_file(path)
        ok = actual == expected
        results[name] = {
            "path": str(path),
            "exists": path.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": ok,
        }
        passed = passed and ok

    if passed:
        receipt = json.loads(
            (evidence / "receipt.json").read_text(encoding="utf-8")
        )
        chain = json.loads(
            (evidence / "launch_chain.json").read_text(encoding="utf-8")
        )
        shortcut = json.loads(
            (evidence / "shortcut_details.json").read_text(encoding="utf-8-sig")
        )
        content_checks = {
            "discovery_state": (
                receipt.get("state")
                == "discovery_verified_ready_for_combined_launcher_design"
            ),
            "discovery_verified": receipt.get("verified") is True,
            "protected_before": receipt.get("protected_before", {}).get("passed") is True,
            "protected_after": receipt.get("protected_after", {}).get("passed") is True,
            "chain_not_truncated": chain.get("truncated") is False,
            "chain_no_unresolved": not chain.get("unresolved_references"),
            "shortcut_target": any(
                item.get("name") == "Launch FOXAI Workshop.bat - Shortcut.lnk"
                and item.get("target_path", "").lower().endswith(
                    r"\foxai\launch foxai workshop.bat"
                )
                and item.get("working_directory", "").lower().endswith(r"\foxai")
                for item in shortcut.get("items") or []
            ),
        }
        passed = passed and all(content_checks.values())
    else:
        content_checks = {}

    return {
        "files": results,
        "content_checks": content_checks,
        "passed": passed,
    }

def verify_exact_files(root: Path):
    results = []
    for relative, expected in EXPECTED_FILES.items():
        path = root / Path(relative)
        actual = sha256_file(path)
        results.append({
            "path": relative,
            "exists": path.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })
    return {
        "files": results,
        "passed": all(item["matches_expected"] for item in results),
    }

def validate_launcher_text(text: str):
    lower = text.lower()
    checks = {
        "separate_destination_name": DESTINATION_NAME.lower() not in {
            "launch foxai workshop.bat",
            "start_foxai_desktop_portable.bat",
        },
        "checks_portable_launcher": (
            r"start_foxai_desktop_portable.bat" in lower
        ),
        "checks_comfy_main": r"comfyui\main.py" in lower,
        "requires_host_python_path": "where python.exe" in lower,
        "verifies_usb_runtime_first": (
            r"verify_desktop_runtime.py" in lower
        ),
        "uses_proven_comfy_command": (
            "python.exe main.py --cpu" in lower
        ),
        "clears_pythonhome_for_comfy": (
            "set pythonhome=" in lower
        ),
        "clears_pythonpath_for_comfy": (
            "set pythonpath=" in lower
        ),
        "preserves_eight_second_wait": (
            "timeout /t 8 /nobreak" in lower
        ),
        "calls_verified_portable_launcher": (
            'call "%root%start_foxai_desktop_portable.bat"' in lower
        ),
        "comfy_precedes_foxai": (
            lower.find("python.exe main.py --cpu")
            < lower.find('call "%root%start_foxai_desktop_portable.bat"')
        ),
        "no_existing_launcher_write": (
            ">launch foxai workshop.bat" not in lower
            and ">start_foxai_desktop_portable.bat" not in lower
        ),
        "no_pip": "pip install" not in lower,
        "no_download_tools": all(
            token not in lower
            for token in ("curl ", "wget ", "invoke-webrequest", "http://", "https://")
        ),
    }
    return {"checks": checks, "passed": all(checks.values())}

def make_report(receipt, plan):
    lines = [
        "# FOXAI Portable Desktop Runtime Phase 3F-P",
        "## Combined Portable Workshop Launcher Preview",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        "- Preview only: **True**",
        "- Live files modified: **False**",
        "- Shortcuts changed: **False**",
        "- FOXAI launched: **False**",
        "- ComfyUI launched: **False**",
        "",
    ]

    if plan:
        lines += [
            "## Proposed new file",
            "",
            f"- Destination: `{plan['action']['destination']}`",
            f"- Status: **{plan['action']['destination_status']}**",
            f"- Size: **{plan['action']['size_bytes']} bytes**",
            f"- SHA-256: `{plan['action']['expected_sha256']}`",
            "",
            "## Preserved startup behavior",
            "",
            "- Verifies the USB-owned Desktop runtime before starting services.",
            "- Starts ComfyUI first with the existing proven host command: `python.exe main.py --cpu`.",
            "- Clears portable Python variables from the ComfyUI process.",
            "- Waits eight seconds.",
            "- Starts FOXAI through the already-verified portable Desktop launcher.",
            "- Leaves the existing shortcut and both existing launchers unchanged.",
            "",
            "## Host-Python observation",
            "",
            f"- Resolved `python.exe`: `{plan['host_python']['resolved_path']}`",
            "",
            "## Approval",
            "",
            f"- Plan ID: `{plan['plan_id']}`",
            f"- Exact approval phrase: **`{plan['approval_phrase']}`**",
            "",
            "**No apply capability is included.**",
        ]
    else:
        lines += [
            "## Stop information",
            "",
            f"- Failure: `{(receipt.get('failure') or {}).get('message')}`",
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
    output = bundle / "PREVIEW_OUTPUT" / started.strftime("%Y%m%dT%H%M%SZ")
    upload = output / "UPLOAD_THIS"
    proposed = upload / "PROPOSED_FILES_NOT_APPLIED"
    proposed.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_pdr_phase3f_combined_portable_workshop_launcher_preview",
        "created": started.isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "preview_only": True,
        "apply_capability_present": False,
        "live_apply_performed": False,
        "live_files_modified": False,
        "shortcut_changes": False,
        "existing_launcher_changes": False,
        "source_changes": False,
        "network_access": False,
        "desktop_gui_launched": False,
        "comfyui_launched": False,
        "browser_launched": False,
        "recursive_drive_scan": False,
        "phase3f_apply_authorized": False,
        "writes_limited_to": str(output),
    }
    plan = None
    exit_code = 1

    try:
        evidence = verify_bundled_evidence(bundle)
        receipt["discovery_evidence"] = evidence
        if not evidence["passed"]:
            raise RuntimeError("Bundled Phase 3F discovery evidence failed verification.")

        protected_before = snapshot_protected(root)
        receipt["protected_before"] = protected_before
        if not protected_before["passed"]:
            raise RuntimeError("Protected FOXAI state failed before combined preview.")

        exact_files = verify_exact_files(root)
        receipt["exact_required_files"] = exact_files
        if not exact_files["passed"]:
            raise RuntimeError("One or more exact launcher/runtime files changed after discovery.")

        host_python = shutil.which("python.exe") or shutil.which("python")
        receipt["host_python_probe"] = {
            "method": "shutil.which; no host Python process launched",
            "resolved_path": host_python,
            "exists": bool(host_python and Path(host_python).is_file()),
        }
        if not host_python or not Path(host_python).is_file():
            raise RuntimeError(
                "The existing ComfyUI `python` command is not resolvable on this machine."
            )

        template = (
            bundle / "START_FOXAI_WORKSHOP_PORTABLE.template.bat"
        ).read_text(encoding="ascii")
        text_validation = validate_launcher_text(template)
        receipt["launcher_text_validation"] = text_validation
        if not text_validation["passed"]:
            failed = [
                name for name, ok in text_validation["checks"].items() if not ok
            ]
            raise RuntimeError(
                "Combined launcher text validation failed: " + ", ".join(failed)
            )

        proposed_path = proposed / DESTINATION_NAME
        proposed_path.write_text(template, encoding="ascii", newline="\r\n")
        proposed_hash = sha256_file(proposed_path)
        destination = root / DESTINATION_NAME

        if not destination.exists():
            status = "ADD"
            destination_hash = None
        elif destination.is_file() and sha256_file(destination) == proposed_hash:
            status = "ALREADY_MATCHES"
            destination_hash = proposed_hash
        elif destination.is_file():
            status = "CONFLICT_DIFFERENT_FILE"
            destination_hash = sha256_file(destination)
        else:
            status = "CONFLICT_NON_FILE"
            destination_hash = None

        if status.startswith("CONFLICT"):
            raise RuntimeError(f"Combined launcher destination conflict: {status}")

        action = {
            "kind": "combined_portable_workshop_launcher",
            "source": str(proposed_path),
            "destination": str(destination),
            "destination_status": status,
            "destination_sha256": destination_hash,
            "size_bytes": proposed_path.stat().st_size,
            "expected_sha256": proposed_hash,
        }

        plan_core = {
            "format": "foxai_pdr_phase3f_combined_launcher_plan_v1",
            "created": utc_now().isoformat(),
            "foxai_root": str(root),
            "action": action,
            "host_python": {
                "selection_method": "PATH resolution matching existing launcher command",
                "command": "python.exe main.py --cpu",
                "resolved_path": str(Path(host_python).resolve()),
                "portable": False,
                "reason": (
                    "ComfyUI/torch remains outside the Desktop runtime; preserve the "
                    "existing proven CPU backend command for this machine."
                ),
            },
            "portable_foxai_launcher": {
                "path": str(root / "START_FOXAI_DESKTOP_PORTABLE.bat"),
                "sha256": EXPECTED_FILES["START_FOXAI_DESKTOP_PORTABLE.bat"],
            },
            "startup_order": [
                "preflight exact required paths and host python command",
                "verify USB-owned Desktop runtime",
                "start ComfyUI CPU using host PATH python",
                "wait 8 seconds",
                "start FOXAI through verified portable Desktop launcher",
            ],
            "existing_files_to_modify": [],
            "files_to_delete": [],
            "shortcuts_to_change": [],
            "existing_launchers_to_change": [],
            "test_after_apply": {
                "run": str(destination),
                "expected": (
                    "ComfyUI CPU starts using the same host-Python method as the "
                    "working shortcut, then FOXAI opens through the USB-owned "
                    "Desktop runtime."
                ),
            },
        }
        plan_id = canonical_hash(plan_core)
        plan_core["plan_id"] = plan_id
        plan_core["approval_phrase"] = (
            f"APPROVE PDR3F {plan_id[:12].upper()}"
        )
        plan = plan_core

        (upload / "EXACT_COMBINED_LAUNCHER_PLAN.json").write_text(
            json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        protected_after = snapshot_protected(root)
        receipt["protected_after"] = protected_after
        if not protected_after["passed"]:
            raise RuntimeError("Protected FOXAI state failed after combined preview.")

        exact_files_after = verify_exact_files(root)
        receipt["exact_required_files_after"] = exact_files_after
        if not exact_files_after["passed"]:
            raise RuntimeError("Required launcher/runtime files changed during preview.")

        receipt["state"] = (
            "combined_launcher_preview_verified_ready_for_operator_review"
        )
        receipt["verified"] = True
        receipt["plan_id"] = plan_id
        receipt["approval_phrase"] = plan["approval_phrase"]
        exit_code = 0

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        try:
            receipt["protected_after"] = snapshot_protected(root)
        except Exception as final_exc:
            receipt["protected_after_error"] = (
                f"{type(final_exc).__name__}: {final_exc}"
            )
    finally:
        completed = utc_now()
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = round((completed - started).total_seconds(), 2)

        (upload / "receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (upload / "report.md").write_text(
            make_report(receipt, plan), encoding="utf-8"
        )
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this UPLOAD_THIS folder only. "
            "No combined launcher was applied or run.\n",
            encoding="utf-8",
        )

        print()
        print("Phase 3F-P preview state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("approval_phrase"):
            print("Approval phrase:", receipt["approval_phrase"])
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("No apply capability is present. Operator review is required.")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
