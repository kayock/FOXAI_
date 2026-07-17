from __future__ import annotations

from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
PLAN = json.loads((PACKAGE / "APPLY_PLAN.json").read_text(encoding="utf-8"))
PACKAGE_MANIFEST = PACKAGE / "PACKAGE_SHA256SUMS.txt"

LIVE_RUNTIME_CORE = ROOT / "Runtime/Core"
LIVE_SITE_PACKAGES = LIVE_RUNTIME_CORE / "site-packages"
LIVE_RUNTIME_MANIFEST = LIVE_RUNTIME_CORE / "CORE_RUNTIME_MANIFEST.json"
LIVE_PTH = ROOT / "env/python/python314._pth"
LIVE_LAUNCHER = ROOT / "START_FOXAI_WEB_PORTABLE.bat"

CANDIDATE_PTH = PACKAGE / "candidate/env/python/python314._pth"
CANDIDATE_LAUNCHER = PACKAGE / "candidate/START_FOXAI_WEB_PORTABLE.bat"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_member(name: str) -> bool:
    pure = PurePosixPath(name)
    return (
        bool(name)
        and not pure.is_absolute()
        and ".." not in pure.parts
        and not any(":" in part for part in pure.parts)
    )


def tree_records(root: Path) -> list[dict]:
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            records.append({
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    return records


def tree_digest(records: list[dict]) -> str:
    digest = hashlib.sha256()
    for item in records:
        digest.update(
            (
                f"{item['path']}\0{item['size_bytes']}\0"
                f"{item['sha256']}\n"
            ).encode("utf-8")
        )
    return digest.hexdigest()


def verify_package_manifest() -> dict:
    files = []
    for line in PACKAGE_MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = PACKAGE / relative
        actual = sha256(path) if path.is_file() else None
        item = {
            "path": relative,
            "expected": expected,
            "actual": actual,
            "ok": actual == expected,
        }
        files.append(item)
    if not files or not all(item["ok"] for item in files):
        raise RuntimeError("Apply package manifest failed.")
    return {"passed": True, "files": files}


def verify_live_baselines() -> dict:
    files = []
    for relative, expected in PLAN["live_baselines"].items():
        path = ROOT / relative
        actual = sha256(path) if path.is_file() else None
        item = {
            "path": relative,
            "expected": expected,
            "actual": actual,
            "ok": actual == expected,
        }
        files.append(item)
    if not files or not all(item["ok"] for item in files):
        raise RuntimeError("One or more live baselines changed.")
    if LIVE_RUNTIME_CORE.exists():
        raise RuntimeError(
            "Runtime/Core already exists. Refusing to overwrite an "
            "unexpected live runtime."
        )
    return {
        "passed": True,
        "files": files,
        "runtime_core_absent": True,
    }


def verify_grounding() -> tuple[dict, dict, dict]:
    preview_path = ROOT / PLAN["grounding"]["live_preview_receipt_path"]
    acquisition_path = (
        ROOT / PLAN["grounding"]["live_acquisition_receipt_path"]
    )

    preview_hash = sha256(preview_path) if preview_path.is_file() else None
    acquisition_hash = (
        sha256(acquisition_path) if acquisition_path.is_file() else None
    )
    if preview_hash != PLAN["grounding"]["live_preview_receipt_sha256"]:
        raise RuntimeError("The live exact-preview receipt changed or is missing.")
    if (
        acquisition_hash
        != PLAN["grounding"]["live_acquisition_receipt_sha256"]
    ):
        raise RuntimeError("The live acquisition receipt changed or is missing.")

    preview = json.loads(preview_path.read_text(encoding="utf-8"))
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    if (
        preview.get("state") != "exact_preview_verified"
        or preview.get("verified") is not True
    ):
        raise RuntimeError("The exact-preview receipt contract failed.")
    if (
        acquisition.get("state") != "quarantined_wheelhouse_verified"
        or acquisition.get("verified") is not True
        or len(acquisition.get("wheels", [])) != 12
    ):
        raise RuntimeError("The acquisition receipt contract failed.")

    return (
        {
            "passed": True,
            "preview_path": str(preview_path),
            "preview_sha256": preview_hash,
            "acquisition_path": str(acquisition_path),
            "acquisition_sha256": acquisition_hash,
        },
        preview,
        acquisition,
    )


def reconstruct_candidate(
    acquisition: dict,
    candidate_core: Path,
    preview_created: str,
) -> dict:
    candidate_site = candidate_core / "site-packages"
    candidate_site.mkdir(parents=True, exist_ok=False)
    verified = Path(acquisition["verified_path"])
    seen: dict[str, str] = {}
    wheel_records = []

    for item in acquisition["wheels"]:
        wheel = verified / item["filename"]
        actual = sha256(wheel) if wheel.is_file() else None
        if actual != item["expected_sha256"]:
            raise RuntimeError(f"Verified wheel changed: {item['filename']}")

        record = {
            "filename": item["filename"],
            "sha256": actual,
            "files": 0,
        }
        with zipfile.ZipFile(wheel) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                if not safe_member(info.filename):
                    raise RuntimeError(
                        f"Unsafe wheel member: {item['filename']} :: "
                        f"{info.filename}"
                    )
                relative = PurePosixPath(info.filename).as_posix()
                data = archive.read(info)
                file_hash = hashlib.sha256(data).hexdigest()
                if relative in seen and seen[relative] != file_hash:
                    raise RuntimeError(
                        f"Conflicting wheel member: {relative}"
                    )
                seen[relative] = file_hash
                destination = (
                    candidate_site
                    / Path(*PurePosixPath(relative).parts)
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    destination.write_bytes(data)
                record["files"] += 1
        wheel_records.append(record)

    records = tree_records(candidate_site)
    digest = tree_digest(records)
    expected = PLAN["candidate"]
    if len(records) != expected["site_package_file_count"]:
        raise RuntimeError(
            f"Candidate file count mismatch: {len(records)}"
        )
    if digest != expected["site_package_tree_digest"]:
        raise RuntimeError(f"Candidate tree digest mismatch: {digest}")

    runtime_manifest = {
        "schema": "foxai.portable-core-runtime.v1",
        "created": preview_created,
        "source_acquisition_receipt_sha256": (
            PLAN["grounding"]["live_acquisition_receipt_sha256"]
        ),
        "python": "CPython 3.14.6",
        "platform": "Windows AMD64",
        "package_root": "Runtime/Core/site-packages",
        "user_site_policy": "disabled by primary launcher",
        "wheel_count": 12,
        "file_count": len(records),
        "tree_digest": digest,
        "wheels": wheel_records,
    }
    manifest_path = candidate_core / "CORE_RUNTIME_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(runtime_manifest, indent=2),
        encoding="utf-8",
    )
    manifest_hash = sha256(manifest_path)
    if manifest_hash != expected["runtime_manifest_sha256"]:
        raise RuntimeError(
            f"Runtime manifest hash mismatch: {manifest_hash}"
        )
    return {
        "passed": True,
        "file_count": len(records),
        "tree_digest": digest,
        "runtime_manifest_sha256": manifest_hash,
        "wheels": wheel_records,
    }


def run_candidate_test(candidate_site: Path) -> dict:
    python = ROOT / "env/python/python.exe"
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    process = subprocess.run(
        [
            str(python),
            "-s",
            str(PACKAGE / "post_apply_runtime_test.py"),
            str(ROOT),
            str(candidate_site),
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    result = {
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "passed": False,
    }
    if process.stdout.strip():
        result.update(json.loads(process.stdout))
    if process.returncode != 0 or not result.get("passed"):
        raise RuntimeError(
            "Candidate preflight import test failed: "
            + (process.stderr[-3000:] or process.stdout[-3000:])
        )
    return result

def run_boundary_watch(extra_runtime: Path | None = None) -> dict:
    python = ROOT / "env/python/python.exe"
    prefix = ""
    args = [str(python), "-s", "-c"]
    if extra_runtime is not None:
        prefix = "sys.path.insert(0,sys.argv[1]);"
    runner = (
        "import sys,unittest;"
        + prefix
        + "root=sys.argv[-2];tests=sys.argv[-1];"
        "sys.path.insert(0,root);"
        "suite=unittest.defaultTestLoader.discover("
        "start_dir=tests,pattern='test_boundary_watch.py');"
        "result=unittest.TextTestRunner(verbosity=2).run(suite);"
        "sys.exit(0 if result.wasSuccessful() else 1)"
    )
    args.append(runner)
    if extra_runtime is not None:
        args.append(str(extra_runtime))
    args.extend([str(ROOT), str(ROOT / "tests")])
    process = subprocess.run(
        args,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
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
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }
    if not passed:
        raise RuntimeError("Boundary Watch failed: " + combined[-3000:])
    return result


def run_live_runtime_test() -> dict:
    python = ROOT / "env/python/python.exe"
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    process = subprocess.run(
        [
            str(python),
            "-s",
            str(PACKAGE / "post_apply_runtime_test.py"),
            str(ROOT),
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    result = {
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "passed": False,
    }
    if process.stdout.strip():
        result.update(json.loads(process.stdout))
    if process.returncode != 0 or not result.get("passed"):
        raise RuntimeError(
            "Live portable runtime test failed: "
            + (process.stderr[-3000:] or process.stdout[-3000:])
        )
    return result


def run_commissioning_no_write() -> dict:
    python = ROOT / "env/python/python.exe"
    commissioner = ROOT / "System/Commissioning/commission_usb.py"
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    process = subprocess.run(
        [
            str(python),
            "-s",
            str(commissioner),
            "--root",
            str(ROOT),
            "--no-write",
            "--json",
            "--noninteractive",
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    result = {
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "passed": False,
    }
    if process.returncode != 0:
        raise RuntimeError(
            "No-write commissioning failed: "
            + (process.stderr[-3000:] or process.stdout[-3000:])
        )
    try:
        payload = json.loads(process.stdout)
    except Exception as exc:
        raise RuntimeError(
            f"No-write commissioning JSON failed: {exc}"
        ) from exc

    web = payload.get("profiles", {}).get("FOXAI WebUI", {})
    embedded = payload.get("runtime", {}).get("embedded_python", {})
    modules = embedded.get("modules", {})
    required_origins = {}
    for name in ("psutil", "requests", "casbin"):
        item = modules.get(name, {})
        required_origins[name] = {
            "available": item.get("available"),
            "origin": item.get("origin"),
        }

    runtime_root = LIVE_SITE_PACKAGES.resolve()
    origins_inside = True
    for name in ("psutil", "requests", "casbin"):
        item = required_origins[name]
        origin = item.get("origin")
        try:
            Path(origin).resolve().relative_to(runtime_root)
        except Exception:
            origins_inside = False

    passed = (
        web.get("required_ok") is True
        and modules.get("psutil", {}).get("available") is True
        and modules.get("casbin", {}).get("available") is True
        and origins_inside
    )
    result.update({
        "passed": passed,
        "overall_status": payload.get("overall_status"),
        "webui": web,
        "required_origins": required_origins,
        "origins_inside_runtime": origins_inside,
    })
    if not passed:
        raise RuntimeError(
            "Commissioning did not confirm the portable core runtime."
        )
    return result


def verify_post_apply_files() -> dict:
    site_records = tree_records(LIVE_SITE_PACKAGES)
    site_digest = tree_digest(site_records)
    expected = PLAN["candidate"]
    checks = {
        "site_file_count": len(site_records),
        "site_tree_digest": site_digest,
        "runtime_manifest_sha256": sha256(LIVE_RUNTIME_MANIFEST),
        "pth_sha256": sha256(LIVE_PTH),
        "launcher_sha256": sha256(LIVE_LAUNCHER),
    }
    passed = (
        checks["site_file_count"] == expected["site_package_file_count"]
        and checks["site_tree_digest"] == expected["site_package_tree_digest"]
        and checks["runtime_manifest_sha256"]
        == expected["runtime_manifest_sha256"]
        and checks["pth_sha256"] == expected["pth_sha256"]
        and checks["launcher_sha256"] == expected["launcher_sha256"]
    )
    checks["passed"] = passed
    if not passed:
        raise RuntimeError("Post-apply file verification failed.")
    return checks


def verify_locked_files_after() -> dict:
    approved_modified = {
        "env/python/python314._pth",
        "START_FOXAI_WEB_PORTABLE.bat",
    }
    files = []
    for relative, expected in PLAN["live_baselines"].items():
        if relative in approved_modified:
            continue
        path = ROOT / relative
        actual = sha256(path) if path.is_file() else None
        item = {
            "path": relative,
            "expected": expected,
            "actual": actual,
            "ok": actual == expected,
        }
        files.append(item)
    passed = bool(files) and all(item["ok"] for item in files)
    result = {"passed": passed, "files": files}
    if not passed:
        raise RuntimeError(
            "A non-target locked file changed during apply."
        )
    return result


def copy_backup(source: Path, backup_root: Path) -> Path:
    destination = backup_root / "preapply" / source.relative_to(ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def restore_from_backup(backup_root: Path) -> dict:
    actions = []
    failed_runtime = backup_root / "failed_applied_Runtime_Core"
    if LIVE_RUNTIME_CORE.exists():
        if failed_runtime.exists():
            raise RuntimeError(
                "Rollback preservation path already exists: "
                + str(failed_runtime)
            )
        os.replace(LIVE_RUNTIME_CORE, failed_runtime)
        actions.append({
            "action": "preserve_failed_runtime",
            "from": str(LIVE_RUNTIME_CORE),
            "to": str(failed_runtime),
        })

    for live in (LIVE_PTH, LIVE_LAUNCHER):
        backup = backup_root / "preapply" / live.relative_to(ROOT)
        if backup.is_file():
            temp = live.with_name(live.name + ".rollback_tmp")
            shutil.copy2(backup, temp)
            os.replace(temp, live)
            actions.append({
                "action": "restore_file",
                "path": str(live),
                "from": str(backup),
            })
    return {"attempted": True, "actions": actions}


def write_report(receipt: dict, path: Path) -> None:
    checks = receipt.get("checks", {})
    lines = [
        "# FOXAI Portable Core Runtime Phase 2B3 — Apply Report",
        "",
        f"- Created: `{receipt['created']}`",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Approval verified: **{receipt['approval_verified']}**",
        f"- Backup: `{receipt['backup_path']}`",
        "- Automatic launch: **False**",
        "- Network access: **False**",
        "- Deletes: **None**",
        "",
        "## Applied",
        "",
        "- Added `Runtime/Core/site-packages` from 12 verified wheels.",
        "- Added `Runtime/Core/CORE_RUNTIME_MANIFEST.json`.",
        "- Updated `env/python/python314._pth`.",
        "- Updated `START_FOXAI_WEB_PORTABLE.bat`.",
        "",
        "## Verification",
        "",
        f"- Candidate preflight: **{bool(checks.get('candidate_preflight', {}).get('passed'))}**",
        f"- Candidate Boundary Watch: **{bool(checks.get('candidate_boundary_watch', {}).get('passed'))}**",
        f"- Live file verification: **{bool(checks.get('post_apply_files', {}).get('passed'))}**",
        f"- Live portable imports: **{bool(checks.get('live_runtime', {}).get('passed'))}**",
        f"- Live Boundary Watch: **{bool(checks.get('live_boundary_watch', {}).get('passed'))}**",
        f"- No-write commissioning: **{bool(checks.get('commissioning', {}).get('passed'))}**",
        "",
        "## Safety",
        "",
        "No source, model, fleet registry, Desktop runtime, ComfyUI runtime,",
        "alternate shell, or Bridge file was changed. On a failed verification,",
        "the attempted Runtime/Core tree is moved into the backup and both",
        "modified files are restored.",
    ]
    if receipt.get("failure"):
        lines += [
            "",
            "## Failure",
            "",
            f"- `{receipt['failure']['type']}: {receipt['failure']['message']}`",
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", required=True)
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = (
        ROOT / "Backups/SecurityMilestone" / f"PR2B3_{stamp}"
    )
    report_root = (
        ROOT / "Reports/PortableRuntime" / f"PR2B3_APPLY_{stamp}"
    )
    backup_root.mkdir(parents=True, exist_ok=False)
    report_root.mkdir(parents=True, exist_ok=False)

    receipt = {
        "action": "foxai_portable_core_runtime_phase2b3_apply",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "root": str(ROOT),
        "approval_phrase_expected": PLAN["operator_approval_phrase"],
        "approval_verified": (
            args.approval == PLAN["operator_approval_phrase"]
        ),
        "backup_path": str(backup_root),
        "report_path": str(report_root),
        "automatic_launch": False,
        "network_access": False,
        "pip_install": False,
        "source_or_security_modified": False,
        "model_modified": False,
        "fleet_registry_modified": False,
        "desktop_or_comfyui_modified": False,
        "delete_operations": [],
        "checks": {},
        "rollback": {"attempted": False, "actions": []},
        "failure": None,
    }

    live_changes_started = False
    candidate_core = backup_root / "candidate/Runtime/Core"

    try:
        if not receipt["approval_verified"]:
            raise RuntimeError("The operator approval phrase did not match.")

        receipt["checks"]["package_manifest"] = verify_package_manifest()
        receipt["checks"]["live_baselines_before"] = verify_live_baselines()
        grounding, preview, acquisition = verify_grounding()
        receipt["checks"]["grounding"] = grounding

        if sha256(CANDIDATE_PTH) != PLAN["candidate"]["pth_sha256"]:
            raise RuntimeError("Candidate _pth hash failed.")
        if (
            sha256(CANDIDATE_LAUNCHER)
            != PLAN["candidate"]["launcher_sha256"]
        ):
            raise RuntimeError("Candidate launcher hash failed.")

        candidate_tree = reconstruct_candidate(
            acquisition,
            candidate_core,
            preview_created=preview["created"],
        )
        receipt["checks"]["candidate_tree"] = candidate_tree
        receipt["checks"]["candidate_preflight"] = run_candidate_test(
            candidate_core / "site-packages"
        )
        receipt["checks"]["candidate_boundary_watch"] = (
            run_boundary_watch(candidate_core / "site-packages")
        )

        copy_backup(LIVE_PTH, backup_root)
        copy_backup(LIVE_LAUNCHER, backup_root)
        (backup_root / "PREAPPLY_STATE.json").write_text(
            json.dumps({
                "runtime_core_existed": False,
                "pth_sha256": sha256(LIVE_PTH),
                "launcher_sha256": sha256(LIVE_LAUNCHER),
                "live_baselines": PLAN["live_baselines"],
            }, indent=2),
            encoding="utf-8",
        )

        LIVE_RUNTIME_CORE.parent.mkdir(parents=True, exist_ok=True)
        os.replace(candidate_core, LIVE_RUNTIME_CORE)
        live_changes_started = True

        pth_temp = LIVE_PTH.with_name(LIVE_PTH.name + ".pr2b3_tmp")
        launcher_temp = LIVE_LAUNCHER.with_name(
            LIVE_LAUNCHER.name + ".pr2b3_tmp"
        )
        shutil.copy2(CANDIDATE_PTH, pth_temp)
        shutil.copy2(CANDIDATE_LAUNCHER, launcher_temp)
        os.replace(pth_temp, LIVE_PTH)
        os.replace(launcher_temp, LIVE_LAUNCHER)

        receipt["checks"]["post_apply_files"] = verify_post_apply_files()
        receipt["checks"]["live_runtime"] = run_live_runtime_test()
        receipt["checks"]["live_boundary_watch"] = run_boundary_watch()
        receipt["checks"]["commissioning"] = run_commissioning_no_write()

        receipt["checks"]["locked_files_after"] = (
            verify_locked_files_after()
        )

        receipt["state"] = "applied_verified"
        receipt["verified"] = True
    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if live_changes_started:
            try:
                receipt["rollback"] = restore_from_backup(backup_root)
                receipt["state"] = "rolled_back_fail_closed"
            except Exception as rollback_exc:
                receipt["rollback"] = {
                    "attempted": True,
                    "actions": receipt["rollback"].get("actions", []),
                    "failure": {
                        "type": type(rollback_exc).__name__,
                        "message": str(rollback_exc),
                    },
                }
                receipt["state"] = "rollback_needs_attention"

    receipt_path = report_root / "APPLY_RECEIPT.json"
    report_path = report_root / "APPLY_REPORT.md"
    receipt_path.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )
    write_report(receipt, report_path)

    print("=" * 72)
    print("FOXAI PORTABLE CORE RUNTIME PHASE 2B3 — GUARDED APPLY")
    print("=" * 72)
    print(f"State: {receipt['state']}")
    print(f"Verified: {receipt['verified']}")
    print(f"Approval verified: {receipt['approval_verified']}")
    print(f"Backup: {backup_root}")
    print(f"Report: {report_root}")
    print("Automatic launch: False")
    print("Deletes: None")
    if receipt["failure"]:
        print(f"Failure: {receipt['failure']['message']}")
    return 0 if receipt["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
