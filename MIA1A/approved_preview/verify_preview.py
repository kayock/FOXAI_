from __future__ import annotations

import ast
import base64
import binascii
import hashlib
import importlib.util
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WEB_BASELINE_SHA = "e4d5811f14ae3ffb0b3f8b59369bee5c0a1218d19459f2decc875589540d04fb"
SERVER_BASELINE_SHA = "9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07"
WEB_CANDIDATE_SHA = "3b1a8d9a1bc63c6d0a6a333edf315a4c1aff06f9ffae44f9ddd679c96b7c1d4d"
SERVER_CANDIDATE_SHA = "238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81"
WEB_DIFF_SHA = "511be5afd5d901b43adbeeb89427d3dccc534c07bdfe566119c52a5158131d9f"
SERVER_DIFF_SHA = "c75524f02cec963f950f4d23b14c19e2ba9deef91cece3e3549a2a344007eb70"
PROJECTOR_NAME = "mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf"
PROJECTOR_SHA = "c6ba85508d82f42590e6eb77d5340369ab6fecf107a7561d809523d8aa5f3bfd"
PROJECTOR_SIZE = 752289728
MODEL_SIZES = {
    "Models/Chat/Qwen3VL-8B-Instruct-Q4_K_M.gguf": 5027784800,
    "Models/Chat/Qwen3VL-8B-Instruct-Q8_0.gguf": 8709519456,
}
PROTECTED_HASHES = {
    "core/security_containment.py": "9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24",
    "core/engineer_agent.py": "f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19",
    "ui/main_window.py": "2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3",
    "tests/test_boundary_watch.py": "b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382",
    "Config/FoxAI.ini": "677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41",
    "Engine/llama-server.exe": "936cfb77f011911f879a5af715013eb12141115547c1f731114d8e9c20ebd89e",
}
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script\s*>", re.I | re.S)


class PreviewError(RuntimeError):
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
            and (candidate / "core/server.py").is_file()
            and (candidate / "Engine/llama-server.exe").is_file()
        ):
            return candidate
    raise PreviewError(
        r"FOXAI root not found. Extract the complete MIA1P folder directly inside Z:\FOXAI."
    )


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "size": 0, "mtime_ns": None, "sha256": None}
    stat = path.stat()
    return {
        "exists": path.is_file(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256(path) if path.is_file() else None,
    }


def protected_snapshot(root: Path) -> dict[str, Any]:
    paths = [
        "core/foxai_web.py",
        "core/server.py",
        *PROTECTED_HASHES.keys(),
    ]
    result = {relative: file_state(root / relative) for relative in paths}
    security = root / "Logs/Security"
    if security.exists():
        for path in sorted(security.rglob("*")):
            if path.is_file():
                relative = str(path.relative_to(root)).replace("\\", "/")
                result[relative] = file_state(path)
    projector = root / "Models/Chat" / PROJECTOR_NAME
    if projector.is_file():
        stat = projector.stat()
        result[str(projector.relative_to(root)).replace("\\", "/")] = {
            "exists": True,
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": PROJECTOR_SHA,
        }
    return result


def package_manifest(package: Path) -> dict[str, Any]:
    manifest = package / "PACKAGE_SHA256SUMS.txt"
    if not manifest.is_file():
        raise PreviewError("Package manifest is missing.")
    checks = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = package / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected": digest,
            "actual": actual,
            "ok": actual == digest,
        })
    if not checks or not all(item["ok"] for item in checks):
        raise PreviewError("Package manifest verification failed.")
    forbidden = [
        path.name for path in package.iterdir()
        if path.name.casefold() in {"apply.py", "apply.bat", "install.py", "install.bat"}
    ]
    if forbidden:
        raise PreviewError(f"Unexpected apply/install capability: {forbidden}")
    return {"passed": True, "files": checks, "apply_capability_present": False}


def apply_unified_diff(source: str, diff_text: str) -> str:
    source_lines = source.splitlines(keepends=True)
    diff_lines = diff_text.splitlines(keepends=True)
    output: list[str] = []
    source_index = 0
    index = 0
    hunks = 0
    while index < len(diff_lines):
        line = diff_lines[index]
        if line.startswith(("--- ", "+++ ")):
            index += 1
            continue
        match = HUNK_RE.match(line.rstrip("\r\n"))
        if not match:
            index += 1
            continue
        hunks += 1
        old_start = int(match.group(1)) - 1
        if old_start < source_index:
            raise PreviewError("Diff hunks overlap or are out of order.")
        output.extend(source_lines[source_index:old_start])
        source_index = old_start
        index += 1
        while index < len(diff_lines):
            patch_line = diff_lines[index]
            if HUNK_RE.match(patch_line.rstrip("\r\n")):
                break
            if patch_line.startswith(("--- ", "+++ ")):
                break
            if patch_line.startswith("\\ No newline at end of file"):
                index += 1
                continue
            if not patch_line:
                index += 1
                continue
            marker, content = patch_line[0], patch_line[1:]
            if marker == " ":
                if source_index >= len(source_lines) or source_lines[source_index] != content:
                    raise PreviewError("Diff context did not match baseline.")
                output.append(content)
                source_index += 1
            elif marker == "-":
                if source_index >= len(source_lines) or source_lines[source_index] != content:
                    raise PreviewError("Diff removal did not match baseline.")
                source_index += 1
            elif marker == "+":
                output.append(content)
            else:
                raise PreviewError("Unsupported unified-diff line.")
            index += 1
    if not hunks:
        raise PreviewError("Diff contains no hunks.")
    output.extend(source_lines[source_index:])
    return "".join(output)


def exact_artifacts(package: Path) -> dict[str, Any]:
    paths = {
        "web_baseline": package / "baseline/core/foxai_web.py",
        "server_baseline": package / "baseline/core/server.py",
        "web_candidate": package / "candidate/core/foxai_web.py",
        "server_candidate": package / "candidate/core/server.py",
        "web_diff": package / "diffs/foxai_web.py.diff",
        "server_diff": package / "diffs/server.py.diff",
    }
    expected = {
        "web_baseline": WEB_BASELINE_SHA,
        "server_baseline": SERVER_BASELINE_SHA,
        "web_candidate": WEB_CANDIDATE_SHA,
        "server_candidate": SERVER_CANDIDATE_SHA,
        "web_diff": WEB_DIFF_SHA,
        "server_diff": SERVER_DIFF_SHA,
    }
    checks = {}
    for key, path in paths.items():
        actual = sha256(path) if path.is_file() else None
        checks[key] = {"expected": expected[key], "actual": actual, "ok": actual == expected[key]}
    if not all(item["ok"] for item in checks.values()):
        raise PreviewError("Baseline, candidate, or exact-diff identity changed.")
    web_base = paths["web_baseline"].read_text(encoding="utf-8")
    server_base = paths["server_baseline"].read_text(encoding="utf-8")
    web_candidate = paths["web_candidate"].read_text(encoding="utf-8")
    server_candidate = paths["server_candidate"].read_text(encoding="utf-8")
    if apply_unified_diff(web_base, paths["web_diff"].read_text(encoding="utf-8")) != web_candidate:
        raise PreviewError("Web diff did not reconstruct the exact candidate.")
    if apply_unified_diff(server_base, paths["server_diff"].read_text(encoding="utf-8")) != server_candidate:
        raise PreviewError("Server diff did not reconstruct the exact candidate.")
    compile(web_base, "baseline/core/foxai_web.py", "exec")
    compile(server_base, "baseline/core/server.py", "exec")
    compile(web_candidate, "candidate/core/foxai_web.py", "exec")
    compile(server_candidate, "candidate/core/server.py", "exec")
    return {
        "passed": True,
        "checks": checks,
        "diff_reconstruction": True,
        "python_compile": True,
    }


def live_baselines(root: Path) -> dict[str, Any]:
    expected = {
        "core/foxai_web.py": WEB_BASELINE_SHA,
        "core/server.py": SERVER_BASELINE_SHA,
        **PROTECTED_HASHES,
    }
    checks = []
    for relative, digest in expected.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected": digest,
            "actual": actual,
            "ok": actual == digest,
        })
    if not all(item["ok"] for item in checks):
        raise PreviewError("A locked live FOXAI baseline changed. No preview approval is valid.")
    return {"passed": True, "files": checks}


def vision_assets(root: Path) -> dict[str, Any]:
    projector = root / "Models/Chat" / PROJECTOR_NAME
    projector_actual = sha256(projector) if projector.is_file() else None
    checks = [{
        "path": str(projector.relative_to(root)).replace("\\", "/") if projector.exists() else f"Models/Chat/{PROJECTOR_NAME}",
        "expected_size": PROJECTOR_SIZE,
        "actual_size": projector.stat().st_size if projector.is_file() else None,
        "expected_sha256": PROJECTOR_SHA,
        "actual_sha256": projector_actual,
        "ok": projector.is_file() and projector.stat().st_size == PROJECTOR_SIZE and projector_actual == PROJECTOR_SHA,
    }]
    for relative, size in MODEL_SIZES.items():
        path = root / relative
        checks.append({
            "path": relative,
            "expected_size": size,
            "actual_size": path.stat().st_size if path.is_file() else None,
            "ok": path.is_file() and path.stat().st_size == size,
        })
    if not all(item["ok"] for item in checks):
        raise PreviewError("A required Qwen3VL model or verified projector is missing or changed.")
    return {"passed": True, "files": checks}


def node_checks(package: Path) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        raise PreviewError("Node.js was not found.")
    source = (package / "candidate/core/foxai_web.py").read_text(encoding="utf-8")
    scripts = SCRIPT_RE.findall(source)
    if not scripts:
        raise PreviewError("No embedded JavaScript was found.")
    results = []
    with tempfile.TemporaryDirectory(prefix="mia1p_js_") as temporary:
        directory = Path(temporary)
        for index, body in enumerate(scripts, 1):
            path = directory / f"embedded_{index:03d}.js"
            path.write_text(body, encoding="utf-8")
            completed = subprocess.run(
                [node, "--check", str(path)],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            results.append({
                "index": index,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "passed": completed.returncode == 0,
            })
    if not all(item["passed"] for item in results):
        raise PreviewError("Candidate embedded JavaScript failed node --check.")
    browser = subprocess.run(
        [node, str(package / "verification/browser_harness.js")],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if browser.returncode != 0:
        raise PreviewError(f"Browser behavior harness failed: {browser.stderr}")
    return {
        "passed": True,
        "javascript_blocks": len(results),
        "node_check": results,
        "browser_harness": {
            "returncode": browser.returncode,
            "stdout": browser.stdout,
            "stderr": browser.stderr,
            "passed": True,
        },
    }


def helper_namespace(web_source: str) -> dict[str, Any]:
    tree = ast.parse(web_source)
    assignments = {
        "MISSION_IMAGE_MAX_BYTES",
        "MISSION_JSON_MAX_BYTES",
        "MISSION_IMAGE_ALLOWED_MIME",
        "VISION_PROJECTOR_FILENAME",
        "VISION_PROJECTOR_SHA256",
    }
    functions = {
        "mission_image_identity",
        "validate_mission_image",
        "mission_user_message",
        "mission_archive_user_text",
        "compact_prior_images",
        "mission_request_messages",
        "mission_image_receipt_details",
    }
    nodes = []
    for item in tree.body:
        if isinstance(item, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in assignments
            for target in item.targets
        ):
            nodes.append(item)
        elif isinstance(item, ast.ClassDef) and item.name == "MissionRequestError":
            nodes.append(item)
        elif isinstance(item, ast.FunctionDef) and item.name in functions:
            nodes.append(item)
    namespace = {
        "base64": base64,
        "binascii": binascii,
        "hashlib": hashlib,
        "re": re,
        "Path": Path,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "mission_image_helpers", "exec"), namespace)
    return namespace


def helper_harness(package: Path) -> dict[str, Any]:
    source = (package / "candidate/core/foxai_web.py").read_text(encoding="utf-8")
    namespace = helper_namespace(source)
    metadata = json.loads((package / "verification/assets.json").read_text(encoding="utf-8"))
    results = []
    for name, expected in metadata.items():
        path = package / "verification/assets" / name
        payload = path.read_bytes()
        mime = expected["mime"]
        data_url = f"data:{mime};base64," + base64.b64encode(payload).decode("ascii")
        image = namespace["validate_mission_image"]({
            "data_url": data_url,
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "width": expected["width"],
            "height": expected["height"],
            "name": f"../{name}",
        })
        if image["mime"] != mime or image["width"] != expected["width"] or image["height"] != expected["height"]:
            raise PreviewError(f"Image helper did not verify {name} correctly.")
        user_message = namespace["mission_user_message"]("Inspect this.", image)
        archive = namespace["mission_archive_user_text"]("Inspect this.", image)
        receipt = namespace["mission_image_receipt_details"](image)
        compacted = namespace["compact_prior_images"]([user_message])
        if "data:image" in archive or "data_url" in receipt or "data:image" in json.dumps(compacted):
            raise PreviewError("Image payload escaped into archive, receipt, or compacted history.")
        for mutation in (
            {"sha256": "0" * 64},
            {"width": expected["width"] + 1},
            {"data_url": data_url.replace(mime, "image/jpeg" if mime != "image/jpeg" else "image/png", 1)},
        ):
            raw = {
                "data_url": data_url,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "width": expected["width"],
                "height": expected["height"],
                "name": name,
            }
            raw.update(mutation)
            try:
                namespace["validate_mission_image"](raw)
            except namespace["MissionRequestError"]:
                pass
            else:
                raise PreviewError(f"Invalid image metadata was accepted for {name}: {mutation}")
        results.append({"name": name, "mime": mime, "passed": True})
    return {
        "passed": True,
        "formats": results,
        "actual_byte_mime_and_dimensions": True,
        "sha256_and_size_validation": True,
        "base64_not_archived": True,
        "prior_image_compaction": True,
    }


def model_filter_harness(package: Path) -> dict[str, Any]:
    source = (package / "candidate/core/foxai_web.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "models"
    )
    with tempfile.TemporaryDirectory(prefix="mia1p_models_") as temporary:
        root = Path(temporary)
        chat = root / "Models/Chat"
        chat.mkdir(parents=True)
        (chat / "Qwen.gguf").write_bytes(b"model")
        (chat / "mmproj-Qwen.gguf").write_bytes(b"projector")
        (chat / "projector.gguf").write_bytes(b"projector")
        namespace = {"ROOT": root, "Path": Path}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "models_filter", "exec"), namespace)
        names = [path.name for path in namespace["models"]()]
    if names != ["Qwen.gguf"]:
        raise PreviewError(f"Projector files leaked into model selection: {names}")
    return {"passed": True, "visible_models": names, "projectors_filtered": True}


def profile_contract_harness(package: Path) -> dict[str, Any]:
    source = (package / "candidate/core/foxai_web.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    nodes = []
    for item in tree.body:
        if isinstance(item, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "WEB_MODEL_PROFILE_RUNTIME"
            for target in item.targets
        ):
            nodes.append(item)
        elif isinstance(item, ast.FunctionDef) and item.name == "web_model_profile_runtime":
            nodes.append(item)
    namespace = {
        "Path": Path,
        "VISION_PROJECTOR_FILENAME": PROJECTOR_NAME,
        "VISION_PROJECTOR_SHA256": PROJECTOR_SHA,
        "verified_vision_projector": lambda: {
            "ok": True,
            "path": f"Z:/FOXAI/Models/Chat/{PROJECTOR_NAME}",
            "sha256": PROJECTOR_SHA,
        },
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "profile_contract", "exec"), namespace)
    fast = namespace["web_model_profile_runtime"](
        "Qwen3VL-8B-Instruct-Q4_K_M.gguf", "fast_vision"
    )
    quality = namespace["web_model_profile_runtime"](
        "Qwen3VL-8B-Instruct-Q8_0.gguf", "quality_vision"
    )
    raw = namespace["web_model_profile_runtime"]("other.gguf", "")
    mismatch = namespace["web_model_profile_runtime"](
        "Qwen3VL-8B-Instruct-Q8_0.gguf", "fast_vision"
    )
    if not (
        fast.get("ok") and fast.get("vision") and fast.get("projector_sha256") == PROJECTOR_SHA
        and quality.get("ok") and quality.get("vision") and quality.get("projector_sha256") == PROJECTOR_SHA
        and raw.get("ok") and raw.get("vision") is False and raw.get("projector_path") is None
        and mismatch.get("ok") is False
    ):
        raise PreviewError("Vision-profile runtime contract failed.")
    return {
        "passed": True,
        "fast_vision": fast,
        "quality_vision": quality,
        "raw_exact_gguf_vision": raw.get("vision"),
        "profile_model_mismatch_denied": True,
    }


def server_harness(package: Path, root: Path) -> dict[str, Any]:
    candidate = package / "candidate/core/server.py"
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    module_name = "mia1p_candidate_server"
    spec = importlib.util.spec_from_file_location(module_name, candidate)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    original_psutil = sys.modules.get("psutil")
    try:
        with tempfile.TemporaryDirectory(prefix="mia1p_server_") as temporary:
            directory = Path(temporary)
            model = directory / "model.gguf"
            projector = directory / "mmproj.gguf"
            model.write_bytes(b"model")
            projector.write_bytes(b"projector")
            runtime = module.LlamaServer(
                interface_name="MIA1P verifier",
                state_file=directory / "state.json",
            )
            target = runtime._target(
                model,
                "127.0.0.1",
                "8080",
                "8192",
                "12",
                "current",
                None,
                True,
                projector,
            )
            captured: dict[str, Any] = {}
            class FakePopenResult:
                pid = 123
            original_popen = module.subprocess.Popen
            module.subprocess.Popen = lambda cmd, **kwargs: (
                captured.update({"cmd": list(cmd), "kwargs": kwargs}) or FakePopenResult()
            )
            try:
                runtime._launch_process(target)
                vision_command = list(captured["cmd"])
                text_target = runtime._target(
                    model,
                    "127.0.0.1",
                    "8080",
                    "8192",
                    "12",
                    "current",
                    None,
                    True,
                    None,
                )
                runtime._launch_process(text_target)
                text_command = list(captured["cmd"])
            finally:
                module.subprocess.Popen = original_popen
            if "--mmproj" not in vision_command or "--mmproj" in text_command:
                raise PreviewError("Projector launch command contract failed.")
            if vision_command[vision_command.index("--mmproj") + 1] != str(projector.resolve()):
                raise PreviewError("Exact projector path was not used.")
            state = {
                "engine_path": str(module.ENGINE),
                "model_path": str(model.resolve()),
                "projector_path": str(projector.resolve()),
                "context": "8192",
                "threads": "12",
                "reasoning_mode": "current",
                "reasoning_budget": None,
            }
            if not runtime._same_model(state, target):
                raise PreviewError("Compatible model/projector state was rejected.")
            no_projector_target = dict(target)
            no_projector_target["projector_path"] = None
            no_projector_target["projector_name"] = None
            if runtime._same_model(state, no_projector_target):
                raise PreviewError("Projector mismatch was accepted.")

            class FakeProcess:
                def __init__(self, arguments):
                    self.arguments = arguments
                def cmdline(self):
                    return list(self.arguments)
                def exe(self):
                    return str(module.ENGINE)
            class FakePsutil:
                def __init__(self, arguments):
                    self.arguments = arguments
                def Process(self, pid):
                    return FakeProcess(self.arguments)
            good_command = [
                str(module.ENGINE), "--model", str(model.resolve()),
                "--host", "127.0.0.1", "--port", "8080",
                "--ctx-size", "8192", "--threads", "12",
                "--mmproj", str(projector.resolve()),
            ]
            sys.modules["psutil"] = FakePsutil(good_command)
            if runtime._process_matches_state(123, state) is not True:
                raise PreviewError("Exact process/projector state was not verified.")
            wrong = list(good_command)
            wrong[wrong.index("--mmproj") + 1] = str(directory / "wrong.gguf")
            sys.modules["psutil"] = FakePsutil(wrong)
            if runtime._process_matches_state(123, state) is not False:
                raise PreviewError("Wrong projector process was accepted.")
            without = good_command[:good_command.index("--mmproj")]
            sys.modules["psutil"] = FakePsutil(without)
            if runtime._process_matches_state(123, state) is not False:
                raise PreviewError("Missing projector flag was accepted.")
            text_state = dict(state)
            text_state["projector_path"] = None
            sys.modules["psutil"] = FakePsutil(good_command)
            if runtime._process_matches_state(123, text_state) is not False:
                raise PreviewError("Text runtime accepted an unexpected projector.")
            sys.modules["psutil"] = FakePsutil(without)
            if runtime._process_matches_state(123, text_state) is not True:
                raise PreviewError("Text runtime without projector was rejected.")
            if list(inspect.signature(runtime.ensure_running).parameters)[-1] != "projector":
                raise PreviewError("ensure_running positional compatibility changed.")
            if list(inspect.signature(runtime.start).parameters)[-1] != "projector":
                raise PreviewError("start positional compatibility changed.")
    finally:
        if original_psutil is None:
            sys.modules.pop("psutil", None)
        else:
            sys.modules["psutil"] = original_psutil
        sys.modules.pop(module_name, None)
    return {
        "passed": True,
        "vision_command_has_mmproj": True,
        "text_command_has_no_mmproj": True,
        "exact_projector_runtime_identity": True,
        "wrong_or_missing_projector_rejected": True,
        "public_positional_compatibility_preserved": True,
    }


def static_contract(package: Path) -> dict[str, Any]:
    web = (package / "candidate/core/foxai_web.py").read_text(encoding="utf-8")
    server = (package / "candidate/core/server.py").read_text(encoding="utf-8")
    checks = {
        "one_image_and_json_limits": "MISSION_IMAGE_MAX_BYTES=6*1024*1024" in web and "MISSION_JSON_MAX_BYTES=9*1024*1024" in web,
        "allowed_types": "{'image/png','image/jpeg','image/webp'}" in web,
        "actual_byte_validation": "actual_mime,width,height=mission_image_identity(payload)" in web,
        "sha_validation": "Image attachment SHA-256 verification failed." in web,
        "no_silent_switch_client": "no model switch occurred" in web,
        "no_silent_switch_server": "No model switch occurred." in web,
        "engineer_image_denied": "Engineer image inspection is not enabled." in web,
        "stream_and_nonstream_accept_image": "JSON.stringify({message:text,image})" in web and web.count("validate_mission_image(d.get('image'))") == 2,
        "archive_metadata_only": "'data_archived':False" in web and "[Earlier image attachment omitted after a newer image was attached.]" in web,
        "cancel_keeps_pending": "if(d?.ok&&image)clearMissionImage()" in web,
        "projector_pinned": PROJECTOR_SHA in web and PROJECTOR_NAME in web,
        "projector_runtime_identity": "projector_path" in server and "--mmproj" in server,
        "projector_filtered_from_selector": "if 'mmproj' in lowered or 'projector' in lowered" in web,
        "vision_evidence_updated": web.count("REAL IMAGE INPUT SUPPORTED • BENCHMARK PASSED") == 2,
        "guarded_streaming_preserved": "# GUARDED_STREAMING_PHASE2_ROUTE_START" in web and "No partial assistant answer was archived." in web,
    }
    if not all(checks.values()):
        raise PreviewError(f"Static contract failed: {[key for key, value in checks.items() if not value]}")
    return {"passed": True, "checks": checks}


def boundary_watch(root: Path) -> dict[str, Any]:
    code = (
        "import sys,unittest;"
        f"sys.path.insert(0,{str(root)!r});"
        "suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_boundary_watch');"
        "result=unittest.TextTestRunner(verbosity=2).run(suite);"
        "raise SystemExit(0 if result.wasSuccessful() else 1)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    combined = completed.stdout + completed.stderr
    passed = completed.returncode == 0 and "Ran 5 tests" in combined and "OK" in combined
    if not passed:
        raise PreviewError("Boundary Watch 5/5 failed.")
    return {
        "passed": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "tests": 5,
    }


def main() -> int:
    package = Path(__file__).resolve().parent
    root = find_root(package)
    output = package / "LIVE_VERIFY_RECEIPT.json"
    receipt: dict[str, Any] = {
        "action": "mission_image_attachments_phase1_exact_preview_verify",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "running",
        "verified": False,
        "root": str(root),
        "live_files_modified": False,
        "candidate_created": True,
        "apply_capability_present": False,
        "changed_files_proposed": ["core/foxai_web.py", "core/server.py"],
        "delete_operations": [],
        "checks": {},
        "failure": None,
    }
    before = protected_snapshot(root)
    try:
        receipt["checks"]["package_manifest"] = package_manifest(package)
        receipt["checks"]["exact_artifacts"] = exact_artifacts(package)
        receipt["checks"]["live_baselines"] = live_baselines(root)
        receipt["checks"]["vision_assets"] = vision_assets(root)
        receipt["checks"]["node_and_browser"] = node_checks(package)
        receipt["checks"]["image_helpers"] = helper_harness(package)
        receipt["checks"]["model_filter"] = model_filter_harness(package)
        receipt["checks"]["profile_contract"] = profile_contract_harness(package)
        receipt["checks"]["server_runtime"] = server_harness(package, root)
        receipt["checks"]["static_contract"] = static_contract(package)
        receipt["checks"]["boundary_watch"] = boundary_watch(root)
        after = protected_snapshot(root)
        changes = [
            key for key in sorted(set(before) | set(after))
            if before.get(key) != after.get(key)
        ]
        if changes:
            raise PreviewError(f"Protected live state changed during verification: {changes}")
        receipt.update({
            "state": "exact_preview_verified",
            "verified": True,
            "live_files_modified": False,
            "protected_changes": [],
        })
    except Exception as exc:
        after = protected_snapshot(root)
        changes = [
            key for key in sorted(set(before) | set(after))
            if before.get(key) != after.get(key)
        ]
        receipt.update({
            "state": "stopped_fail_closed",
            "verified": not changes,
            "live_files_modified": bool(changes),
            "protected_changes": changes,
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        })
    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print()
    print("=" * 72)
    print("FOXAI MISSION IMAGE ATTACHMENTS — PHASE 1 EXACT PREVIEW")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Live files modified:", receipt["live_files_modified"])
    print("Apply capability present: False")
    print("Proposed changed files:", receipt["changed_files_proposed"])
    print("Delete operations:", receipt["delete_operations"])
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    print("Receipt:", output)
    print()
    input("Press Enter to close...")
    return 0 if receipt["state"] == "exact_preview_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
