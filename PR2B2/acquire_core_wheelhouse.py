from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from email.parser import Parser
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
LOCK_PATH = PACKAGE / "WHEELHOUSE_LOCK.json"
REPORT_ROOT = ROOT / "Reports" / "PortableRuntime"
WHEELHOUSE_ROOT = ROOT / "Wheelhouse" / "Core"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirement_name(value: str) -> str:
    value = value.split(";", 1)[0].strip()
    value = value.split("[", 1)[0].strip()
    match = re.match(r"([A-Za-z0-9_.-]+)", value)
    return normalize(match.group(1)) if match else ""


def version_tuple(value: str) -> tuple[int, ...]:
    parts = []
    for chunk in re.split(r"[._-]", value):
        match = re.match(r"(\d+)", chunk)
        if not match:
            break
        parts.append(int(match.group(1)))
    return tuple(parts)


def python_satisfies(spec: str | None, target=(3, 14, 6)) -> bool:
    if not spec:
        return True
    for term in spec.split(","):
        term = term.strip()
        match = re.match(r"(>=|<=|==|!=|>|<)\s*([0-9.]+)", term)
        if not match:
            continue
        op, raw = match.groups()
        wanted = version_tuple(raw)
        current = target[:len(wanted)]
        if op == ">=" and not current >= wanted:
            return False
        if op == "<=" and not current <= wanted:
            return False
        if op == ">" and not current > wanted:
            return False
        if op == "<" and not current < wanted:
            return False
        if op == "==" and not current == wanted:
            return False
        if op == "!=" and not current != wanted:
            return False
    return True


def powershell_download(url: str, destination: Path) -> dict:
    destination_text = str(destination).replace("'", "''")
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "$ErrorActionPreference='Stop';"
            "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;"
            f"Invoke-WebRequest -UseBasicParsing -Uri '{url}' "
            f"-OutFile '{destination_text}'"
        ),
    ]
    process = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    return {
        "returncode": process.returncode,
        "stdout": process.stdout[-2000:],
        "stderr": process.stderr[-4000:],
    }


def wheel_metadata(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        metadata_names = [
            name for name in archive.namelist()
            if name.endswith(".dist-info/METADATA")
        ]
        wheel_names = [
            name for name in archive.namelist()
            if name.endswith(".dist-info/WHEEL")
        ]
        if len(metadata_names) != 1 or len(wheel_names) != 1:
            raise RuntimeError(f"Unexpected wheel metadata layout: {path.name}")
        metadata_text = archive.read(metadata_names[0]).decode("utf-8", "replace")
        wheel_text = archive.read(wheel_names[0]).decode("utf-8", "replace")

    message = Parser().parsestr(metadata_text)
    requirements = message.get_all("Requires-Dist", [])
    tags = [
        line.split(":", 1)[1].strip()
        for line in wheel_text.splitlines()
        if line.startswith("Tag:")
    ]
    return {
        "name": message.get("Name"),
        "version": message.get("Version"),
        "requires_python": message.get("Requires-Python"),
        "requires_dist": requirements,
        "requires_dist_names": sorted({
            parse_requirement_name(item)
            for item in requirements
            if parse_requirement_name(item)
        }),
        "tags": tags,
    }


def allowed_filename(filename: str) -> bool:
    return filename.endswith("-py3-none-any.whl") or filename.endswith(
        "-py3-none-win_amd64.whl"
    ) or filename.endswith("-cp37-abi3-win_amd64.whl")


def write_markdown(receipt: dict, path: Path) -> None:
    lines = [
        "# FOXAI Portable Runtime Phase 2B2 — Wheelhouse Acquisition",
        "",
        f"- Created: `{receipt['created']}`",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Wheels: **{len(receipt.get('wheels', []))}**",
        "- Live runtime installed: **False**",
        "- Launcher changed: **False**",
        "- Configuration changed: **False**",
        "",
        "## Wheel results",
        "",
    ]
    for item in receipt.get("wheels", []):
        lines.append(
            f"- `{item['filename']}` — hash: "
            f"{'PASS' if item.get('hash_ok') else 'FAIL'}, "
            f"metadata: {'PASS' if item.get('metadata_ok') else 'FAIL'}"
        )
    lines += [
        "",
        "## Staging import test",
        "",
        f"- Passed: **{receipt.get('staging_test', {}).get('passed', False)}**",
        f"- Staging path: `{receipt.get('staging_path', '')}`",
        "",
        "## Safety",
        "",
        "The downloaded wheels and extracted staging tree are quarantined.",
        "Nothing was installed into the live FOXAI Python runtime and no launcher,",
        "source, configuration, registry, model, or security file was modified.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    stamp = datetime.now().strftime("PR2B2_%Y%m%dT%H%M%S")
    incoming = WHEELHOUSE_ROOT / "incoming" / stamp
    verified_dir = WHEELHOUSE_ROOT / "verified" / stamp
    staging = WHEELHOUSE_ROOT / "staging" / stamp / "site-packages"
    report_dir = REPORT_ROOT / stamp

    for path in (incoming, verified_dir, staging, report_dir):
        if path.exists():
            raise RuntimeError(f"Refusing to reuse existing path: {path}")
        path.mkdir(parents=True)

    receipt = {
        "action": "foxai_portable_runtime_phase2b2_acquisition",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "root": str(ROOT),
        "network_downloads": True,
        "official_pypi_files_only": True,
        "live_runtime_installed": False,
        "source_or_config_modified": False,
        "launcher_modified": False,
        "delete_operations": [],
        "incoming_path": str(incoming),
        "verified_path": str(verified_dir),
        "staging_path": str(staging),
        "report_path": str(report_dir),
        "wheels": [],
        "live_baselines": [],
        "staging_test": {},
        "failure": None,
    }

    try:
        for relative, expected in lock["live_baselines"].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            item = {
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            }
            receipt["live_baselines"].append(item)
            if not item["ok"]:
                raise RuntimeError(f"Live baseline changed: {relative}")

        metadata_by_name = {}

        for item in lock["wheels"]:
            destination = incoming / item["filename"]
            download = powershell_download(item["url"], destination)
            wheel_result = {
                "name": item["name"],
                "version": item["version"],
                "filename": item["filename"],
                "url": item["url"],
                "expected_sha256": item["sha256"],
                "download": download,
                "hash_ok": False,
                "metadata_ok": False,
            }
            receipt["wheels"].append(wheel_result)

            if download["returncode"] != 0 or not destination.is_file():
                raise RuntimeError(
                    f"Download failed for {item['filename']}: "
                    f"{download['stderr']}"
                )

            actual = sha256(destination)
            wheel_result["actual_sha256"] = actual
            wheel_result["hash_ok"] = actual == item["sha256"]
            wheel_result["size_bytes"] = destination.stat().st_size
            if not wheel_result["hash_ok"]:
                raise RuntimeError(f"Hash mismatch: {item['filename']}")

            if not allowed_filename(item["filename"]):
                raise RuntimeError(f"Wheel tag is outside policy: {item['filename']}")

            metadata = wheel_metadata(destination)
            wheel_result["metadata"] = metadata
            expected_name = normalize(item["name"])
            metadata_ok = (
                normalize(metadata["name"] or "") == expected_name
                and metadata["version"] == item["version"]
                and python_satisfies(metadata["requires_python"])
            )
            wheel_result["metadata_ok"] = metadata_ok
            if not metadata_ok:
                raise RuntimeError(f"Metadata mismatch: {item['filename']}")
            metadata_by_name[expected_name] = metadata

        for parent, expected_dependencies in lock["dependency_contract"].items():
            parent_metadata = metadata_by_name.get(normalize(parent))
            if not parent_metadata:
                raise RuntimeError(f"Missing parent metadata: {parent}")
            actual_dependencies = set(parent_metadata["requires_dist_names"])
            missing = [
                dependency for dependency in expected_dependencies
                if normalize(dependency) not in actual_dependencies
            ]
            if missing:
                raise RuntimeError(
                    f"Dependency contract mismatch for {parent}: {missing}"
                )

        for item in lock["wheels"]:
            source = incoming / item["filename"]
            shutil.copy2(source, verified_dir / item["filename"])
            with zipfile.ZipFile(source) as archive:
                archive.extractall(staging)

        python = ROOT / "env/python/python.exe"
        process = subprocess.run(
            [
                str(python),
                "-s",
                str(PACKAGE / "staging_import_test.py"),
                str(staging),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        receipt["staging_test"] = {
            "returncode": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "passed": False,
        }
        if process.stdout.strip():
            try:
                payload = json.loads(process.stdout)
                receipt["staging_test"].update(payload)
            except Exception:
                pass
        if process.returncode != 0 or not receipt["staging_test"].get("passed"):
            raise RuntimeError(
                "Staging import test failed: "
                + (process.stderr[-3000:] or process.stdout[-3000:])
            )

        receipt["state"] = "quarantined_wheelhouse_verified"
        receipt["verified"] = True

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    receipt_path = report_dir / "receipt.json"
    report_path = report_dir / "report.md"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    write_markdown(receipt, report_path)

    print("=" * 72)
    print("FOXAI PORTABLE RUNTIME PHASE 2B2")
    print("=" * 72)
    print(f"State: {receipt['state']}")
    print(f"Verified: {receipt['verified']}")
    print("Live runtime installed: False")
    print(f"Report: {report_dir}")
    if receipt["failure"]:
        print(f"Failure: {receipt['failure']['message']}")
    return 0 if receipt["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
