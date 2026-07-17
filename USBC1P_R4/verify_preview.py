from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import traceback
from datetime import datetime, timezone

EXPECTED_LIVE = {
    "core/foxai_web.py": "e0ec7d66bae40d3be67653f47f86cde310e50147924ee48778c4634f3c1d7525",
    "core/server.py": "238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81",
    "core/security_containment.py": "9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24",
    "Config/application_registry.json": "6338e10b813460ee421e4cbf3d9d74fd82d5f24178347e35f4318ef3c4ef9022",
    "Config/fleet_registry.json": "18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6",
    "Config/FoxAI.ini": "677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41",
    "START_FOXAI_WEB_PORTABLE.bat": "dcd4115c1db4e11996b794fae3e40f8efc743868049c04adf93cd0a9c9157705",
    "START_FOXAI_WEB.bat": "286b586363ab9fb323dce6d8f5a7d71383144c10d87fb2137237a4996d49b498",
    "Start FoxAI.bat": "44a3631da95b0db4adc7ea12e358677fbffa591e6d45b5b8208d081b0b354c1b",
    "Start_KayocktheOS.bat": "bfa9ee6cc5ec5bf94852b55a3fe462f935d69744cfa66c52d9196351ecd18620",
    "requirements.txt": "ab55b33a0a31d51be2a81a4f51430dd0b58a9e6c85a884f600b1315b12240447",
    "USB_TREE.txt": "495df4266ca52a3b3542f4f0d15807cd2bd42cb4e7aff4a61874a3df93dc46ee",
    "System/Launchers/launch.py": "1bbb6873f11ebccc8a12ceb9c5c8dfd29087d44c25b987c106dbb606e27252a5",
    "env/python/python314._pth": "e5e2f410d50987906471dc221849354947e5d8a5781234089b133285eced37a8",
    "tests/test_boundary_watch.py": "b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382"
}
EXPECTED_CANDIDATE = {
    "COMMISSION_FOXAI_USB.bat": "3a911a8ea2a09b7c99efe857f911ea0f7dddb74d0d0e096346c957b2fd81f38b",
    "System/Commissioning/commission_usb.py": "cd46b557fef1cb6fabccccff96ae73f4a3fcbd146971f80a0971a1b67f1dc869",
    "00_START_HERE/USB_COMMISSIONING_GUIDE.md": "bc4e722df598d3b2745714473d788be72826b3230badd4f6640ae4bd434b8c30"
}
PROPOSED = [
    "COMMISSION_FOXAI_USB.bat",
    "System/Commissioning/commission_usb.py",
    "00_START_HERE/USB_COMMISSIONING_GUIDE.md",
]


class VerifyError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "core/foxai_web.py").is_file()
            and (candidate / "Engine/llama-server.exe").is_file()
        ):
            return candidate
    raise VerifyError(
        "FOXAI root not found. Extract USBC1P directly inside the FOXAI root."
    )


def snapshot(root: Path) -> dict:
    paths = list(EXPECTED_LIVE) + PROPOSED + [
        "Reports/Commissioning",
        "Config/extension_state.json",
        "tests/test_boundary_watch.py",
    ]
    result = {}
    for relative in paths:
        path = root / relative
        if path.is_file():
            result[relative] = {
                "kind": "file",
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
        elif path.is_dir():
            files = {}
            for item in sorted(path.rglob("*")):
                if item.is_file():
                    key = str(item.relative_to(path)).replace("\\", "/")
                    files[key] = {
                        "sha256": sha256(item),
                        "size": item.stat().st_size,
                    }
            result[relative] = {"kind": "dir", "files": files}
        else:
            result[relative] = {"kind": "missing"}
    return result


def package_manifest(package: Path) -> dict:
    checks = []
    manifest = package / "PACKAGE_SHA256SUMS.txt"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = package / relative
        actual = sha256(path) if path.is_file() else None
        checks.append(
            {
                "path": relative,
                "expected": digest,
                "actual": actual,
                "ok": actual == digest,
            }
        )
    if not checks or not all(item["ok"] for item in checks):
        raise VerifyError("Package manifest failed.")
    return {
        "passed": True,
        "files": checks,
        "apply_capability_present": False,
    }


def live_baselines(root: Path) -> dict:
    checks = []
    for relative, expected in EXPECTED_LIVE.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        checks.append(
            {
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            }
        )
    if not all(item["ok"] for item in checks):
        raise VerifyError("A live audit baseline changed.")
    return {"passed": True, "files": checks}


def candidate_check(package: Path) -> dict:
    checks = []
    for relative, expected in EXPECTED_CANDIDATE.items():
        path = package / "candidate" / relative
        actual = sha256(path) if path.is_file() else None
        checks.append(
            {
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            }
        )

    source_path = (
        package / "candidate/System/Commissioning/commission_usb.py"
    )
    source = source_path.read_text(encoding="utf-8")
    compile(source, str(source_path), "exec")

    bat = (
        package / "candidate/COMMISSION_FOXAI_USB.bat"
    ).read_text(encoding="utf-8", errors="replace").casefold()
    forbidden = [
        "pip install",
        "npm install",
        "powershell",
        "curl ",
        "bitsadmin",
        "del ",
        "rmdir",
        "robocopy",
        "xcopy",
        "copy /y",
        "move ",
    ]
    found = [term for term in forbidden if term in bat]

    static = {
        "no_automatic_install": '"automatic_install": False' in source,
        "no_automatic_repair": '"automatic_repair": False' in source,
        "no_automatic_launch": '"automatic_launch": False' in source,
        "reports_path": "Reports/Commissioning" in source,
        "ready_states": all(
            value in source
            for value in ["READY", "READY_WITH_NOTES", "NEEDS_ATTENTION"]
        ),
        "alternate_shell_warning": "System/Logs/boot.log" in source,
        "safe_folder_repair_deferred": (
            "safe_folder_repair_available_in_this_phase" in source
        ),
    }
    if (
        not all(item["ok"] for item in checks)
        or found
        or not all(static.values())
    ):
        raise VerifyError("Candidate identity or safety contract failed.")
    return {
        "passed": True,
        "files": checks,
        "python_compile": True,
        "bat_forbidden_terms": found,
        "static": static,
    }


def run_live_no_write(package: Path, root: Path) -> dict:
    python = root / "env/python/python.exe"
    script = (
        package / "candidate/System/Commissioning/commission_usb.py"
    )
    if not python.is_file():
        raise VerifyError("Bundled Python is missing.")
    process = subprocess.run(
        [
            str(python),
            str(script),
            "--root",
            str(root),
            "--no-write",
            "--json",
            "--noninteractive",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if process.returncode not in (0, 2):
        raise VerifyError(
            "Live no-write commissioning failed: "
            + process.stderr[-1200:]
        )
    try:
        data = json.loads(process.stdout)
    except Exception as exc:
        raise VerifyError(
            "Live commissioning JSON was invalid: " + str(exc)
        )

    profiles = data.get("profiles") or {}
    models = data.get("models") or {}
    comfyui = data.get("comfyui") or {}
    conditions = {
        "read_only_check": data.get("read_only_check") is True,
        "reports_written": data.get("reports_written") is False,
        "automatic_install": data.get("automatic_install") is False,
        "automatic_repair": data.get("automatic_repair") is False,
        "automatic_launch": data.get("automatic_launch") is False,
        "primary_launcher": (
            data.get("primary_launcher")
            == "START_FOXAI_WEB_PORTABLE.bat"
        ),
        "alternate_shell_nondefault": (
            (profiles.get("KayocktheOS Alternate Shell") or {}).get(
                "default"
            )
            is False
        ),
        "models_present": (models.get("language_model_count") or 0) > 0,
        "projector_separate": "vision_projectors" in models,
        "safe_folder_repair_deferred": (
            comfyui.get("safe_folder_repair_available_in_this_phase")
            is False
        ),
        "overall_status": data.get("overall_status")
        in ("READY", "READY_WITH_NOTES", "NEEDS_ATTENTION"),
    }
    if not all(conditions.values()):
        raise VerifyError("Live no-write commissioning contract failed.")
    return {
        "passed": True,
        "returncode": process.returncode,
        "conditions": conditions,
        "summary": {
            "overall_status": data.get("overall_status"),
            "profiles": {
                key: value.get("status")
                for key, value in profiles.items()
            },
            "language_models": models.get("language_model_count"),
            "projectors": models.get("vision_projector_count"),
            "checkpoints": models.get("creative_checkpoint_count"),
            "embedded_pth": (
                (data.get("runtime") or {}).get("embedded_pth") or {}
            ),
            "venv_config": (
                (data.get("runtime") or {}).get("venv_config") or {}
            ),
        },
    }


def boundary_watch(root: Path) -> dict:
    test = root / "tests/test_boundary_watch.py"
    if not test.is_file():
        raise VerifyError("Boundary Watch test is missing.")
    python = root / "env/python/python.exe"
    runner = (
        "import sys,unittest;"
        "root=sys.argv[1];"
        "tests=sys.argv[2];"
        "sys.path.insert(0,root);"
        "suite=unittest.defaultTestLoader.discover("
        "start_dir=tests,pattern='test_boundary_watch.py');"
        "result=unittest.TextTestRunner(verbosity=2).run(suite);"
        "sys.exit(0 if result.wasSuccessful() else 1)"
    )
    process = subprocess.run(
        [
            str(python),
            "-c",
            runner,
            str(root),
            str(root / "tests"),
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    combined = (process.stdout or "") + "\n" + (process.stderr or "")
    passed = (
        process.returncode == 0
        and "Ran 5 tests" in combined
        and "\nOK" in combined
    )
    result = {
        "passed": passed,
        "tests": 5 if "Ran 5 tests" in combined else None,
        "test_file": str(test),
        "test_sha256": sha256(test),
        "runner": "isolated subprocess with explicit FOXAI root injection",
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }
    if not passed:
        diagnostic = combined[-3000:].strip() or "No test output was produced."
        raise VerifyError(
            "Boundary Watch failed. Test diagnostics: " + diagnostic
        )
    return result


def main() -> int:
    package = Path(__file__).resolve().parent
    root = find_root(package)
    output = package / "LIVE_VERIFY_RECEIPT.json"
    before = snapshot(root)
    receipt = {
        "action": "foxai_usb_commissioning_phase1_exact_preview_r4_verify",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "running",
        "verified": False,
        "root": str(root),
        "live_files_modified": False,
        "candidate_created": True,
        "apply_capability_present": False,
        "changed_files_proposed": PROPOSED,
        "modified_existing_files": [],
        "delete_operations": [],
        "runtime_writes_only_after_later_apply_and_normal_run": [
            "Reports/Commissioning/*"
        ],
        "checks": {},
        "failure": None,
        "protected_changes": [],
    }
    try:
        receipt["checks"]["package_manifest"] = package_manifest(package)
        receipt["checks"]["live_baselines"] = live_baselines(root)
        receipt["checks"]["candidate"] = candidate_check(package)
        receipt["checks"]["live_no_write_commissioning"] = (
            run_live_no_write(package, root)
        )
        receipt["checks"]["boundary_watch"] = boundary_watch(root)

        after = snapshot(root)
        changes = [
            key
            for key in sorted(set(before) | set(after))
            if before.get(key) != after.get(key)
        ]
        if changes:
            raise VerifyError(
                "Read-only verification changed live state: "
                + str(changes)
            )
        receipt.update(
            {
                "state": "exact_preview_verified",
                "verified": True,
                "live_files_modified": False,
                "protected_changes": [],
            }
        )
    except Exception as exc:
        after = snapshot(root)
        changes = [
            key
            for key in sorted(set(before) | set(after))
            if before.get(key) != after.get(key)
        ]
        receipt.update(
            {
                "state": "stopped_fail_closed",
                "verified": not changes,
                "live_files_modified": bool(changes),
                "protected_changes": changes,
                "failure": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            }
        )

    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Live files modified:", receipt["live_files_modified"])
    print("Apply capability present:", receipt["apply_capability_present"])
    print("Receipt:", output)
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    input("Press Enter to close...")
    return 0 if receipt["state"] == "exact_preview_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
