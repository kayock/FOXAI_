from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APPROVAL_PHRASE = "DOWNLOAD OFFICIAL QWEN3VL Q8 MMPROJ"

SOURCE_REPO = "Qwen/Qwen3-VL-8B-Instruct-GGUF"
SOURCE_COMMIT = "00e7d63528e65d7b64e80e1293a8360b4af6a594"
FILENAME = "mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf"
SOURCE_URL = (
    "https://huggingface.co/"
    f"{SOURCE_REPO}/resolve/{SOURCE_COMMIT}/{FILENAME}"
    "?download=true"
)
EXPECTED_SHA256 = (
    "c6ba85508d82f42590e6eb77d5340369ab6fecf107a7561d809523d8aa5f3bfd"
)

TARGET_RELATIVE = f"Models/Chat/{FILENAME}"
PART_SUFFIX = ".part"
CHUNK_SIZE = 4 * 1024 * 1024
TIMEOUT = 120
MAX_RETRIES = 8

LOCKED_HASHES = {
    "core/foxai_web.py":
        "e4d5811f14ae3ffb0b3f8b59369bee5c0a1218d19459f2decc875589540d04fb",
    "core/server.py":
        "9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07",
    "Engine/llama-server.exe":
        "936cfb77f011911f879a5af715013eb12141115547c1f731114d8e9c20ebd89e",
}

MODEL_EXPECTATIONS = {
    "Models/Chat/Qwen3VL-8B-Instruct-Q4_K_M.gguf": 5027784800,
    "Models/Chat/Qwen3VL-8B-Instruct-Q8_0.gguf": 8709519456,
}


class InstallError(RuntimeError):
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
    raise InstallError(
        r"FOXAI root not found. Extract the complete MMQ8A folder directly inside Z:\FOXAI."
    )


def checkpoint(path: Path, receipt: dict[str, Any]) -> None:
    stage = path.with_suffix(path.suffix + ".tmp")
    stage.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )
    os.replace(stage, path)


def package_manifest(package_dir: Path) -> dict[str, Any]:
    manifest = package_dir / "sums.txt"
    if not manifest.is_file():
        raise InstallError("Package manifest is missing.")
    checks = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = package_dir / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected": digest,
            "actual": actual,
            "ok": actual == digest,
        })
    if not checks or not all(item["ok"] for item in checks):
        raise InstallError("Package manifest verification failed.")
    return {"passed": True, "files": checks}


def verify_live(root: Path) -> dict[str, Any]:
    files = []
    for relative, expected in LOCKED_HASHES.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        files.append({
            "path": relative,
            "expected": expected,
            "actual": actual,
            "ok": actual == expected,
        })
    for relative, expected_size in MODEL_EXPECTATIONS.items():
        path = root / relative
        size = path.stat().st_size if path.is_file() else None
        files.append({
            "path": relative,
            "expected_size": expected_size,
            "actual_size": size,
            "ok": size == expected_size,
        })
    if not all(item["ok"] for item in files):
        raise InstallError(
            "A locked FOXAI source, engine, or Qwen3VL model identity changed."
        )
    return {"passed": True, "files": files}


def download_with_resume(
    url: str,
    part: Path,
    receipt_path: Path,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    part.parent.mkdir(parents=True, exist_ok=True)
    retries = 0
    total_written = part.stat().st_size if part.is_file() else 0
    initial_size = total_written
    last_checkpoint = time.monotonic()

    while True:
        headers = {
            "User-Agent": "FOXAI-Qwen3VL-mmproj-installer/1.0",
        }
        if total_written > 0:
            headers["Range"] = f"bytes={total_written}-"

        request = urllib.request.Request(
            url,
            headers=headers,
            method="GET",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=TIMEOUT,
            ) as response:
                status = getattr(response, "status", 200)
                if total_written > 0 and status != 206:
                    # Server ignored resume. Restart the temporary download only.
                    with part.open("wb"):
                        pass
                    total_written = 0
                    receipt["download"]["resume_restarted"] = True
                    checkpoint(receipt_path, receipt)
                    continue

                mode = "ab" if total_written > 0 else "wb"
                content_length = response.headers.get("Content-Length")
                remote_remaining = (
                    int(content_length)
                    if content_length and content_length.isdigit()
                    else None
                )
                expected_total = (
                    total_written + remote_remaining
                    if remote_remaining is not None
                    else None
                )
                receipt["download"].update({
                    "http_status": status,
                    "expected_total_bytes": expected_total,
                    "resumed_from_bytes": initial_size,
                })
                checkpoint(receipt_path, receipt)

                with part.open(mode) as handle:
                    while True:
                        block = response.read(CHUNK_SIZE)
                        if not block:
                            break
                        handle.write(block)
                        handle.flush()
                        total_written += len(block)

                        now = time.monotonic()
                        if now - last_checkpoint >= 5:
                            receipt["download"]["downloaded_bytes"] = total_written
                            checkpoint(receipt_path, receipt)
                            if expected_total:
                                percent = 100.0 * total_written / expected_total
                                print(
                                    f"\rDownloaded {total_written:,} / "
                                    f"{expected_total:,} bytes "
                                    f"({percent:5.1f}%)",
                                    end="",
                                    flush=True,
                                )
                            else:
                                print(
                                    f"\rDownloaded {total_written:,} bytes",
                                    end="",
                                    flush=True,
                                )
                            last_checkpoint = now

                print()
                receipt["download"]["downloaded_bytes"] = total_written
                checkpoint(receipt_path, receipt)
                return {
                    "downloaded_bytes": total_written,
                    "resumed_from_bytes": initial_size,
                    "expected_total_bytes": expected_total,
                    "http_status": status,
                }

        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            OSError,
        ) as exc:
            retries += 1
            receipt["download"]["retries"] = retries
            receipt["download"]["last_network_error"] = (
                f"{type(exc).__name__}: {exc}"
            )
            receipt["download"]["downloaded_bytes"] = (
                part.stat().st_size if part.is_file() else 0
            )
            checkpoint(receipt_path, receipt)

            if retries > MAX_RETRIES:
                raise InstallError(
                    "Download stopped after repeated network errors. "
                    "The .part file was preserved for a future resume."
                ) from exc

            delay = min(30, 2 ** retries)
            print()
            print(
                f"Network interruption ({retries}/{MAX_RETRIES}); "
                f"retrying in {delay} seconds..."
            )
            time.sleep(delay)
            total_written = part.stat().st_size if part.is_file() else 0


def main() -> int:
    package_dir = Path(__file__).resolve().parent
    root = find_root(package_dir)
    receipt_path = package_dir / "RECEIPT.json"
    target = root / TARGET_RELATIVE
    part = target.with_name(target.name + PART_SUFFIX)

    receipt: dict[str, Any] = {
        "action": "install_official_qwen3vl_q8_mmproj",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "running",
        "verified": False,
        "operator_approved": False,
        "live_source_files_modified": False,
        "configuration_modified": False,
        "archive_modified": False,
        "delete_operations": [],
        "target": str(target),
        "source": {
            "repository": SOURCE_REPO,
            "commit": SOURCE_COMMIT,
            "filename": FILENAME,
            "url": SOURCE_URL,
            "expected_sha256": EXPECTED_SHA256,
        },
        "download": {
            "part_path": str(part),
            "downloaded_bytes": part.stat().st_size if part.is_file() else 0,
            "retries": 0,
        },
        "checks": {},
        "failure": None,
    }
    checkpoint(receipt_path, receipt)

    try:
        receipt["checks"]["package_manifest"] = package_manifest(package_dir)
        receipt["checks"]["live_identity"] = verify_live(root)
        checkpoint(receipt_path, receipt)

        if target.exists():
            if not target.is_file():
                raise InstallError(
                    "The intended projector target exists but is not a file."
                )
            existing_hash = sha256(target)
            receipt["checks"]["existing_target"] = {
                "exists": True,
                "sha256": existing_hash,
            }
            if existing_hash == EXPECTED_SHA256:
                receipt.update({
                    "state": "already_installed_verified",
                    "verified": True,
                    "operator_approved": False,
                    "installed_sha256": existing_hash,
                    "installed_size_bytes": target.stat().st_size,
                })
                checkpoint(receipt_path, receipt)
            else:
                raise InstallError(
                    "A different file already exists at the projector target. "
                    "Nothing was overwritten."
                )
        else:
            print()
            print("=" * 72)
            print("FOXAI QWEN3VL OFFICIAL VISION PROJECTOR")
            print("=" * 72)
            print()
            print("Official repository:", SOURCE_REPO)
            print("Pinned commit:", SOURCE_COMMIT)
            print("File:", FILENAME)
            print("Expected SHA-256:", EXPECTED_SHA256)
            print("Target:", target)
            print()
            print("This adds one model-support file and changes no source code.")
            print("A partial download is resumable and is never treated as installed.")
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
                })
                checkpoint(receipt_path, receipt)
            else:
                receipt["operator_approved"] = True
                checkpoint(receipt_path, receipt)

                receipt["download"]["state"] = "downloading"
                checkpoint(receipt_path, receipt)
                download_result = download_with_resume(
                    SOURCE_URL,
                    part,
                    receipt_path,
                    receipt,
                )
                receipt["download"].update(download_result)
                receipt["download"]["state"] = "download_complete"
                checkpoint(receipt_path, receipt)

                print("Verifying the complete projector SHA-256...")
                actual_hash = sha256(part)
                receipt["checks"]["download_sha256"] = {
                    "expected": EXPECTED_SHA256,
                    "actual": actual_hash,
                    "ok": actual_hash == EXPECTED_SHA256,
                }
                checkpoint(receipt_path, receipt)

                if actual_hash != EXPECTED_SHA256:
                    raise InstallError(
                        "Downloaded projector hash did not match the official "
                        "pinned file. The .part file was not installed."
                    )

                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(part, target)

                installed_hash = sha256(target)
                if installed_hash != EXPECTED_SHA256:
                    raise InstallError(
                        "Installed projector failed final hash verification."
                    )

                receipt.update({
                    "state": "installed_verified",
                    "verified": True,
                    "operator_approved": True,
                    "installed_sha256": installed_hash,
                    "installed_size_bytes": target.stat().st_size,
                    "live_source_files_modified": False,
                    "configuration_modified": False,
                    "archive_modified": False,
                    "delete_operations": [],
                })
                receipt["checks"]["final_target"] = {
                    "path": str(target),
                    "sha256": installed_hash,
                    "ok": True,
                }
                checkpoint(receipt_path, receipt)

    except Exception as exc:
        receipt.update({
            "state": "stopped_fail_closed",
            "verified": True,
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        })
        checkpoint(receipt_path, receipt)

    print()
    print("=" * 72)
    print("FOXAI QWEN3VL VISION PROJECTOR")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Operator approved:", receipt["operator_approved"])
    print("Live source files modified:", receipt["live_source_files_modified"])
    print("Target:", receipt["target"])
    if receipt.get("installed_sha256"):
        print("Installed SHA-256:", receipt["installed_sha256"])
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    print("Receipt:", receipt_path)
    print()
    print("Nothing is considered installed unless the state is:")
    print("  installed_verified")
    print("or:")
    print("  already_installed_verified")
    print()
    input("Press Enter to close...")

    return 0 if receipt["state"] in {
        "installed_verified",
        "already_installed_verified",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
