
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback
from typing import Any

REQUIRED_COMFY_DIRS = (
    Path("ComfyUI") / "custom_nodes",
    Path("ComfyUI") / "models",
    Path("ComfyUI") / "models" / "checkpoints",
    Path("ComfyUI") / "models" / "loras",
    Path("ComfyUI") / "models" / "vae",
    Path("ComfyUI") / "input",
    Path("ComfyUI") / "output",
    Path("ComfyUI") / "temp",
)

TEXT_SUFFIXES = {
    ".bat", ".cmd", ".ps1", ".py", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".txt", ".md"
}
MAX_CAPTURE_FILES = 30
MAX_CAPTURE_BYTES = 2 * 1024 * 1024
MAX_TEXT_SCAN_BYTES = 4 * 1024 * 1024


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(bundle: Path) -> dict[str, Any]:
    path = bundle / "PACKAGE_MANIFEST.json"
    result: dict[str, Any] = {"checked": 0, "failures": [], "passed": False}
    if not path.is_file():
        result["failures"].append("PACKAGE_MANIFEST.json missing")
        return result

    manifest = json.loads(path.read_text(encoding="utf-8"))
    for relative, expected in manifest.items():
        target = bundle / relative
        actual_hash = sha256_file(target)
        actual_size = target.stat().st_size if target.is_file() else None
        result["checked"] += 1
        if not (
            target.is_file()
            and actual_hash == expected["sha256"]
            and actual_size == expected["size_bytes"]
        ):
            result["failures"].append({
                "path": relative,
                "expected_sha256": expected["sha256"],
                "actual_sha256": actual_hash,
                "expected_size_bytes": expected["size_bytes"],
                "actual_size_bytes": actual_size,
            })
    result["passed"] = not result["failures"]
    return result


def safe_read_text(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_TEXT_SCAN_BYTES:
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return None


def path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def classify_python(path: Path, root: Path) -> str:
    resolved = path.resolve()
    if resolved == (root / "Runtime/Desktop/python/python.exe").resolve():
        return "USB_PORTABLE_DESKTOP"
    if resolved == (root / "env/python/python.exe").resolve():
        return "USB_LEGACY_EMBEDDED"
    if resolved == (root / ".venv/Scripts/python.exe").resolve():
        return "USB_VENV"
    if path_is_under(resolved, root):
        return "USB_OTHER"
    return "HOST"


def clean_probe_environment(root: Path, kind: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONHOME", None)
    if kind == "USB_PORTABLE_DESKTOP":
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONPATH"] = os.pathsep.join([
            str(root / "Runtime/Desktop/site-packages"),
            str(root / "Runtime/Core/site-packages"),
        ])
    elif kind.startswith("USB_"):
        env["PYTHONNOUSERSITE"] = "1"
        env.pop("PYTHONPATH", None)
    else:
        env.pop("PYTHONNOUSERSITE", None)
        env.pop("PYTHONPATH", None)
    return env


def discover_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.bat", "*.cmd", "*.ps1"):
        files.extend(root.glob(pattern))

    for fixed in (
        root / "core/foxai_web.py",
        root / "START_FOXAI_WORKSHOP_PORTABLE.bat",
        root / "START_FOXAI_WEB_PORTABLE.bat",
        root / "START_FOXAI_DESKTOP_PORTABLE.bat",
        root / "ComfyUI/main.py",
    ):
        if fixed.is_file():
            files.append(fixed)

    for folder in (root / "core", root / "System", root / "tools"):
        if not folder.is_dir():
            continue
        for path in folder.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in TEXT_SUFFIXES
                and path.stat().st_size <= MAX_TEXT_SCAN_BYTES
            ):
                files.append(path)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in files:
        try:
            key = str(path.resolve()).lower()
        except Exception:
            key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def find_comfy_sources(root: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    terms = ("comfy", "8188", "COMFY_MAIN", "--cpu", "torch")
    findings: list[dict[str, Any]] = []
    texts: dict[str, str] = {}

    for path in discover_source_files(root):
        text = safe_read_text(path)
        if text is None:
            continue
        lower = text.lower()
        if not any(term.lower() in lower for term in terms):
            continue

        relative = str(path.relative_to(root)).replace("\\", "/")
        matches = []
        for number, line in enumerate(text.splitlines(), start=1):
            if any(term.lower() in line.lower() for term in terms):
                matches.append({"line": number, "text": line})
        texts[relative] = text
        findings.append({
            "path": relative,
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
            "matching_line_count": len(matches),
            "matching_lines": matches[:250],
        })

    findings.sort(key=lambda item: item["path"].lower())
    return findings, texts


def discover_python_candidates(
    root: Path,
    source_texts: dict[str, str],
) -> list[dict[str, Any]]:
    candidates: list[Path] = [
        root / "Runtime/Desktop/python/python.exe",
        root / "env/python/python.exe",
        root / ".venv/Scripts/python.exe",
        Path(r"C:\Python314\python.exe"),
    ]

    found = shutil.which("python")
    if found:
        candidates.append(Path(found))

    try:
        result = subprocess.run(
            ["where", "python"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            candidates.extend(
                Path(line.strip())
                for line in result.stdout.splitlines()
                if line.strip()
            )
    except Exception:
        pass

    absolute_pattern = re.compile(r'(?i)([A-Z]:\\[^"\r\n]*?python\.exe)')
    for text in source_texts.values():
        for match in absolute_pattern.finditer(text):
            candidates.append(Path(match.group(1)))

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in candidates:
        try:
            key = str(path.resolve()).lower()
        except Exception:
            key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append({
            "path": str(path),
            "exists": path.is_file(),
            "kind": classify_python(path, root),
        })
    return unique


def torch_probe(executable: Path, root: Path, kind: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(executable),
        "kind": kind,
        "exists": executable.is_file(),
        "runs": False,
        "torch_available": False,
        "torch_origin_usb_owned": False,
        "error": None,
    }
    if not executable.is_file():
        return result

    probe = r'''
import json, os, platform, site, sys
data = {
    "executable": sys.executable,
    "version": sys.version,
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "enable_user_site": site.ENABLE_USER_SITE,
    "pythonpath": os.environ.get("PYTHONPATH"),
    "python_no_user_site": os.environ.get("PYTHONNOUSERSITE"),
    "platform": platform.platform(),
}
try:
    import torch
    data["torch"] = {
        "available": True,
        "version": getattr(torch, "__version__", None),
        "origin": getattr(torch, "__file__", None),
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_version": getattr(getattr(torch, "version", None), "cuda", None),
        "mkldnn_available": bool(
            getattr(getattr(torch.backends, "mkldnn", None), "is_available", lambda: False)()
        ),
        "threads": torch.get_num_threads(),
        "interop_threads": torch.get_num_interop_threads(),
    }
except Exception as exc:
    data["torch"] = {"available": False, "error": f"{type(exc).__name__}: {exc}"}

for module_name in ("torchvision", "torchaudio"):
    try:
        module = __import__(module_name)
        data[module_name] = {
            "available": True,
            "version": getattr(module, "__version__", None),
            "origin": getattr(module, "__file__", None),
        }
    except Exception as exc:
        data[module_name] = {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

print(json.dumps(data))
'''
    command = [str(executable)]
    if kind.startswith("USB_"):
        command.append("-s")
    command.extend(["-c", probe])

    try:
        process = subprocess.run(
            command,
            cwd=str(root),
            env=clean_probe_environment(root, kind),
            capture_output=True,
            text=True,
            timeout=45,
        )
        result["returncode"] = process.returncode
        result["stdout"] = process.stdout[-12000:]
        result["stderr"] = process.stderr[-12000:]
        if process.returncode != 0:
            result["error"] = (
                f"Interpreter returned {process.returncode}: "
                f"{process.stderr.strip()[-1000:]}"
            )
            return result

        payload = json.loads(process.stdout.strip().splitlines()[-1])
        result["runs"] = True
        result["details"] = payload
        torch_data = payload.get("torch") or {}
        result["torch_available"] = torch_data.get("available") is True
        origin = torch_data.get("origin")
        if origin:
            result["torch_origin_usb_owned"] = path_is_under(Path(origin), root)
        return result
    except subprocess.TimeoutExpired:
        result["error"] = "Torch probe timed out after 45 seconds."
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def copy_source_snapshots(
    root: Path,
    texts: dict[str, str],
    destination: Path,
) -> list[dict[str, Any]]:
    captured = []
    for relative in sorted(texts)[:MAX_CAPTURE_FILES]:
        source = root / relative
        if not source.is_file() or source.stat().st_size > MAX_CAPTURE_BYTES:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as src, target.open("xb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        captured.append({
            "path": relative,
            "sha256": sha256_file(target),
            "size_bytes": target.stat().st_size,
        })
    return captured


def directory_size(path: Path) -> dict[str, Any]:
    total = 0
    count = 0
    errors = []
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "size_bytes": 0,
            "file_count": 0,
            "errors": [],
        }

    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                            count += 1
                    except Exception as exc:
                        if len(errors) < 25:
                            errors.append(f"{entry.path}: {type(exc).__name__}: {exc}")
        except Exception as exc:
            if len(errors) < 25:
                errors.append(f"{current}: {type(exc).__name__}: {exc}")

    return {
        "path": str(path),
        "exists": True,
        "size_bytes": total,
        "file_count": count,
        "errors": errors,
    }


def comfy_inventory(root: Path) -> dict[str, Any]:
    comfy = root / "ComfyUI"
    required = []
    for relative in REQUIRED_COMFY_DIRS:
        path = root / relative
        required.append({
            "path": str(relative).replace("\\", "/"),
            "exists": path.is_dir(),
            "safe_create_candidate": not path.exists(),
        })

    top_level = []
    if comfy.is_dir():
        for child in sorted(comfy.iterdir(), key=lambda item: item.name.lower()):
            if child.is_dir():
                top_level.append(directory_size(child))
            elif child.is_file():
                top_level.append({
                    "path": str(child),
                    "exists": True,
                    "size_bytes": child.stat().st_size,
                    "file_count": 1,
                    "errors": [],
                })

    model_files = []
    models = comfy / "models"
    if models.is_dir():
        for path in models.rglob("*"):
            if path.is_file() and path.suffix.lower() in {
                ".safetensors", ".ckpt", ".pt", ".pth", ".bin",
                ".gguf", ".onnx"
            }:
                model_files.append({
                    "path": str(path.relative_to(root)).replace("\\", "/"),
                    "size_bytes": path.stat().st_size,
                })

    model_files.sort(key=lambda item: item["size_bytes"], reverse=True)
    missing = [item["path"] for item in required if not item["exists"]]
    return {
        "comfy_root": str(comfy),
        "comfy_exists": comfy.is_dir(),
        "required_directories": required,
        "missing_safe_directories": missing,
        "top_level_inventory": top_level,
        "model_files": model_files[:200],
        "model_file_count": len(model_files),
        "model_size_bytes": sum(item["size_bytes"] for item in model_files),
    }


def wheelhouse_inventory(root: Path) -> dict[str, Any]:
    folders = [
        root / "Wheelhouse",
        root / "wheelhouse",
        root / "Runtime/Wheelhouse",
        root / "Runtime/wheelhouse",
        root / "System/Wheelhouse",
        root / "System/wheelhouse",
        root / "wheels",
    ]
    scanned = []
    wheels = []
    for folder in folders:
        if not folder.is_dir():
            continue
        scanned.append(str(folder))
        for path in folder.rglob("*.whl"):
            name = path.name.lower()
            if any(token in name for token in (
                "torch", "torchvision", "torchaudio", "numpy",
                "safetensors", "tokenizers", "transformers"
            )):
                wheels.append({
                    "path": str(path.relative_to(root)).replace("\\", "/"),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                })
    wheels.sort(key=lambda item: item["path"].lower())
    return {
        "scanned_directories": scanned,
        "matching_wheels": wheels,
        "matching_wheel_count": len(wheels),
        "matching_wheel_size_bytes": sum(item["size_bytes"] for item in wheels),
    }


def torch_footprints(probes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    seen = set()
    for probe in probes:
        torch_data = (probe.get("details") or {}).get("torch") or {}
        origin = torch_data.get("origin")
        if not origin:
            continue
        package = Path(origin).parent
        try:
            key = str(package.resolve()).lower()
        except Exception:
            key = str(package).lower()
        if key in seen:
            continue
        seen.add(key)
        info = directory_size(package)
        info.update({
            "torch_version": torch_data.get("version"),
            "source_interpreter": probe.get("path"),
            "usb_owned": probe.get("torch_origin_usb_owned"),
        })
        output.append(info)
    return output


def classify(
    probes: list[dict[str, Any]],
    inventory: dict[str, Any],
) -> dict[str, Any]:
    portable = [
        probe for probe in probes
        if probe.get("kind") == "USB_PORTABLE_DESKTOP"
        and probe.get("torch_available")
        and probe.get("torch_origin_usb_owned")
    ]
    host = [
        probe for probe in probes
        if probe.get("kind") == "HOST"
        and probe.get("torch_available")
    ]
    missing = inventory.get("missing_safe_directories") or []

    if portable and not missing:
        mode = "PORTABLE_READY"
        blockers = []
    elif host:
        mode = "HOST_ASSISTED_READY"
        blockers = ["torch is not currently proven USB-owned for Creative Studio."]
    else:
        mode = "NEEDS_ATTENTION"
        blockers = ["No working torch runtime was found for Creative Studio."]

    notes = []
    if missing:
        notes.append("Missing safe-create directories: " + ", ".join(missing))
    if portable:
        notes.append("A USB-owned torch runtime was detected.")
    if host:
        notes.append("A host torch runtime was detected.")

    return {
        "mode": mode,
        "blocking_findings": blockers,
        "notes": notes,
        "next_gate": (
            "Prepare an exact safe-folder and portable-torch plan preview."
            if mode != "PORTABLE_READY"
            else "Verify a fully USB-owned ComfyUI launch."
        ),
    }


def report_markdown(
    receipt: dict[str, Any],
    result: dict[str, Any],
) -> str:
    classification = result.get("classification") or {}
    lines = [
        "# FOXAI USB C3",
        "## Creative Studio / ComfyUI Portability Preflight",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Root: `{receipt.get('root')}`",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        f"- Creative Studio mode: **{classification.get('mode')}**",
        "- Live FOXAI files modified: **False**",
        "- Install/download/repair/launch/network: **False**",
        "",
        "## Findings",
        "",
    ]
    for item in classification.get("blocking_findings") or []:
        lines.append(f"- BLOCKING: {item}")
    for item in classification.get("notes") or []:
        lines.append(f"- NOTE: {item}")
    lines += [
        "",
        "## Next gate",
        "",
        f"- {classification.get('next_gate')}",
        "",
        "Upload this entire `UPLOAD_THIS` folder for exact review.",
    ]
    if receipt.get("failure"):
        lines += ["", "## Failure", "", f"- `{receipt['failure']['message']}`"]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()

    started = now()
    root = Path(args.root).resolve()
    bundle = Path(args.bundle).resolve()
    output = bundle / "PREFLIGHT_OUTPUT" / started.strftime("%Y%m%dT%H%M%SZ")
    upload = output / "UPLOAD_THIS"
    snapshots = upload / "SOURCE_SNAPSHOTS"
    snapshots.mkdir(parents=True, exist_ok=True)

    receipt: dict[str, Any] = {
        "action": "foxai_usbc3_comfyui_portability_preflight",
        "created": started.isoformat(),
        "root": str(root),
        "state": "stopped_fail_closed",
        "verified": False,
        "read_only_preflight": True,
        "live_files_modified": False,
        "files_deleted": False,
        "files_overwritten": False,
        "missing_folders_created": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "desktop_launched": False,
        "comfyui_launched": False,
        "browser_launched": False,
        "writes_limited_to": str(output),
    }
    result: dict[str, Any] = {}
    rc = 1

    try:
        result["package_integrity"] = verify_manifest(bundle)
        if not result["package_integrity"]["passed"]:
            raise RuntimeError("C3 package integrity failed.")

        usage = shutil.disk_usage(root)
        result["usb_space"] = {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
        }

        findings, texts = find_comfy_sources(root)
        result["comfy_source_findings"] = findings
        result["captured_sources"] = copy_source_snapshots(
            root,
            texts,
            snapshots,
        )

        candidates = discover_python_candidates(root, texts)
        result["python_candidates"] = candidates

        probes = []
        for candidate in candidates:
            if not candidate["exists"]:
                probes.append({
                    **candidate,
                    "runs": False,
                    "torch_available": False,
                    "torch_origin_usb_owned": False,
                    "error": "Interpreter does not exist.",
                })
            else:
                probes.append(torch_probe(
                    Path(candidate["path"]),
                    root,
                    candidate["kind"],
                ))
        result["torch_probes"] = probes

        result["comfy_inventory"] = comfy_inventory(root)
        result["wheelhouse_inventory"] = wheelhouse_inventory(root)
        result["torch_footprints"] = torch_footprints(probes)
        result["classification"] = classify(
            probes,
            result["comfy_inventory"],
        )

        receipt["state"] = "preflight_complete_ready_for_exact_review"
        receipt["verified"] = True
        rc = 0

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    finally:
        completed = now()
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = round((completed - started).total_seconds(), 2)
        receipt["classification"] = (
            result.get("classification") or {}
        ).get("mode")

        outputs = {
            "receipt.json": receipt,
            "package_integrity.json": result.get("package_integrity", {}),
            "usb_space.json": result.get("usb_space", {}),
            "python_candidates.json": result.get("python_candidates", []),
            "torch_probes.json": result.get("torch_probes", []),
            "comfy_inventory.json": result.get("comfy_inventory", {}),
            "wheelhouse_inventory.json": result.get("wheelhouse_inventory", {}),
            "torch_footprints.json": result.get("torch_footprints", []),
            "comfy_source_findings.json": result.get("comfy_source_findings", []),
            "captured_sources.json": result.get("captured_sources", []),
            "classification.json": result.get("classification", {}),
        }
        for filename, data in outputs.items():
            (upload / filename).write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        (upload / "report.md").write_text(
            report_markdown(receipt, result),
            encoding="utf-8",
        )
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this entire UPLOAD_THIS folder. "
            "No live FOXAI file was modified.\n",
            encoding="utf-8",
        )

        print()
        print("USB C3 state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Creative Studio mode:", receipt.get("classification"))
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("No install, repair, folder creation, or launch occurred.")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
