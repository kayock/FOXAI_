#!/usr/bin/env python3
"""FOXAI USB C3E — Exact Isolated Installation and Transactional Commit.

C3E is the first approved write stage. It consumes only the exact reviewed C3D
lock and exact C3C wheelhouse, installs offline into one new adjacent transaction
folder, verifies the result with the protected portable Python, and commits by
same-volume rename only after all pre-commit gates pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ACTION = "foxai_usbc3e_exact_isolated_installation"
SUCCESS = "C3E_INSTALLED_VERIFIED_COMMITTED_READY_FOR_C3F_REVIEW"
BLOCKED_STAGING = "C3E_BLOCKED_FAIL_CLOSED_STAGING_PRESERVED"
BLOCKED_PARENT = "C3E_BLOCKED_FAIL_CLOSED_RUNTIME_PARENT_PRESERVED"
BLOCKED_PREWRITE = "C3E_BLOCKED_FAIL_CLOSED_NO_RUNTIME_WRITE"
BLOCKED_COMMITTED = "C3E_COMMITTED_FAIL_CLOSED_REVIEW_REQUIRED"
EXPECTED_PORTABLE_VERSION = (3, 14, 6)
EXPECTED_HOST_VERSION = (3, 14, 6)
EXPECTED_HOST_PIP = "26.1.2"
EXPECTED_HOST_PYTHON = Path(r"C:\Python314\python.exe")
EXPECTED_HOST_HASH = "03168c01b7b7491423350e82c26fee71f35b43694d1319d3c668bda6903a0c38"
EXPECTED_HOST_SIZE = 106208
EXPECTED_COUNT = 96
EXPECTED_COMPRESSED = 718_175_632
EXPECTED_UNCOMPRESSED = 1_517_752_485
EXPECTED_REQUIREMENTS_HASH = "3eee40ecaa2646442d1f99ce32000b4b4767782abce56a7b826023d2bb0ee483"
EXPECTED_LOCK_HASH = "ed46ca056a8f54a2ce45cc8f30fcb726e71dbebfdf2acbe33f9c50adea3fd2b2"
FINAL_REL = Path("Runtime/ComfyUI/site-packages")
RUNTIME_WHEELHOUSE_REL = Path("Runtime/ComfyUI/wheelhouse")
PORTABLE_REL = Path("Runtime/Desktop/python/python.exe")
C3C_WHEELHOUSE_REL = Path("FOXAI_USBC3C_EXACT_WHEEL_ACQUISITION/STAGING_WHEELHOUSE")
C3D_PACKAGE = "FOXAI_USBC3D_EXACT_ISOLATED_INSTALL_PLAN"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
APPROVAL_TEXT = "Proceed to USB C3E exact isolated installation under the reviewed C3D transaction and rollback boundaries."

# Exact package-resource exceptions reviewed after the first C3E install. These
# files are intentionally shipped as cross-architecture resources and are not
# importable CPython extension modules or generated runtime launchers.
REVIEWED_NON_CURRENT_PE_RESOURCES = {
    "opengl/dlls/freeglut32.vc9.dll": {
        "machine": 0x014C,
        "reason": "PyOpenGL legacy 32-bit GLUT resource; not selected by the x64 isolated import path",
    },
    "opengl/dlls/freeglut32.vc10.dll": {
        "machine": 0x014C,
        "reason": "PyOpenGL legacy 32-bit GLUT resource; not selected by the x64 isolated import path",
    },
    "opengl/dlls/freeglut32.vc14.dll": {
        "machine": 0x014C,
        "reason": "PyOpenGL legacy 32-bit GLUT resource; not selected by the x64 isolated import path",
    },
    "opengl/dlls/gle32.vc9.dll": {
        "machine": 0x014C,
        "reason": "PyOpenGL legacy 32-bit GLE resource; not selected by the x64 isolated import path",
    },
    "opengl/dlls/gle32.vc10.dll": {
        "machine": 0x014C,
        "reason": "PyOpenGL legacy 32-bit GLE resource; not selected by the x64 isolated import path",
    },
    "opengl/dlls/gle32.vc14.dll": {
        "machine": 0x014C,
        "reason": "PyOpenGL legacy 32-bit GLE resource; not selected by the x64 isolated import path",
    },
    "setuptools/cli.exe": {
        "machine": 0x014C,
        "reason": "Setuptools legacy x86 launcher template resource",
    },
    "setuptools/cli-32.exe": {
        "machine": 0x014C,
        "reason": "Setuptools explicit x86 launcher template resource",
    },
    "setuptools/cli-arm64.exe": {
        "machine": 0xAA64,
        "reason": "Setuptools ARM64 launcher template resource",
    },
    "setuptools/gui.exe": {
        "machine": 0x014C,
        "reason": "Setuptools legacy x86 GUI launcher template resource",
    },
    "setuptools/gui-32.exe": {
        "machine": 0x014C,
        "reason": "Setuptools explicit x86 GUI launcher template resource",
    },
    "setuptools/gui-arm64.exe": {
        "machine": 0xAA64,
        "reason": "Setuptools ARM64 GUI launcher template resource",
    },
}
RESUME_STAGING_PATTERN = re.compile(r"^\.C3E_site-packages_staging_(\d{8}T\d{6}Z)$")
EXPECTED_RESUME_RUN_ID = "20260718T020221Z"
EXPECTED_RESUME_EVIDENCE_HASHES = {
    "boundary_before.json": "574ece7236f4a83b5d1c915c36fad9bed5aec45e3b7fe481d8c782bea20d099a",
    "boundary_final_observed.json": "abe2f4ebc6cd5c8bca61049c9a52e2acf180b87772d38d89ca75d549f074eadf",
    "boundary_final_protected_comparison.json": "7b3fb45d7d1c3c4e55cb7e9ab095a59dc076c9ee62e2d13a4c6f312ea586d57f",
    "c3d_input_verification.json": "4e3076c4d4397b27486acffe38661f322da855f35f0e9e605cb33dd041e57f02",
    "classification.json": "03dd91a8db48ef8daa9898f8c7358749cd1a07bbf83945d5339738b0312d9d92",
    "evidence_integrity.json": "55bbfcc465b45c7d36daea7c320b7ac44fb7a0e2746e05c68b0842200daf0fc6",
    "exact_install_lock_summary.json": "180cb4eb65b76d7741259b8aad02905ec089dc8ac45dc3d43d7fcee2b09af4c9",
    "exception.txt": "0ef7f35eb63ca13601e633dce19be7c50b9d6dbd1c813c430b14c59c0550d37b",
    "installer_identity_after.json": "8540111f5b36cf2c196070e686883bc893076a7da752e12abe13390c74c2c3e6",
    "installer_identity_before.json": "f3cdb40885163a88d11afba44c6965fe3d3093913e16a7a35f6c06ea6236ad70",
    "operator_approval.json": "c67b722f5e147103f30b7a3deab47e746e55cc5d18111258845a9ca4fb1659b6",
    "package_verification.json": "17cb2167a64796f1d8ae8e75473e325c2882322800ff539dcb265f667b622fb2",
    "pip_install_execution.json": "7f88254313598752ec73a190f1dc8dcb9f58f11acbf32572a1a870896e82824e",
    "pip_install_stderr.txt": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "pip_install_stdout.txt": "6e4badd460bfbc548ed48b6a7bd4537ace1b1bb6f49ff88f14ceaced112ced01",
    "process_safety.json": "774c771acd775f351df774a5d66ea457b15b26d5ab41d93f006ad63c0ac72051",
    "receipt.json": "d096369f036418fe386dc9668cdde143931e10d7f8a6c11d058f406e5d21ce48",
    "report.md": "31658e72d0875723014bb7904ab297c1d2f31be12713356e51d194fd20f9cd32",
    "rollback_state.json": "4e012c1501f329e609ba92d245e42cd337a0e73d283b866fe9adefbfe122fa92",
    "runtime_identity.json": "8c3a24b1b04bb31e605581296bca6e9a6c246ee64ce0f692e24c0ac647f36333",
    "space_before.json": "2a48e4e4e62148033cb3e6e5da1ec6267185a268d8a5ceea7a15bd19cead918f",
    "transaction_parent.json": "f91fcc94430802687711ea4f811d97cf4b42380e991d77aa029600c3ae64a7a8",
    "transaction_target.json": "641ff004aa3d5b389a39c67e2a14768b1fab6d3196c9fbe282920af92298cac2",
    "wheelhouse_after_install.json": "d28191a9406311c90d744a828f73a54a4121ccf7453f3fd5f7151d39c1b4c016",
    "wheelhouse_before_install.json": "d28191a9406311c90d744a828f73a54a4121ccf7453f3fd5f7151d39c1b4c016",
}

EXPECTED_C3D_HASHES = {
    "OPERATOR_APPROVAL_REQUEST.txt": "b1a68759e0a0c5621aaa65ce1a1457769515117200cca9146df3676397e1639d",
    "activation_plan.json": "9cb31a628dca1442ea6d7f1165cbfa832e9e3e416261bec3340e1a4bf99e06c2",
    "boundary_after.json": "7807487d15a85ae9286f29a7b35a5a9498b1d91c0ac40bbeb19e33991d87360f",
    "boundary_before.json": "e751cfe42ce6163ee37657db3929fa61a1b63b72528020fe493e7b307975d333",
    "boundary_comparison.json": "aa0359de867cb32d37f19dae80b72d2c02bc155cfe4a2610eb6a91a70aa3e709",
    "c3b_install_order_verification.json": "9ffc24b1cd9796d02a1dfc96c3a97d27d27b0cd33e35a17d74d312533f0c1bec",
    "c3c_documents_summary.json": "a2624b763873e55be2bc9cf45d1e5b92c2995388a7e8ccae16fb58b600e48a4f",
    "c3c_input_verification.json": "6fb9a968e8325fac50eb9a5f7f0b54c1667409779f896bd4a04798782b37c586",
    "c3e_transaction_plan.json": "a5400f8588171613ec933bd6a74ee5433893a952ae77e7516ce237dcd293c7a9",
    "classification.json": "cf7b3db84f4cc0d51e9fdf85073af0a22ec02ba55173023d1d2216436e56a9a0",
    "destination_collision_report.json": "363317fad806dea865edd04c873ebfe825ba5fe115dcc26109b30f998c23f4a7",
    "entry_points_review.json": "89fb94eb33bf47f5681cfe3407b4056e118b7007c324f7f2e7550b29abc53226",
    "evidence_integrity.json": "ca44511602e39005773da373c0014332720bb2a03d44f125deb18927db37a8ad",
    "exact-offline-install-requirements.txt": EXPECTED_REQUIREMENTS_HASH,
    "exact_install_lock.json": EXPECTED_LOCK_HASH,
    "pip_capability.json": "2436453eca169aee87d058ad86a2041c760a977f5b622b20b905edea29c338d5",
    "pip_dry_run_execution.json": "99e73fd5ade58c0f36db4254fce8ee11a2c18d4e8e507e1a641dab9e28184f40",
    "pip_dry_run_report.json": "9557a04fc226b518a1c8c34eea82f9636396506dd1fd9951a2a9afc5156c0da2",
    "pip_dry_run_stderr.txt": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "pip_dry_run_stdout.txt": "936247a9821c0b47fcba64beb5f4cc50293c278a9b4d76a52a7858da5b474def",
    "pip_dry_run_validation.json": "2f85f651a6a2e890a7a66826c80414ee7159eb7787f8b7eb3d5ed88b12572b9f",
    "post_install_verification_plan.json": "8a4838009a6795abc825a180731d5bbaada41909c1eabb882ce53abe0aaf609b",
    "pth_review.json": "359df1b4c6173f41496b60b1bb600873f0b42b69e12d825e8fa55ba0e61ec1d5",
    "receipt.json": "a38444e1b115ebe5ea974c4c8fa3ab626441e7c9cc3f4d41ee4fa22d99185225",
    "report.md": "403e72d6146a2bf64046db7e834fadffd68df07a8af031bac0aa2582e6489937",
    "rollback_plan.json": "8eeab4ac81b82ce89d16510a2a444e6f67a548959852a8e818534a594c25b59d",
    "runtime_identity.json": "bf56f1b356b1177c13ba0eee8a236159c39089e1cf6960af0cecf0a59ac6f551",
    "space_plan.json": "a31efb59bea760196bfe6c13a75db3373d35c80e91d283c3226b7601e6a840ca",
    "wheel_payload_analysis.json": "6e61a6e12e62481ca4e341ff6db6101130a97ba0327242c6c91318e40d10ecc5",
    "wheelhouse_reverification.json": "b6954b2ac3277dce315abab8af524728535f4626ddceecfa317b2970d478cefb",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def slug() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def norm(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path.resolve(strict=False))))


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except Exception:
        return False


def run_command(command: list[str], cwd: Path, env: dict[str, str], timeout: int) -> dict[str, Any]:
    started = utc_now()
    try:
        completed = subprocess.run(command, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout, check=False)
        ended = utc_now()
        return {
            "command": command,
            "command_display": subprocess.list2cmdline(command),
            "started": started.isoformat(),
            "completed": ended.isoformat(),
            "elapsed_seconds": round((ended - started).total_seconds(), 3),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        ended = utc_now()
        return {
            "command": command,
            "command_display": subprocess.list2cmdline(command),
            "started": started.isoformat(),
            "completed": ended.isoformat(),
            "elapsed_seconds": round((ended - started).total_seconds(), 3),
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + f"\nTimed out after {timeout} seconds.",
            "timed_out": True,
        }


def verify_self(package: Path) -> dict[str, Any]:
    manifest_path = package / "PACKAGE_INTEGRITY.json"
    if not manifest_path.is_file():
        raise RuntimeError("PACKAGE_INTEGRITY.json is missing")
    manifest = read_json(manifest_path)
    issues = []
    rows = []
    for item in manifest.get("files", []):
        path = package / item["path"]
        if not path.is_file():
            issues.append(f"missing package file: {item['path']}")
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        verified = size == item["size_bytes"] and digest == item["sha256"]
        rows.append({"path": item["path"], "size_bytes": size, "sha256": digest, "verified": verified})
        if not verified:
            issues.append(f"package integrity mismatch: {item['path']}")
    if len(rows) != manifest.get("file_count"):
        issues.append("package file count mismatch")
    if issues:
        raise RuntimeError(f"C3E package integrity failed: {issues}")
    return {"verified": True, "file_count": len(rows), "files": rows}


def verify_approval(package: Path) -> dict[str, Any]:
    approval = read_json(package / "OPERATOR_APPROVAL.json")
    verified = approval.get("approved") is True and approval.get("approval") == APPROVAL_TEXT
    if not verified:
        raise RuntimeError("Embedded C3E operator approval is missing or changed")
    return {"verified": True, **approval}


def verify_portable_identity(root: Path) -> dict[str, Any]:
    expected = root / PORTABLE_REL
    checks = {
        "exact_executable": norm(Path(sys.executable)) == norm(expected),
        "version": tuple(sys.version_info[:3]) == EXPECTED_PORTABLE_VERSION,
        "cpython": platform.python_implementation() == "CPython",
        "windows": os.name == "nt" and sys.platform == "win32",
        "64_bit": struct.calcsize("P") * 8 == 64,
        "amd64": platform.machine().upper() in {"AMD64", "X86_64"},
        "isolated": bool(sys.flags.isolated),
    }
    result = {
        "expected": str(expected),
        "actual": sys.executable,
        "version": list(sys.version_info[:3]),
        "implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "pointer_bits": struct.calcsize("P") * 8,
        "checks": checks,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Portable runtime identity failed: {result}")
    return result


def find_exact_c3d(root: Path) -> tuple[Path, dict[str, Any]]:
    base = root / C3D_PACKAGE / "PLAN_OUTPUT"
    candidates = sorted({p.parent for p in base.rglob("receipt.json")}) if base.is_dir() else []
    matches = []
    attempts = []
    for folder in candidates:
        issues = []
        for name, expected in EXPECTED_C3D_HASHES.items():
            path = folder / name
            if not path.is_file():
                issues.append({"file": name, "status": "missing"})
            else:
                actual = sha256_file(path)
                if actual != expected:
                    issues.append({"file": name, "status": "hash_mismatch", "actual": actual})
        attempts.append({"folder": str(folder), "issues": issues})
        if not issues:
            matches.append(folder)
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one reviewed C3D evidence folder; found {len(matches)}. Attempts: {attempts}")
    folder = matches[0]
    classification = read_json(folder / "classification.json")
    receipt = read_json(folder / "receipt.json")
    dry = read_json(folder / "pip_dry_run_validation.json")
    transaction = read_json(folder / "c3e_transaction_plan.json")
    collisions = read_json(folder / "destination_collision_report.json")
    pth = read_json(folder / "pth_review.json")
    space = read_json(folder / "space_plan.json")
    if classification.get("mode") != "C3D_READY_FOR_OPERATOR_APPROVAL" or classification.get("verified") is not True:
        raise RuntimeError("Reviewed C3D classification changed")
    if receipt.get("verified") is not True or receipt.get("exact_package_count") != EXPECTED_COUNT or receipt.get("pip_dry_run_install_count") != EXPECTED_COUNT:
        raise RuntimeError("Reviewed C3D receipt changed")
    if dry.get("verified") is not True or dry.get("install_count") != EXPECTED_COUNT:
        raise RuntimeError("Reviewed C3D dry run changed")
    engine = transaction.get("installer_engine") or {}
    command = transaction.get("future_install_command_argv") or []
    required_flags = {"--ignore-installed", "--no-index", "--no-deps", "--only-binary=:all:", "--require-hashes", "--no-cache-dir", "--no-compile", "--target"}
    if (engine.get("verified") is not True or engine.get("python") != str(EXPECTED_HOST_PYTHON)
            or engine.get("python_sha256") != EXPECTED_HOST_HASH or engine.get("pip_version") != EXPECTED_HOST_PIP):
        raise RuntimeError("Reviewed C3D installer engine binding changed")
    if not required_flags.issubset(set(command)):
        raise RuntimeError("Reviewed C3D future install command lost required safety flags")
    if collisions.get("verified") is not True or collisions.get("case_insensitive_cross_wheel_collision_count") != 0:
        raise RuntimeError("Reviewed C3D collision result changed")
    if pth.get("pth_file_count") != 1 or pth.get("pth_files_with_executable_import_lines") != 1:
        raise RuntimeError("Reviewed C3D .pth finding changed")
    if space.get("sufficient") is not True:
        raise RuntimeError("Reviewed C3D space plan was not sufficient")
    return folder, {
        "verified": True, "folder": str(folder), "file_count": len(EXPECTED_C3D_HASHES), "hashes": EXPECTED_C3D_HASHES,
        "transaction_engine": {"python": engine.get("python"), "python_sha256": engine.get("python_sha256"), "pip_version": engine.get("pip_version")},
        "required_install_flags": sorted(required_flags), "collision_count": 0, "reviewed_pth_files": 1,
    }


def load_lock(c3d: Path, wheelhouse: Path) -> tuple[list[dict[str, Any]], Path, dict[str, Any]]:
    lock_path = c3d / "exact_install_lock.json"
    requirements = c3d / "exact-offline-install-requirements.txt"
    if sha256_file(lock_path) != EXPECTED_LOCK_HASH or sha256_file(requirements) != EXPECTED_REQUIREMENTS_HASH:
        raise RuntimeError("Exact C3D lock or requirements hash changed")
    lock = read_json(lock_path)
    entries = lock.get("entries") or []
    if lock.get("verified") is not True or len(entries) != EXPECTED_COUNT:
        raise RuntimeError("Exact install lock no longer contains 96 verified entries")
    names = set()
    filenames = set()
    total = 0
    normalized = []
    for item in entries:
        name = re.sub(r"[-_.]+", "-", str(item["name"])).lower()
        filename = str(item["filename"])
        digest = str(item["sha256"]).lower()
        if not HEX64.fullmatch(digest):
            raise RuntimeError(f"Malformed wheel hash for {filename}")
        if name in names or filename.casefold() in filenames:
            raise RuntimeError("Duplicate package name or wheel filename in exact lock")
        names.add(name)
        filenames.add(filename.casefold())
        path = wheelhouse / filename
        normalized.append({
            "position": int(item["position"]),
            "name": name,
            "version": str(item["version"]),
            "filename": filename,
            "size_bytes": int(item["size_bytes"]),
            "sha256": digest,
            "path": str(path),
        })
        total += int(item["size_bytes"])
    if total != EXPECTED_COMPRESSED:
        raise RuntimeError(f"Exact compressed wheel total changed: {total}")
    normalized.sort(key=lambda row: row["position"])
    return normalized, requirements, lock


def verify_wheelhouse(rows: list[dict[str, Any]], wheelhouse: Path) -> dict[str, Any]:
    if not wheelhouse.is_dir():
        raise RuntimeError(f"C3C wheelhouse missing: {wheelhouse}")
    actual = sorted(p.name for p in wheelhouse.iterdir() if p.is_file())
    expected_names = [row["filename"] for row in rows]
    missing = sorted(set(expected_names) - set(actual))
    unexpected = sorted(set(actual) - set(expected_names))
    results = []
    for row in rows:
        path = wheelhouse / row["filename"]
        if not path.is_file():
            results.append({**row, "verified": False, "reason": "missing"})
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        verified = size == row["size_bytes"] and digest == row["sha256"]
        results.append({**row, "actual_size_bytes": size, "actual_sha256": digest, "verified": verified})
    verified = not missing and not unexpected and all(item["verified"] for item in results)
    if not verified:
        raise RuntimeError(f"Wheelhouse exact verification failed: missing={missing}, unexpected={unexpected}")
    return {"verified": True, "wheel_count": len(results), "compressed_bytes": sum(i["actual_size_bytes"] for i in results), "missing": missing, "unexpected": unexpected, "wheels": results}


def clean_env(output: Path) -> dict[str, str]:
    for directory in [output / "PIP_TEMP", output / "PIP_CACHE", output / "OFFLINE_CACHE"]:
        directory.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    for key in ["PYTHONHOME", "PYTHONPATH", "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
        env.pop(key, None)
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "PIP_NO_INDEX": "1",
        "PIP_CACHE_DIR": str(output / "PIP_CACHE"),
        "TMP": str(output / "PIP_TEMP"),
        "TEMP": str(output / "PIP_TEMP"),
        "HF_HUB_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "NO_PROXY": "*",
        "SETUPTOOLS_USE_DISTUTILS": "local",
        "HF_HOME": str(output / "OFFLINE_CACHE" / "huggingface"),
        "HUGGINGFACE_HUB_CACHE": str(output / "OFFLINE_CACHE" / "huggingface" / "hub"),
        "TRANSFORMERS_CACHE": str(output / "OFFLINE_CACHE" / "transformers"),
        "TORCH_HOME": str(output / "OFFLINE_CACHE" / "torch"),
        "XDG_CACHE_HOME": str(output / "OFFLINE_CACHE" / "xdg"),
        "MPLCONFIGDIR": str(output / "OFFLINE_CACHE" / "matplotlib"),
        "UV_CACHE_DIR": str(output / "OFFLINE_CACHE" / "uv"),
    })
    return env


def verify_host_installer(output: Path) -> dict[str, Any]:
    path = EXPECTED_HOST_PYTHON
    if not path.is_file():
        raise RuntimeError(f"Approved host installer is missing: {path}")
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != EXPECTED_HOST_SIZE or digest != EXPECTED_HOST_HASH:
        raise RuntimeError(f"Approved host installer changed: size={size}, sha256={digest}")
    env = clean_env(output)
    identity_code = (
        "import json,platform,struct,sys;"
        "print(json.dumps({'version':list(sys.version_info[:3]),'implementation':platform.python_implementation(),"
        "'machine':platform.machine(),'bits':struct.calcsize('P')*8,'platform':sys.platform,'executable':sys.executable}))"
    )
    identity = run_command([str(path), "-I", "-B", "-c", identity_code], output, env, 60)
    version = run_command([str(path), "-I", "-B", "-m", "pip", "--isolated", "--disable-pip-version-check", "--version"], output, env, 60)
    help_result = run_command([str(path), "-I", "-B", "-m", "pip", "--isolated", "--disable-pip-version-check", "install", "--help"], output, env, 60)
    try:
        identity_json = json.loads(identity["stdout"].strip()) if identity["returncode"] == 0 else {}
    except Exception:
        identity_json = {}
    pip_match = re.search(r"\bpip\s+([^\s]+)", version.get("stdout", ""))
    pip_version = pip_match.group(1) if pip_match else None
    help_text = help_result.get("stdout", "") + "\n" + help_result.get("stderr", "")
    required = ["--target", "--ignore-installed", "--no-index", "--no-deps", "--only-binary", "--require-hashes", "--no-cache-dir", "--no-compile"]
    support = {item: item in help_text for item in required}
    verified = (
        identity["returncode"] == 0
        and identity_json.get("version") == list(EXPECTED_HOST_VERSION)
        and identity_json.get("implementation") == "CPython"
        and str(identity_json.get("machine", "")).upper() in {"AMD64", "X86_64"}
        and identity_json.get("bits") == 64
        and identity_json.get("platform") == "win32"
        and version["returncode"] == 0
        and pip_version == EXPECTED_HOST_PIP
        and help_result["returncode"] == 0
        and all(support.values())
    )
    result = {
        "verified": verified,
        "path": str(path),
        "size_bytes": size,
        "sha256": digest,
        "identity": identity_json,
        "identity_probe": identity,
        "pip_version": pip_version,
        "pip_version_probe": version,
        "required_option_support": support,
        "pip_help_sha256": hashlib.sha256(help_text.encode("utf-8", errors="replace")).hexdigest(),
        "pip_help_returncode": help_result["returncode"],
    }
    if not verified:
        raise RuntimeError(f"Approved host installer verification failed: {result}")
    return result


def process_safety_check(root: Path, output: Path) -> dict[str, Any]:
    command = [
        "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command",
        "$ErrorActionPreference='Stop'; Get-CimInstance Win32_Process | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress -Depth 3",
    ]
    result = run_command(command, output, os.environ.copy(), 60)
    if result["returncode"] != 0:
        raise RuntimeError(f"Could not perform required process safety check: {result['stderr']}")
    raw = result["stdout"].strip()
    try:
        parsed = json.loads(raw) if raw else []
    except Exception as exc:
        raise RuntimeError(f"Process inventory JSON parse failed: {type(exc).__name__}: {exc}")
    if isinstance(parsed, dict):
        parsed = [parsed]
    blockers = []
    root_text = str(root).lower()
    current = os.getpid()
    keywords = ["comfyui", "start_foxai", "webui", "main_window.py", "mission console", "agent fox"]
    for row in parsed:
        pid = int(row.get("ProcessId") or 0)
        if pid == current:
            continue
        name = str(row.get("Name") or "")
        executable = str(row.get("ExecutablePath") or "")
        cmdline = str(row.get("CommandLine") or "")
        text = (executable + " " + cmdline).lower()
        under_root = root_text in text
        relevant = under_root and any(keyword in text for keyword in keywords)
        portable_python_other = norm(Path(executable)) == norm(root / PORTABLE_REL) if executable else False
        if relevant or portable_python_other:
            blockers.append({"pid": pid, "name": name, "executable": executable, "command_line": cmdline, "reason": "FOXAI/ComfyUI runtime process or additional portable Python process"})
    summary = {"verified": not blockers, "process_count": len(parsed), "blockers": blockers, "probe": {k: v for k, v in result.items() if k not in {"stdout", "stderr"}}}
    if blockers:
        raise RuntimeError(f"Runtime process safety check blocked installation: {blockers}")
    return summary


def tree_digest(path: Path, excludes: Iterable[str] = ()) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    exclude_set = {item.casefold() for item in excludes}
    aggregate = hashlib.sha256()
    file_count = 0
    byte_count = 0
    skipped = []
    for item in sorted(path.rglob("*"), key=lambda p: str(p).casefold()):
        if not item.is_file():
            continue
        try:
            rel = item.relative_to(path)
        except Exception:
            continue
        parts = [part.casefold() for part in rel.parts]
        if parts and parts[0] in exclude_set:
            skipped.append(rel.as_posix())
            continue
        if "__pycache__" in parts:
            continue
        digest = sha256_file(item)
        size = item.stat().st_size
        aggregate.update(rel.as_posix().casefold().encode("utf-8", errors="surrogatepass"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
        file_count += 1
        byte_count += size
    return {"path": str(path), "exists": True, "file_count": file_count, "byte_count": byte_count, "tree_sha256": aggregate.hexdigest(), "excluded_top_level": sorted(exclude_set), "skipped_count": len(skipped)}


def snapshot_boundaries(root: Path) -> dict[str, Any]:
    key_paths = [root / "ComfyUI/main.py", root / PORTABLE_REL, root / "START_FOXAI_CLEAN.bat"]
    for pattern in ("*.bat", "*.cmd", "*.ps1"):
        key_paths.extend(root.glob(pattern))
    unique = sorted({p.resolve(strict=False) for p in key_paths}, key=lambda p: str(p).casefold())
    key_files = []
    for path in unique:
        row = {"path": str(path), "exists": path.is_file()}
        if path.is_file():
            row.update({"size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
        key_files.append(row)
    staging = sorted(str(p) for p in (root / "Runtime/ComfyUI").glob(".C3E_site-packages_staging_*") if p.exists())
    return {
        "captured": iso_now(),
        "key_files": key_files,
        "protected_trees": {
            "desktop": tree_digest(root / "Runtime/Desktop"),
            "core": tree_digest(root / "Runtime/Core"),
            "system": tree_digest(root / "System"),
            "comfyui_source": tree_digest(root / "ComfyUI", excludes=["models", "input", "output", "temp"]),
        },
        "final_target_exists": (root / FINAL_REL).exists(),
        "runtime_wheelhouse_exists": (root / RUNTIME_WHEELHOUSE_REL).exists(),
        "c3e_staging_directories": staging,
    }


def compare_boundaries(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_files = {row["path"]: row for row in before["key_files"]}
    after_files = {row["path"]: row for row in after["key_files"]}
    file_changes = []
    for path in sorted(set(before_files) | set(after_files)):
        left = before_files.get(path)
        right = after_files.get(path)
        if left != right:
            file_changes.append({"path": path, "before": left, "after": right})
    tree_changes = []
    for key in before["protected_trees"]:
        left = before["protected_trees"][key]
        right = after["protected_trees"].get(key)
        comparable_left = {k: v for k, v in left.items() if k != "path"}
        comparable_right = {k: v for k, v in (right or {}).items() if k != "path"}
        if comparable_left != comparable_right:
            tree_changes.append({"tree": key, "before": left, "after": right})
    return {"verified": not file_changes and not tree_changes, "protected_file_changes": file_changes, "protected_tree_changes": tree_changes}



def prepare_transaction_parent(root: Path) -> tuple[Path, bool]:
    """Return Runtime/ComfyUI, creating only that one approved parent if absent."""
    runtime_root = root / "Runtime"
    parent = runtime_root / "ComfyUI"
    if not runtime_root.is_dir() or runtime_root.is_symlink():
        raise RuntimeError(f"Protected Runtime directory is missing or unsafe: {runtime_root}")
    if parent.exists():
        if not parent.is_dir() or parent.is_symlink():
            raise RuntimeError(f"Runtime/ComfyUI exists but is not a safe directory: {parent}")
        return parent, False
    parent.mkdir(exist_ok=False)
    if not parent.is_dir() or parent.is_symlink():
        raise RuntimeError(f"Could not create the approved Runtime/ComfyUI parent safely: {parent}")
    return parent, True


def verify_evidence_directory(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "evidence_integrity.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"Prior C3E evidence integrity manifest is missing: {manifest_path}")
    manifest = read_json(manifest_path)
    issues = []
    rows = []
    for record in manifest.get("files", []):
        path = run_dir / record["file"]
        if not path.is_file():
            issues.append(f"missing prior evidence file: {record['file']}")
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        verified = size == record["size_bytes"] and digest == record["sha256"]
        rows.append({
            "file": record["file"],
            "size_bytes": size,
            "sha256": digest,
            "verified": verified,
        })
        if not verified:
            issues.append(f"prior evidence mismatch: {record['file']}")
    if len(rows) != manifest.get("file_count"):
        issues.append(
            f"prior evidence file count mismatch: expected={manifest.get('file_count')} observed={len(rows)}"
        )
    if issues:
        raise RuntimeError(f"Prior C3E evidence verification failed: {issues}")
    return {
        "verified": True,
        "run_directory": str(run_dir),
        "file_count": len(rows),
        "manifest_sha256": sha256_file(manifest_path),
        "files": rows,
    }


def verify_resume_transaction(
    package: Path,
    staging: Path,
    final_target: Path,
    current_output: Path,
) -> dict[str, Any]:
    if not staging.is_dir() or staging.is_symlink():
        raise RuntimeError(f"Preserved staging target is missing or unsafe: {staging}")
    match = RESUME_STAGING_PATTERN.fullmatch(staging.name)
    if not match:
        raise RuntimeError(f"Preserved staging target has an unexpected name: {staging.name}")
    run_id = match.group(1)
    if run_id != EXPECTED_RESUME_RUN_ID:
        raise RuntimeError(
            f"Preserved staging run is not the exact reviewed C3E run: {run_id}"
        )
    prior_output = package / "INSTALL_OUTPUT" / run_id
    if prior_output.resolve(strict=False) == current_output.resolve(strict=False):
        raise RuntimeError("Current C3E evidence directory cannot serve as resume evidence")
    if not prior_output.is_dir() or prior_output.is_symlink():
        raise RuntimeError(f"Exact prior C3E evidence directory is missing or unsafe: {prior_output}")

    exact_hash_rows = []
    exact_hash_issues = []
    for name, expected_hash in EXPECTED_RESUME_EVIDENCE_HASHES.items():
        path = prior_output / name
        if not path.is_file():
            exact_hash_issues.append(f"missing exact reviewed resume evidence: {name}")
            continue
        digest = sha256_file(path)
        verified = digest == expected_hash
        exact_hash_rows.append({
            "file": name,
            "sha256": digest,
            "expected_sha256": expected_hash,
            "verified": verified,
        })
        if not verified:
            exact_hash_issues.append(f"exact reviewed resume evidence changed: {name}")
    if exact_hash_issues:
        raise RuntimeError(
            f"Exact reviewed C3E resume evidence binding failed: {exact_hash_issues}"
        )

    evidence = verify_evidence_directory(prior_output)
    required = [
        "classification.json",
        "receipt.json",
        "pip_install_execution.json",
        "installer_identity_after.json",
        "wheelhouse_after_install.json",
        "boundary_final_protected_comparison.json",
    ]
    missing = [name for name in required if not (prior_output / name).is_file()]
    if missing:
        raise RuntimeError(f"Prior C3E resume evidence is incomplete: {missing}")

    classification = read_json(prior_output / "classification.json")
    receipt = read_json(prior_output / "receipt.json")
    pip_execution = read_json(prior_output / "pip_install_execution.json")
    installer_after = read_json(prior_output / "installer_identity_after.json")
    wheelhouse_after = read_json(prior_output / "wheelhouse_after_install.json")
    boundary_comparison = read_json(prior_output / "boundary_final_protected_comparison.json")

    checks = {
        "classification_is_fail_closed_staging_preserved": classification.get("mode") == BLOCKED_STAGING,
        "classification_reports_staging_preserved": classification.get("staging_preserved") is True,
        "classification_reports_no_commit": classification.get("final_target_committed") is False,
        "receipt_install_completed": receipt.get("package_install_completed") is True,
        "receipt_staging_exists": receipt.get("staging_exists") is True,
        "receipt_no_commit": receipt.get("final_target_committed") is False,
        "receipt_no_network": receipt.get("network_access") is False,
        "receipt_no_launcher_change": receipt.get("launcher_change") is False,
        "receipt_staging_matches": norm(Path(receipt.get("staging_target", ""))) == norm(staging),
        "receipt_final_matches": norm(Path(receipt.get("final_target", ""))) == norm(final_target),
        "pip_returncode_zero": pip_execution.get("returncode") == 0,
        "pip_network_forbidden": pip_execution.get("network_allowed") is False,
        "pip_target_matches": norm(Path(pip_execution.get("target", ""))) == norm(staging),
        "installer_after_verified": installer_after.get("verified") is True,
        "installer_hash_matches": installer_after.get("sha256") == EXPECTED_HOST_HASH,
        "installer_pip_matches": installer_after.get("pip_version") == EXPECTED_HOST_PIP,
        "wheelhouse_after_verified": wheelhouse_after.get("verified") is True,
        "wheelhouse_count_matches": wheelhouse_after.get("wheel_count") == EXPECTED_COUNT,
        "wheelhouse_bytes_match": wheelhouse_after.get("compressed_bytes") == EXPECTED_COMPRESSED,
        "protected_boundaries_unchanged": boundary_comparison.get("verified") is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Preserved C3E transaction failed resume verification: {failed}")

    return {
        "verified": True,
        "mode": "resume_exact_preserved_staging_without_reinstall",
        "run_id": run_id,
        "prior_output": str(prior_output),
        "staging_target": str(staging),
        "final_target": str(final_target),
        "checks": checks,
        "prior_evidence": evidence,
        "exact_reviewed_evidence_binding": {
            "verified": True,
            "file_count": len(exact_hash_rows),
            "files": exact_hash_rows,
        },
        "prior_classification_sha256": sha256_file(prior_output / "classification.json"),
        "prior_receipt_sha256": sha256_file(prior_output / "receipt.json"),
        "prior_pip_execution_sha256": sha256_file(prior_output / "pip_install_execution.json"),
        "runtime_parent_created_by_prior_c3e": receipt.get("runtime_parent_created_by_c3e") is True,
    }


def disk_space(root: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(root)
    required = max(EXPECTED_UNCOMPRESSED * 2, EXPECTED_UNCOMPRESSED + 1024 * 1024 * 1024)
    result = {"free_bytes": usage.free, "required_bytes": required, "sufficient": usage.free >= required}
    if not result["sufficient"]:
        raise RuntimeError(f"Insufficient free space for C3E transaction: {result}")
    return result


def pe_machine(path: Path) -> int:
    with path.open("rb") as handle:
        if handle.read(2) != b"MZ":
            raise ValueError("missing MZ header")
        handle.seek(0x3C)
        offset_bytes = handle.read(4)
        if len(offset_bytes) != 4:
            raise ValueError("missing PE offset")
        pe_offset = struct.unpack("<I", offset_bytes)[0]
        handle.seek(pe_offset)
        if handle.read(4) != b"PE\0\0":
            raise ValueError("missing PE signature")
        machine_bytes = handle.read(2)
        if len(machine_bytes) != 2:
            raise ValueError("missing PE machine")
        return struct.unpack("<H", machine_bytes)[0]


def classify_pe_binary(relative_path: str, machine: int) -> dict[str, Any]:
    normalized = relative_path.replace("\\", "/").casefold()
    if machine == 0x8664:
        return {
            "verified": True,
            "architecture": "AMD64",
            "current_architecture": True,
            "classification": "current_runtime_binary",
        }
    reviewed = REVIEWED_NON_CURRENT_PE_RESOURCES.get(normalized)
    if reviewed and machine == reviewed["machine"]:
        architecture = {0x014C: "X86", 0xAA64: "ARM64"}.get(machine, f"OTHER_0x{machine:04x}")
        return {
            "verified": True,
            "architecture": architecture,
            "current_architecture": False,
            "classification": "reviewed_non_current_architecture_package_resource",
            "reason": reviewed["reason"],
        }
    return {
        "verified": False,
        "architecture": {0x014C: "X86", 0xAA64: "ARM64"}.get(machine, f"OTHER_0x{machine:04x}"),
        "current_architecture": False,
        "classification": "unapproved_non_current_architecture_binary",
    }


def inventory_target(target: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = []
    pe_rows = []
    total = 0
    issues = []
    for path in sorted(target.rglob("*"), key=lambda p: str(p).casefold()):
        if path.is_symlink():
            issues.append(f"symlink/reparse-like entry is not permitted: {path}")
            continue
        if not path.is_file():
            continue
        if not is_within(path, target):
            issues.append(f"file escapes target: {path}")
            continue
        rel = path.relative_to(target).as_posix()
        size = path.stat().st_size
        digest = sha256_file(path)
        rows.append({"path": rel, "size_bytes": size, "sha256": digest})
        total += size
        if path.suffix.lower() in {".pyd", ".dll", ".exe"}:
            try:
                machine = pe_machine(path)
                classification = classify_pe_binary(rel, machine)
                row = {
                    "path": rel,
                    "machine": f"0x{machine:04x}",
                    **classification,
                }
                pe_rows.append(row)
                if not classification["verified"]:
                    issues.append(
                        f"unapproved non-AMD64 PE binary: {rel} machine=0x{machine:04x}"
                    )
            except Exception as exc:
                pe_rows.append({"path": rel, "verified": False, "issue": f"{type(exc).__name__}: {exc}"})
                issues.append(f"invalid PE binary {rel}: {type(exc).__name__}: {exc}")
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row["path"].casefold().encode("utf-8", errors="surrogatepass"))
        digest.update(b"\0")
        digest.update(str(row["size_bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(row["sha256"].encode("ascii"))
        digest.update(b"\n")
    inventory = {"verified": not issues, "target": str(target), "file_count": len(rows), "total_bytes": total, "tree_sha256": digest.hexdigest(), "issues": issues, "files": rows}
    pe = {
        "verified": not issues and all(row.get("verified") for row in pe_rows),
        "binary_count": len(pe_rows),
        "current_architecture_binary_count": sum(1 for row in pe_rows if row.get("current_architecture") is True),
        "reviewed_non_current_resource_count": sum(
            1
            for row in pe_rows
            if row.get("classification") == "reviewed_non_current_architecture_package_resource"
        ),
        "issues": [issue for issue in issues if "PE" in issue or "binary" in issue],
        "binaries": pe_rows,
    }
    if issues:
        raise RuntimeError(f"Installed target inventory/PE validation failed: {issues[:20]}")
    return inventory, pe


def portable_verify(root: Path, package: Path, target: Path, lock: Path, output: Path, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    verifier = package / "System/Installation/usbc3e_portable_verify.py"
    result_path = output / f"portable_verification_{label}.json"
    env = clean_env(output)
    command = [str(root / PORTABLE_REL), "-I", "-B", "-S", str(verifier), "--target", str(target), "--lock", str(lock), "--output", str(result_path)]
    execution = run_command(command, output, env, 1800)
    (output / f"portable_verification_{label}_stdout.txt").write_text(execution["stdout"], encoding="utf-8", newline="\n")
    (output / f"portable_verification_{label}_stderr.txt").write_text(execution["stderr"], encoding="utf-8", newline="\n")
    summary = {k: v for k, v in execution.items() if k not in {"stdout", "stderr"}}
    summary.update({"stdout_file": f"portable_verification_{label}_stdout.txt", "stderr_file": f"portable_verification_{label}_stderr.txt", "result_file": result_path.name, "result_exists": result_path.is_file()})
    verification = read_json(result_path) if result_path.is_file() else {"verified": False, "issues": ["portable verifier produced no result"]}
    if execution["returncode"] != 0 or verification.get("verified") is not True:
        raise RuntimeError(f"Portable verification {label} failed: returncode={execution['returncode']}, issues={verification.get('issues')}")
    return summary, verification


def build_report(receipt: dict[str, Any], classification: dict[str, Any]) -> str:
    return "\n".join([
        "# FOXAI USB C3E — Exact Isolated Installation",
        "",
        f"- Classification: `{classification['mode']}`",
        f"- Verified: `{classification['verified']}`",
        f"- Installed package count: **{receipt.get('exact_package_count')}**",
        f"- Final target committed: **{receipt.get('final_target_committed')}**",
        f"- Installed files: **{receipt.get('installed_file_count')}**",
        f"- Installed bytes: **{receipt.get('installed_bytes')}**",
        f"- PE binaries verified: **{receipt.get('pe_binary_count')}**",
        "",
        "C3E made no launcher change and did not launch FOXAI, WebUI, Desktop, or ComfyUI.",
        "The isolated target must remain unintegrated until exact C3E evidence review and the later C3F controlled launch gate.",
        "",
        "## Blocking findings",
        "",
        *(f"- {item}" for item in classification.get("blocking_findings", [])),
    ]) + "\n"


def seal_evidence(output: Path) -> tuple[Path, str]:
    integrity_path = output / "evidence_integrity.json"
    review_zip = output / "UPLOAD_THIS_C3E_REVIEW.zip"
    files = sorted(p for p in output.iterdir() if p.is_file() and p not in {integrity_path, review_zip})
    records = []
    for path in files:
        records.append({"file": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(integrity_path, {"verified": True, "file_count": len(records), "files": records})
    if review_zip.exists():
        review_zip.unlink()
    with zipfile.ZipFile(review_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in output.iterdir() if p.is_file() and p != review_zip):
            archive.write(path, path.name)
    with zipfile.ZipFile(review_zip, "r") as archive:
        names = set(archive.namelist())
        if "evidence_integrity.json" not in names:
            raise RuntimeError("review bundle is missing evidence_integrity.json")
        for record in records:
            if record["file"] not in names:
                raise RuntimeError(f"review bundle is missing {record['file']}")
            content = archive.read(record["file"])
            if len(content) != record["size_bytes"] or hashlib.sha256(content).hexdigest() != record["sha256"]:
                raise RuntimeError(f"review bundle integrity mismatch for {record['file']}")
    return review_zip, sha256_file(review_zip)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve(strict=True)
    package = Path(__file__).resolve().parents[2]
    output_base = package / "INSTALL_OUTPUT"
    output_base.mkdir(exist_ok=True)
    run_id = slug()
    output = output_base / run_id
    output.mkdir(exist_ok=False)
    started = utc_now()

    blocking: list[str] = []
    classification_mode = BLOCKED_PREWRITE
    state = "install_blocked_fail_closed_no_runtime_write"
    staging: Path | None = None
    committed = False
    install_attempted = False
    install_completed = False
    boundary_before: dict[str, Any] | None = None
    runtime_parent: Path | None = None
    runtime_parent_created = False
    installed_inventory: dict[str, Any] = {}
    pe_report: dict[str, Any] = {}
    all_data: dict[str, Any] = {}
    resumed_existing_staging = False
    resume_verification: dict[str, Any] = {}
    seal_failed = False

    try:
        self_verification = verify_self(package)
        approval = verify_approval(package)
        runtime = verify_portable_identity(root)
        write_json(output / "package_verification.json", self_verification)
        write_json(output / "operator_approval.json", approval)
        write_json(output / "runtime_identity.json", runtime)

        final_target = root / FINAL_REL
        runtime_wheelhouse = root / RUNTIME_WHEELHOUSE_REL
        runtime_parent_path = root / "Runtime/ComfyUI"
        existing_staging = sorted(
            runtime_parent_path.glob(".C3E_site-packages_staging_*")
        ) if runtime_parent_path.is_dir() else []
        if final_target.exists():
            raise RuntimeError(f"Final target already exists; C3E refuses overwrite or merge: {final_target}")
        if runtime_wheelhouse.exists():
            raise RuntimeError(f"Runtime wheelhouse unexpectedly exists: {runtime_wheelhouse}")
        if len(existing_staging) > 1:
            raise RuntimeError(
                f"Multiple C3E staging directories require manual review: {[str(p) for p in existing_staging]}"
            )
        if existing_staging:
            staging = existing_staging[0]
            resume_verification = verify_resume_transaction(
                package, staging, final_target, output
            )
            resumed_existing_staging = True
            classification_mode = BLOCKED_STAGING
            state = "install_blocked_fail_closed_staging_preserved"
            write_json(output / "resume_input_verification.json", resume_verification)

        c3d_folder, c3d_verification = find_exact_c3d(root)
        write_json(output / "c3d_input_verification.json", c3d_verification)
        wheelhouse = root / C3C_WHEELHOUSE_REL
        rows, requirements, lock = load_lock(c3d_folder, wheelhouse)
        write_json(output / "exact_install_lock_summary.json", {"verified": True, "entry_count": len(rows), "requirements": str(requirements), "requirements_sha256": sha256_file(requirements), "lock_sha256": sha256_file(c3d_folder / "exact_install_lock.json"), "entries": rows})

        wheel_before = verify_wheelhouse(rows, wheelhouse)
        write_json(output / "wheelhouse_before_install.json", wheel_before)
        host = verify_host_installer(output)
        write_json(output / "installer_identity_before.json", host)
        processes = process_safety_check(root, output)
        write_json(output / "process_safety.json", processes)
        space = disk_space(root)
        write_json(output / "space_before.json", space)

        boundary_before = snapshot_boundaries(root)
        write_json(output / "boundary_before.json", boundary_before)
        expected_staging = [str(staging)] if resumed_existing_staging and staging else []
        if (
            boundary_before["final_target_exists"]
            or boundary_before["runtime_wheelhouse_exists"]
            or boundary_before["c3e_staging_directories"] != expected_staging
        ):
            raise RuntimeError(
                f"Boundary precondition failed: expected_staging={expected_staging}, observed={boundary_before}"
            )

        runtime_parent, runtime_parent_created = prepare_transaction_parent(root)
        if runtime_parent_created:
            classification_mode = BLOCKED_PARENT
            state = "install_blocked_fail_closed_runtime_parent_preserved"
        write_json(output / "transaction_parent.json", {
            "path": str(runtime_parent),
            "created_by_this_run": runtime_parent_created,
            "created_by_prior_c3e": resume_verification.get("runtime_parent_created_by_prior_c3e", False),
            "exists": runtime_parent.is_dir(),
            "authorized_scope": "Create exactly Runtime/ComfyUI only when Runtime already exists and the parent is absent.",
        })

        if resumed_existing_staging:
            if staging is None:
                raise RuntimeError("Resume mode was selected without an exact staging target")
            if staging.parent != runtime_parent:
                raise RuntimeError(
                    f"Preserved staging target is outside the approved runtime parent: {staging}"
                )
            classification_mode = BLOCKED_STAGING
            state = "install_blocked_fail_closed_staging_preserved"
            install_completed = True
            write_json(output / "transaction_target.json", {
                "created": False,
                "resumed": True,
                "staging": str(staging),
                "final": str(final_target),
                "same_parent": staging.parent == final_target.parent,
                "same_volume": staging.drive.casefold() == final_target.drive.casefold(),
                "runtime_parent_created_by_c3e": runtime_parent_created,
                "prior_run_id": resume_verification.get("run_id"),
            })
            write_json(output / "pip_install_execution.json", {
                "skipped": True,
                "reason": "Exact preserved staging target resumed after prior offline pip return code 0",
                "network_allowed": False,
                "target": str(staging),
                "prior_output": resume_verification.get("prior_output"),
                "prior_pip_execution_sha256": resume_verification.get("prior_pip_execution_sha256"),
            })
        else:
            staging = runtime_parent / f".C3E_site-packages_staging_{run_id}"
            staging.mkdir(exist_ok=False)
            classification_mode = BLOCKED_STAGING
            state = "install_blocked_fail_closed_staging_preserved"
            write_json(output / "transaction_target.json", {
                "created": True,
                "resumed": False,
                "staging": str(staging),
                "final": str(final_target),
                "same_parent": staging.parent == final_target.parent,
                "same_volume": staging.drive.casefold() == final_target.drive.casefold(),
                "runtime_parent_created_by_c3e": runtime_parent_created,
            })

            pip_temp = output / "PIP_TEMP"
            pip_cache = output / "PIP_CACHE"
            shutil.rmtree(pip_temp, ignore_errors=True)
            shutil.rmtree(pip_cache, ignore_errors=True)
            pip_temp.mkdir(exist_ok=False)
            pip_cache.mkdir(exist_ok=False)
            env = clean_env(output)
            command = [
                str(EXPECTED_HOST_PYTHON), "-I", "-B", "-m", "pip", "--isolated", "--disable-pip-version-check",
                "install", "--ignore-installed", "--no-index", "--no-deps", "--only-binary=:all:", "--require-hashes",
                "--no-cache-dir", "--no-compile", "--progress-bar", "off", "--target", str(staging), "-r", str(requirements),
            ]
            install_attempted = True
            install = run_command(command, output, env, 3600)
            (output / "pip_install_stdout.txt").write_text(install["stdout"], encoding="utf-8", newline="\n")
            (output / "pip_install_stderr.txt").write_text(install["stderr"], encoding="utf-8", newline="\n")
            install_summary = {k: v for k, v in install.items() if k not in {"stdout", "stderr"}}
            install_summary.update({"stdout_file": "pip_install_stdout.txt", "stderr_file": "pip_install_stderr.txt", "network_allowed": False, "target": str(staging)})
            write_json(output / "pip_install_execution.json", install_summary)
            shutil.rmtree(pip_temp, ignore_errors=True)
            shutil.rmtree(pip_cache, ignore_errors=True)
            if install["returncode"] != 0:
                raise RuntimeError(f"Exact offline pip install failed with return code {install['returncode']}")
            install_completed = True

        host_after = verify_host_installer(output)
        wheel_after = verify_wheelhouse(rows, wheelhouse)
        write_json(output / "installer_identity_after.json", host_after)
        write_json(output / "wheelhouse_after_install.json", wheel_after)
        if wheel_before["wheels"] != wheel_after["wheels"]:
            raise RuntimeError("C3C wheelhouse changed during installation")

        installed_inventory, pe_report = inventory_target(staging)
        write_json(output / "installed_file_inventory_precommit.json", installed_inventory)
        write_json(output / "pe_binary_verification_precommit.json", pe_report)

        pre_exec, pre_verify = portable_verify(root, package, staging, c3d_folder / "exact_install_lock.json", output, "precommit")
        write_json(output / "portable_verification_precommit_execution.json", pre_exec)
        precommit_inventory_after_verify, precommit_pe_after_verify = inventory_target(staging)
        write_json(output / "installed_file_inventory_precommit_after_verification.json", precommit_inventory_after_verify)
        write_json(output / "pe_binary_verification_precommit_after_verification.json", precommit_pe_after_verify)
        if (precommit_inventory_after_verify["tree_sha256"] != installed_inventory["tree_sha256"]
                or precommit_inventory_after_verify["file_count"] != installed_inventory["file_count"]
                or precommit_inventory_after_verify["total_bytes"] != installed_inventory["total_bytes"]):
            raise RuntimeError("Portable pre-commit verification modified the candidate target")
        installed_inventory = precommit_inventory_after_verify
        pe_report = precommit_pe_after_verify

        boundary_precommit = snapshot_boundaries(root)
        write_json(output / "boundary_precommit.json", boundary_precommit)
        boundary_precommit_comparison = compare_boundaries(boundary_before, boundary_precommit)
        write_json(output / "boundary_precommit_comparison.json", boundary_precommit_comparison)
        if not boundary_precommit_comparison["verified"]:
            raise RuntimeError(f"Protected boundaries changed before commit: {boundary_precommit_comparison}")
        if final_target.exists():
            raise RuntimeError("Final target appeared before commit")
        current_staging = sorted((root / "Runtime/ComfyUI").glob(".C3E_site-packages_staging_*"))
        if current_staging != [staging]:
            raise RuntimeError(f"Unexpected C3E staging state before commit: {[str(p) for p in current_staging]}")

        # Commit is authorized only now: same parent, same volume, final absent.
        if staging.parent != final_target.parent or staging.drive.casefold() != final_target.drive.casefold():
            raise RuntimeError("Staging and final targets are not on the same parent/volume")
        os.rename(staging, final_target)
        committed = True
        classification_mode = BLOCKED_COMMITTED
        state = "installed_committed_but_postcommit_review_failed"
        write_json(output / "commit_receipt.json", {"committed": True, "method": "os.rename same-volume directory rename", "from": str(staging), "to": str(final_target), "committed_utc": iso_now(), "staging_exists_after": staging.exists(), "final_exists_after": final_target.is_dir()})
        if staging.exists() or not final_target.is_dir():
            raise RuntimeError("Same-volume commit rename did not produce the expected final state")

        post_inventory, post_pe = inventory_target(final_target)
        write_json(output / "installed_file_inventory_postcommit.json", post_inventory)
        write_json(output / "pe_binary_verification_postcommit.json", post_pe)
        if post_inventory["tree_sha256"] != installed_inventory["tree_sha256"] or post_inventory["file_count"] != installed_inventory["file_count"] or post_inventory["total_bytes"] != installed_inventory["total_bytes"]:
            raise RuntimeError("Committed target inventory differs from verified staging inventory")

        post_exec, post_verify = portable_verify(root, package, final_target, c3d_folder / "exact_install_lock.json", output, "postcommit")
        write_json(output / "portable_verification_postcommit_execution.json", post_exec)
        final_inventory_after_verify, final_pe_after_verify = inventory_target(final_target)
        write_json(output / "installed_file_inventory_final.json", final_inventory_after_verify)
        write_json(output / "pe_binary_verification_final.json", final_pe_after_verify)
        if (final_inventory_after_verify["tree_sha256"] != installed_inventory["tree_sha256"]
                or final_inventory_after_verify["file_count"] != installed_inventory["file_count"]
                or final_inventory_after_verify["total_bytes"] != installed_inventory["total_bytes"]):
            raise RuntimeError("Portable post-commit verification modified the committed isolated target")

        boundary_after = snapshot_boundaries(root)
        write_json(output / "boundary_after.json", boundary_after)
        boundary_comparison = compare_boundaries(boundary_before, boundary_after)
        write_json(output / "boundary_comparison.json", boundary_comparison)
        if not boundary_comparison["verified"]:
            raise RuntimeError(f"Protected boundaries changed during C3E: {boundary_comparison}")
        if boundary_after["runtime_wheelhouse_exists"] or boundary_after["c3e_staging_directories"] or not boundary_after["final_target_exists"]:
            raise RuntimeError(f"Final authorized boundary state is incorrect: {boundary_after}")

        classification_mode = SUCCESS
        state = "installed_verified_committed_ready_for_exact_review"
        all_data.update({"pre_verify": pre_verify, "post_verify": post_verify})

    except Exception as exc:
        blocking.append(f"{type(exc).__name__}: {exc}")
        (output / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8", newline="\n")

    finally:
        try:
            boundary_final = snapshot_boundaries(root)
            write_json(output / "boundary_final_observed.json", boundary_final)
            if boundary_before is not None:
                final_comparison = compare_boundaries(boundary_before, boundary_final)
                write_json(output / "boundary_final_protected_comparison.json", final_comparison)
                if not final_comparison["verified"]:
                    blocking.append("Protected boundary comparison failed in finalization")
        except Exception as exc:
            blocking.append(f"Final boundary snapshot failed: {type(exc).__name__}: {exc}")

        verified = classification_mode == SUCCESS and not blocking
        if blocking and classification_mode == SUCCESS:
            classification_mode = BLOCKED_COMMITTED if committed else BLOCKED_STAGING if staging and staging.exists() else BLOCKED_PARENT if runtime_parent_created else BLOCKED_PREWRITE
            state = "install_blocked_fail_closed"
        rollback_state = {
            "automatic_cleanup_performed": False,
            "automatic_rollback_performed": False,
            "staging_target": str(staging) if staging else None,
            "staging_exists": bool(staging and staging.exists()),
            "runtime_parent": str(runtime_parent) if runtime_parent else str(root / "Runtime/ComfyUI"),
            "runtime_parent_created_by_c3e": runtime_parent_created,
            "runtime_parent_created_by_prior_c3e": resume_verification.get("runtime_parent_created_by_prior_c3e", False),
            "runtime_parent_exists": (root / "Runtime/ComfyUI").is_dir(),
            "final_target": str(root / FINAL_REL),
            "final_target_exists": (root / FINAL_REL).is_dir(),
            "final_target_committed": committed,
            "operator_action": (
                "Preserve the failed staging target unchanged for exact review; do not delete it."
                if staging and staging.exists() else
                "Preserve the committed isolated target disabled from launchers for exact review."
                if committed else
                "Preserve the newly created empty Runtime/ComfyUI parent for exact review; no package installation was attempted."
                if runtime_parent_created else
                "No Runtime/ComfyUI installation tree was created."
            ),
            "forbidden": [
                "Do not run pip uninstall against Desktop, Core, host Python, staging, or final target",
                "Do not delete the C3C wheelhouse",
                "Do not edit launchers or launch ComfyUI",
                "Do not merge a staging target into any existing directory",
            ],
        }
        write_json(output / "rollback_state.json", rollback_state)
        classification = {
            "mode": classification_mode,
            "verified": verified,
            "blocking_findings": list(dict.fromkeys(blocking)),
            "operator_approval": APPROVAL_TEXT,
            "staging_preserved": bool(staging and staging.exists()),
            "resumed_existing_staging": resumed_existing_staging,
            "runtime_parent_created_by_c3e": runtime_parent_created,
            "final_target_committed": committed,
            "launcher_change": False,
            "network_access": False,
            "comfyui_launched": False,
            "next_gate": "Upload UPLOAD_THIS_C3E_REVIEW.zip for exact review. Do not edit launchers or launch ComfyUI.",
        }
        write_json(output / "classification.json", classification)
        completed = utc_now()
        receipt = {
            "action": ACTION,
            "state": state,
            "started": started.isoformat(),
            "completed": completed.isoformat(),
            "elapsed_seconds": round((completed - started).total_seconds(), 3),
            "verified": verified,
            "classification": classification_mode,
            "root": str(root),
            "staging_target": str(staging) if staging else None,
            "staging_exists": bool(staging and staging.exists()),
            "runtime_parent": str(runtime_parent) if runtime_parent else str(root / "Runtime/ComfyUI"),
            "runtime_parent_created_by_c3e": runtime_parent_created,
            "runtime_parent_created_by_prior_c3e": resume_verification.get("runtime_parent_created_by_prior_c3e", False),
            "runtime_parent_exists": (root / "Runtime/ComfyUI").is_dir(),
            "final_target": str(root / FINAL_REL),
            "final_target_committed": committed,
            "final_target_exists": (root / FINAL_REL).is_dir(),
            "runtime_wheelhouse_exists": (root / RUNTIME_WHEELHOUSE_REL).exists(),
            "exact_package_count": EXPECTED_COUNT,
            "exact_compressed_wheel_bytes": EXPECTED_COMPRESSED,
            "reviewed_uncompressed_payload_bytes": EXPECTED_UNCOMPRESSED,
            "installed_file_count": installed_inventory.get("file_count"),
            "installed_bytes": installed_inventory.get("total_bytes"),
            "installed_tree_sha256": installed_inventory.get("tree_sha256"),
            "pe_binary_count": pe_report.get("binary_count"),
            "pe_current_architecture_binary_count": pe_report.get("current_architecture_binary_count"),
            "pe_reviewed_non_current_resource_count": pe_report.get("reviewed_non_current_resource_count"),
            "package_install_attempted": install_attempted,
            "package_install_completed": install_completed,
            "resumed_existing_staging": resumed_existing_staging,
            "resume_prior_output": resume_verification.get("prior_output") if resume_verification else None,
            "package_install_reused_from_prior_run": resumed_existing_staging,
            "package_uninstall": False,
            "network_access": False,
            "launcher_change": False,
            "foxai_launched": False,
            "webui_launched": False,
            "desktop_launched": False,
            "comfyui_launched": False,
            "automatic_cleanup": False,
            "automatic_rollback": False,
            "blocking_findings": classification["blocking_findings"],
        }
        write_json(output / "receipt.json", receipt)
        (output / "report.md").write_text(build_report(receipt, classification), encoding="utf-8", newline="\n")
        for temporary in [output / "PIP_TEMP", output / "PIP_CACHE", output / "OFFLINE_CACHE"]:
            shutil.rmtree(temporary, ignore_errors=True)
        try:
            review_zip, review_hash = seal_evidence(output)
            print(f"C3E review bundle: {review_zip}")
            print(f"C3E review bundle SHA-256: {review_hash}")
        except Exception as exc:
            seal_failed = True
            print(f"WARNING: could not create review bundle: {type(exc).__name__}: {exc}", file=sys.stderr)

    if seal_failed:
        return 9
    return 0 if classification_mode == SUCCESS and not blocking else 2


if __name__ == "__main__":
    raise SystemExit(main())
