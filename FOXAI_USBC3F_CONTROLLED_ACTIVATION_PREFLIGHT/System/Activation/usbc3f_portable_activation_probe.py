#!/usr/bin/env python3
"""No-launch portable activation probe for FOXAI USB C3F.

Run only with the protected portable CPython using -I -B -S. The probe adds the
committed isolated ComfyUI dependency target and the ComfyUI source directory,
blocks networking/process/server activity with an audit hook, compiles source
without writing bytecode, and imports the dependency/source modules needed to
prove an isolated launch can be wired safely. It never executes ComfyUI main.py.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import site
import sys
import traceback
from pathlib import Path
from typing import Any

BLOCKED_AUDIT_EVENTS = {
    "socket.bind",
    "socket.connect",
    "socket.connect_ex",
    "subprocess.Popen",
    "os.system",
    "os.startfile",
}
EXCLUDED_SOURCE_PARTS = {
    ".git", "__pycache__", "custom_nodes", "input", "output", "temp",
    "models", "user", "python_embeded", "venv", ".venv",
}
DEPENDENCY_IMPORTS = [
    "aiohttp", "av", "blake3", "cryptography", "huggingface_hub",
    "kornia", "numpy", "OpenGL", "OpenGL.GL", "PIL", "psutil",
    "safetensors", "scipy", "sentencepiece", "sqlalchemy", "tokenizers",
    "torch", "torchaudio", "torchvision", "transformers", "yaml",
]
COMFY_IMPORTS = [
    "folder_paths",
    "comfy.utils",
    "comfy.model_management",
    "comfy.model_detection",
    "comfy.sd",
    "comfy.samplers",
    "comfy_execution.graph",
    "comfy_api.feature_flags",
    "app.logger",
]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except Exception:
        return False


def module_locations(module: Any) -> list[str]:
    locations: list[str] = []
    file_value = getattr(module, "__file__", None)
    if file_value:
        locations.append(str(Path(file_value).resolve(strict=False)))
    path_value = getattr(module, "__path__", None)
    if path_value:
        for item in path_value:
            locations.append(str(Path(item).resolve(strict=False)))
    return sorted(set(locations))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def compile_comfy_source(comfy: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for path in sorted(comfy.rglob("*.py"), key=lambda p: str(p).casefold()):
        rel = path.relative_to(comfy)
        if any(part.casefold() in EXCLUDED_SOURCE_PARTS for part in rel.parts):
            continue
        try:
            source = path.read_bytes()
            compile(source, str(path), "exec", dont_inherit=True, optimize=0)
            rows.append({"path": rel.as_posix(), "size_bytes": len(source), "sha256": hashlib.sha256(source).hexdigest()})
        except Exception as exc:
            failures.append({"path": rel.as_posix(), "error": f"{type(exc).__name__}: {exc}"})
    aggregate = hashlib.sha256()
    for row in rows:
        aggregate.update(row["path"].casefold().encode("utf-8", errors="surrogatepass"))
        aggregate.update(b"\0")
        aggregate.update(str(row["size_bytes"]).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(row["sha256"].encode("ascii"))
        aggregate.update(b"\n")
    return {
        "verified": not failures,
        "compiled_file_count": len(rows),
        "source_tree_sha256": aggregate.hexdigest(),
        "failures": failures,
    }


def checked_import(
    module_name: str,
    target: Path,
    comfy: Path,
    portable_root: Path,
    issues: list[str],
    imported: list[dict[str, Any]],
) -> Any | None:
    try:
        module = importlib.import_module(module_name)
        locations = module_locations(module)
        bad_locations = [
            location for location in locations
            if not is_within(Path(location), target)
            and not is_within(Path(location), comfy)
            and not is_within(Path(location), portable_root)
        ]
        if bad_locations:
            issues.append(f"{module_name} loaded outside USB activation roots: {bad_locations}")
        imported.append({
            "module": module_name,
            "verified": not bad_locations,
            "locations": locations,
            "version": str(getattr(module, "__version__", "")),
        })
        return module
    except Exception as exc:
        issues.append(f"Import failed for {module_name}: {type(exc).__name__}: {exc}")
        imported.append({
            "module": module_name,
            "verified": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(limit=12),
        })
        return None


def initialize_comfy_cpu_cli(
    target: Path,
    comfy: Path,
    portable_root: Path,
    issues: list[str],
    imported: list[dict[str, Any]],
) -> dict[str, Any]:
    """Match ComfyUI main.py argument initialization without executing main.py."""
    options = checked_import(
        "comfy.options", target, comfy, portable_root, issues, imported
    )
    if options is None:
        return {
            "verified": False,
            "cpu": False,
            "disable_all_custom_nodes": False,
            "initializer_called": False,
        }

    initializer = getattr(options, "enable_args_parsing", None)
    if not callable(initializer):
        issues.append("comfy.options.enable_args_parsing is missing or not callable")
        return {
            "verified": False,
            "cpu": False,
            "disable_all_custom_nodes": False,
            "initializer_called": False,
        }

    initializer()
    cli = checked_import(
        "comfy.cli_args", target, comfy, portable_root, issues, imported
    )
    parsed = getattr(cli, "args", None) if cli is not None else None
    result = {
        "verified": bool(
            parsed is not None
            and getattr(parsed, "cpu", False)
            and getattr(parsed, "disable_all_custom_nodes", False)
        ),
        "cpu": bool(getattr(parsed, "cpu", False)),
        "disable_all_custom_nodes": bool(
            getattr(parsed, "disable_all_custom_nodes", False)
        ),
        "initializer_called": True,
        "argv": list(sys.argv),
    }
    if not result["cpu"]:
        issues.append("ComfyUI CLI activation did not resolve CPU mode")
    if not result["disable_all_custom_nodes"]:
        issues.append("ComfyUI CLI activation did not disable all custom nodes")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--comfy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve(strict=True)
    target = Path(args.target).resolve(strict=True)
    comfy = Path(args.comfy).resolve(strict=True)
    output = Path(args.output)
    portable_python = Path(sys.executable).resolve(strict=True)
    portable_root = portable_python.parent
    issues: list[str] = []
    blocked_events: list[dict[str, str]] = []
    imported: list[dict[str, Any]] = []

    result: dict[str, Any] = {
        "verified": False,
        "no_launch": True,
        "network_access": False,
        "process_launch": False,
        "server_bind": False,
        "root": str(root),
        "target": str(target),
        "comfy": str(comfy),
        "python": str(portable_python),
        "version": list(sys.version_info[:3]),
        "isolated_flag": int(sys.flags.isolated),
        "no_site_flag": int(sys.flags.no_site),
        "dont_write_bytecode": bool(sys.dont_write_bytecode),
        "issues": issues,
    }

    def audit_hook(event: str, event_args: tuple[Any, ...]) -> None:
        if event in BLOCKED_AUDIT_EVENTS:
            blocked_events.append({"event": event, "args": repr(event_args)[:500]})
            raise RuntimeError(f"C3F no-launch audit blocked event: {event}")

    try:
        if list(sys.version_info[:3]) != [3, 14, 6]:
            issues.append(f"Portable Python version changed: {sys.version_info[:3]}")
        if not sys.flags.isolated or not sys.flags.no_site:
            issues.append("Probe must run with both -I and -S")
        if not sys.dont_write_bytecode:
            issues.append("Probe must run with -B/PYTHONDONTWRITEBYTECODE")
        if portable_python != root / "Runtime" / "Desktop" / "python" / "python.exe":
            issues.append(f"Unexpected portable interpreter: {portable_python}")
        if target != root / "Runtime" / "ComfyUI" / "site-packages":
            issues.append(f"Unexpected isolated target: {target}")
        if comfy != root / "ComfyUI":
            issues.append(f"Unexpected ComfyUI source directory: {comfy}")
        if not (comfy / "main.py").is_file():
            issues.append("ComfyUI main.py is missing")
        if issues:
            raise RuntimeError("Initial activation identity gate failed")

        sys.addaudithook(audit_hook)
        before_path = list(sys.path)
        os.environ.update({
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "HF_HUB_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "DO_NOT_TRACK": "1",
            "NO_PROXY": "*",
            "SETUPTOOLS_USE_DISTUTILS": "local",
        })
        sys.argv = [str(comfy / "main.py"), "--cpu", "--disable-all-custom-nodes", "--dont-print-server"]
        site.addsitedir(str(target))
        if str(comfy) not in sys.path:
            sys.path.insert(0, str(comfy))
        after_path = list(sys.path)

        forbidden_path_entries: list[str] = []
        for entry in after_path:
            if not entry:
                continue
            path = Path(entry).resolve(strict=False)
            if is_within(path, root):
                continue
            # Built-in zip/stdlib paths should be inside the portable runtime.
            forbidden_path_entries.append(str(path))
        if forbidden_path_entries:
            issues.append(f"Forbidden non-USB sys.path entries: {forbidden_path_entries}")

        source_compile = compile_comfy_source(comfy)
        if not source_compile["verified"]:
            issues.append(f"ComfyUI source compilation failures: {source_compile['failures'][:10]}")

        for module_name in DEPENDENCY_IMPORTS:
            checked_import(
                module_name, target, comfy, portable_root, issues, imported
            )

        # ComfyUI main.py performs these two lines before importing any
        # CUDA-sensitive ComfyUI modules. C3F mirrors that ordering without
        # executing main.py or starting the server.
        cli_result = initialize_comfy_cpu_cli(
            target, comfy, portable_root, issues, imported
        )
        if not cli_result["verified"]:
            raise RuntimeError(
                "Fail-closed: ComfyUI CPU/custom-node CLI activation was not established"
            )

        for module_name in COMFY_IMPORTS:
            checked_import(
                module_name, target, comfy, portable_root, issues, imported
            )

        torch_result: dict[str, Any] = {}
        try:
            import torch
            a = torch.tensor([[1.0, 2.0], [3.0, 4.0]], device="cpu")
            b = torch.tensor([[2.0], [1.0]], device="cpu")
            c = a @ b
            torch_result = {
                "verified": c.tolist() == [[4.0], [10.0]],
                "torch_version": str(torch.__version__),
                "cuda_available": bool(torch.cuda.is_available()),
                "result": c.tolist(),
            }
            if not torch_result["verified"]:
                issues.append("CPU torch tensor test returned an unexpected result")
        except Exception as exc:
            torch_result = {"verified": False, "error": f"{type(exc).__name__}: {exc}"}
            issues.append(f"CPU torch test failed: {type(exc).__name__}: {exc}")

        torchvision_result: dict[str, Any] = {}
        try:
            import torch
            import torchvision
            boxes = torch.tensor([[0.0, 0.0, 10.0, 10.0], [1.0, 1.0, 9.0, 9.0]])
            scores = torch.tensor([0.9, 0.8])
            kept = torchvision.ops.nms(boxes, scores, 0.5).tolist()
            torchvision_result = {
                "verified": kept == [0],
                "version": str(torchvision.__version__),
                "nms_result": kept,
            }
            if not torchvision_result["verified"]:
                issues.append(f"torchvision NMS result was unexpected: {kept}")
        except Exception as exc:
            torchvision_result = {"verified": False, "error": f"{type(exc).__name__}: {exc}"}
            issues.append(f"torchvision compiled-op test failed: {type(exc).__name__}: {exc}")

        torchaudio_result: dict[str, Any] = {}
        try:
            import torch
            import torchaudio
            wave = torch.arange(0, 16, dtype=torch.float32).reshape(1, -1)
            resampled = torchaudio.functional.resample(wave, 16000, 8000)
            torchaudio_result = {
                "verified": bool(resampled.numel() > 0),
                "version": str(torchaudio.__version__),
                "output_shape": list(resampled.shape),
            }
            if not torchaudio_result["verified"]:
                issues.append("torchaudio resample produced no output")
        except Exception as exc:
            torchaudio_result = {"verified": False, "error": f"{type(exc).__name__}: {exc}"}
            issues.append(f"torchaudio test failed: {type(exc).__name__}: {exc}")

        main_path = comfy / "main.py"
        main_compile = {
            "path": str(main_path),
            "size_bytes": main_path.stat().st_size,
            "sha256": sha256_file(main_path),
            "compiled": False,
            "executed": False,
        }
        compile(main_path.read_bytes(), str(main_path), "exec", dont_inherit=True)
        main_compile["compiled"] = True

        result.update({
            "sys_path_before_activation": before_path,
            "sys_path_after_activation": after_path,
            "forbidden_sys_path_entries": forbidden_path_entries,
            "source_compile": source_compile,
            "imports": imported,
            "torch_cpu_test": torch_result,
            "torchvision_compiled_op_test": torchvision_result,
            "torchaudio_test": torchaudio_result,
            "comfy_cli_test": cli_result,
            "main_py": main_compile,
            "blocked_audit_events": blocked_events,
        })
        if blocked_events:
            issues.append(f"Blocked launch/network audit events occurred: {blocked_events}")
        result["verified"] = not issues
    except Exception as exc:
        if not issues:
            issues.append(f"{type(exc).__name__}: {exc}")
        result["exception"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc(limit=30)
        result["blocked_audit_events"] = blocked_events
        result["verified"] = False
    finally:
        write_json(output, result)

    return 0 if result.get("verified") else 17


if __name__ == "__main__":
    raise SystemExit(main())
