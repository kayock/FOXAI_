from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import traceback

EXPECTED_BASELINES = {'Config/fleet_registry.json': '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6', 'Config/model_sources.json': 'c17eb3b8b6c93734f7e117522213c95af6c105fe26400d0560768fe586e21c91', 'core/engineer_agent.py': 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19', 'core/foxai_web.py': 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7', 'core/model_sources.py': 'e00a861265eff8826c4d7eeb89b3765e719b88f349811a2e608525d8a3f91ea2', 'core/security_containment.py': '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24', 'core/server.py': '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81', 'core/service_registry.py': 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b', 'env/python/python314._pth': '48d77ccee161647ef7053cb563d3b37b4053938d5ad92ae64ccedc2165bcd42d', 'Launch FOXAI Workshop.bat': '7f974eeeaa66c6fd331b6b3e8cb5f312d25a410761817ad35408ccb47acd4480', 'START_FOXAI_WEB_PORTABLE.bat': '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1', 'tests/test_boundary_watch.py': 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382', 'tests/test_model_sources.py': 'ec94f8b8d90d36f05385db74400dd99b436cd4e488b1b517bcb77442a16fc6f2', 'ui/main_window.py': '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3'}
EXPECTED_SHORTCUTS = {'desktop': {'filename': 'Launch FOXAI Workshop.bat - Shortcut.lnk', 'sha256': '2a41fab836312e95e40d5404bc379b050f31b7cd61bd1ac26bb22ce902aeae02'}, 'web': {'filename': 'START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk', 'sha256': 'af0f79cfc583c51c4108cb2c1baa86634bf427e2eb881c64ed51a5994f2e40dd'}}
EXPECTED_DIAGNOSTIC_NAME = "desktop_runtime_diagnostic_20260717T010709Z.json"
EXPECTED_DIAGNOSTIC_SHA256 = "66a517da70407b60d2f03605545c325e1194e664a5083213ceb7e53c6306a12a"

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

def verify_diagnostic(root: Path):
    path = root / "Logs" / "PortableRuntime" / EXPECTED_DIAGNOSTIC_NAME
    actual_hash = sha256_file(path)
    result = {
        "path": str(path),
        "exists": path.is_file(),
        "expected_sha256": EXPECTED_DIAGNOSTIC_SHA256,
        "actual_sha256": actual_hash,
        "hash_matches": actual_hash == EXPECTED_DIAGNOSTIC_SHA256,
        "content_checks": {},
        "passed": False,
    }
    if not path.is_file():
        return result

    data = json.loads(path.read_text(encoding="utf-8"))
    checks = data.get("checks") or {}
    modules = data.get("modules") or {}

    result["content_checks"] = {
        "action": data.get("action") == "foxai_portable_desktop_runtime_diagnostic",
        "root": os.path.normcase(data.get("root", "")) == os.path.normcase(str(root)),
        "verified": data.get("verified") is True,
        "all_checks_true": bool(checks) and all(checks.values()),
        "all_modules_available": bool(modules) and all(
            item.get("available") for item in modules.values()
        ),
        "all_module_origins_correct": bool(modules) and all(
            item.get("origin_ok") for item in modules.values()
        ),
        "foxai_not_launched": data.get("foxai_launched") is False,
        "comfyui_not_launched": data.get("comfyui_launched") is False,
    }
    result["passed"] = (
        result["hash_matches"]
        and all(result["content_checks"].values())
    )
    return result

def validate_launcher_text(text: str):
    lower = text.lower()
    checks = {
        "uses_usb_desktop_python": r"runtime\desktop\python\python.exe" in lower,
        "disables_user_site": 'set "pythonnousersite=1"' in lower,
        "disables_bytecode_writes": 'set "pythondontwritebytecode=1"' in lower,
        "sets_pythonhome": 'set "pythonhome=%root%runtime\\desktop\\python"' in lower,
        "sets_pythonpath": (
            r"runtime\desktop\site-packages" in lower
            and r"runtime\core\site-packages" in lower
        ),
        "runs_runtime_verifier_first": (
            r"system\portableruntime\verify_desktop_runtime.py" in lower
        ),
        "launches_foxai_entrypoint": r"%root%foxai.py" in lower,
        "no_comfyui": "comfyui" not in lower,
        "no_pip": "pip install" not in lower and " pip " not in lower,
        "no_network_tools": all(
            token not in lower
            for token in ("curl ", "wget ", "invoke-webrequest", "http://", "https://")
        ),
        "no_system_python_fallback": (
            "\npython " not in lower
            and "\npython.exe " not in lower
            and "\npy " not in lower
        ),
    }

    verifier_pos = lower.find("verify_desktop_runtime.py")
    foxai_pos = lower.find(r"%root%foxai.py")
    checks["verifier_precedes_launch"] = (
        verifier_pos >= 0 and foxai_pos > verifier_pos
    )
    return {"checks": checks, "passed": all(checks.values())}

def destination_status(path: Path, expected_hash: str):
    if not path.exists():
        return {"status": "ADD", "actual_sha256": None}
    if not path.is_file():
        return {"status": "CONFLICT_NON_FILE", "actual_sha256": None}
    actual = sha256_file(path)
    if actual == expected_hash:
        return {"status": "ALREADY_MATCHES", "actual_sha256": actual}
    return {"status": "CONFLICT_DIFFERENT_FILE", "actual_sha256": actual}

def make_report(receipt, plan):
    lines = [
        "# FOXAI Portable Desktop Runtime Phase 3E-P",
        "## Separate Portable Launcher Preview",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        "- Preview only: **True**",
        "- Live files modified: **False**",
        "- FOXAI launched: **False**",
        "- ComfyUI launched: **False**",
        "",
    ]

    if plan:
        lines += [
            "## Exact proposed addition",
            "",
            f"- Destination: `{plan['action']['destination']}`",
            f"- Status: **{plan['action']['destination_status']}**",
            f"- Size: **{plan['action']['size_bytes']} bytes**",
            f"- SHA-256: `{plan['action']['expected_sha256']}`",
            "",
            "## Launcher behavior",
            "",
            "- Uses only `Runtime\\Desktop\\python\\python.exe`.",
            "- Runs the existing portable-runtime verifier before FOXAI.",
            "- Stops without launching FOXAI if verification fails.",
            "- Launches `foxai.py` directly.",
            "- Does not start ComfyUI.",
            "- Does not use host Python or user-site packages.",
            "",
            "## Explicitly unchanged",
            "",
            "- Both USB-root shortcuts",
            "- `Launch FOXAI Workshop.bat`",
            "- `START_FOXAI_WEB_PORTABLE.bat`",
            "- FOXAI source and protected baselines",
            "",
            "## Approval",
            "",
            f"- Plan ID: `{plan['plan_id']}`",
            f"- Exact approval phrase: **`{plan['approval_phrase']}`**",
            "",
            "**No apply package is included.**",
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
        "action": "foxai_pdr_phase3e_separate_launcher_preview",
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
        "recursive_drive_scan": False,
        "phase3e_apply_authorized": False,
        "writes_limited_to": str(output),
    }
    plan = None
    exit_code = 1

    try:
        protected_before = snapshot_protected(root)
        receipt["protected_before"] = protected_before
        if not protected_before["passed"]:
            raise RuntimeError("Protected FOXAI state failed before launcher preview.")

        diagnostic = verify_diagnostic(root)
        receipt["diagnostic_evidence"] = diagnostic
        if not diagnostic["passed"]:
            raise RuntimeError("The exact passed portable-runtime diagnostic could not be verified.")

        required_paths = [
            root / "Runtime" / "Desktop" / "python" / "python.exe",
            root / "Runtime" / "Desktop" / "site-packages",
            root / "Runtime" / "Core" / "site-packages",
            root / "System" / "PortableRuntime" / "verify_desktop_runtime.py",
            root / "foxai.py",
        ]
        missing = [str(path) for path in required_paths if not path.exists()]
        receipt["required_paths"] = {
            "checked": [str(path) for path in required_paths],
            "missing": missing,
            "passed": not missing,
        }
        if missing:
            raise RuntimeError("Required portable launcher path(s) are missing.")

        template = (bundle / "START_FOXAI_DESKTOP_PORTABLE.template.bat").read_text(
            encoding="ascii"
        )
        validation = validate_launcher_text(template)
        receipt["launcher_text_validation"] = validation
        if not validation["passed"]:
            failed = [name for name, ok in validation["checks"].items() if not ok]
            raise RuntimeError("Launcher text validation failed: " + ", ".join(failed))

        proposed_path = proposed / "START_FOXAI_DESKTOP_PORTABLE.bat"
        proposed_path.write_text(template, encoding="ascii", newline="\r\n")
        proposed_hash = sha256_file(proposed_path)
        destination = root / "START_FOXAI_DESKTOP_PORTABLE.bat"
        status = destination_status(destination, proposed_hash)

        if status["status"].startswith("CONFLICT"):
            raise RuntimeError(
                f"Proposed launcher destination conflict: {status['status']}"
            )

        foxai_hash_before = sha256_file(root / "foxai.py")
        action = {
            "kind": "portable_desktop_launcher",
            "source": str(proposed_path),
            "destination": str(destination),
            "destination_status": status["status"],
            "destination_sha256": status["actual_sha256"],
            "size_bytes": proposed_path.stat().st_size,
            "expected_sha256": proposed_hash,
        }

        plan_core = {
            "format": "foxai_pdr_phase3e_launcher_plan_v1",
            "created": utc_now().isoformat(),
            "foxai_root": str(root),
            "diagnostic_name": EXPECTED_DIAGNOSTIC_NAME,
            "diagnostic_sha256": EXPECTED_DIAGNOSTIC_SHA256,
            "action": action,
            "existing_files_to_modify": [],
            "files_to_delete": [],
            "shortcuts_to_change": [],
            "existing_launchers_to_change": [],
            "foxai_entrypoint_sha256": foxai_hash_before,
            "test_after_apply": {
                "run": str(destination),
                "expected": (
                    "Portable runtime verifier passes, then FOXAI Desktop opens "
                    "without the launcher starting ComfyUI."
                ),
            },
        }
        plan_id = canonical_hash(plan_core)
        plan_core["plan_id"] = plan_id
        plan_core["approval_phrase"] = f"APPROVE PDR3E {plan_id[:12].upper()}"
        plan = plan_core

        (upload / "EXACT_LAUNCHER_PLAN.json").write_text(
            json.dumps(plan, indent=2), encoding="utf-8"
        )

        protected_after = snapshot_protected(root)
        receipt["protected_after"] = protected_after
        if not protected_after["passed"]:
            raise RuntimeError("Protected FOXAI state failed after launcher preview.")

        foxai_hash_after = sha256_file(root / "foxai.py")
        receipt["foxai_entrypoint"] = {
            "path": str(root / "foxai.py"),
            "sha256_before": foxai_hash_before,
            "sha256_after": foxai_hash_after,
            "unchanged": foxai_hash_before == foxai_hash_after,
        }
        if foxai_hash_before != foxai_hash_after:
            raise RuntimeError("foxai.py changed during preview.")

        receipt["state"] = "launcher_preview_verified_ready_for_operator_review"
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
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        (upload / "report.md").write_text(
            make_report(receipt, plan), encoding="utf-8"
        )
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this UPLOAD_THIS folder only. "
            "No launcher has been applied or run.\n",
            encoding="utf-8",
        )

        print()
        print("Phase 3E preview state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("approval_phrase"):
            print("Approval phrase:", receipt["approval_phrase"])
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("No apply package is present. Operator review is required.")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
