from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WEB_BASELINE_SHA = "7fcbddeae22904af7f9aa75e9546e3e28721d455222fbfc42c27c5186ba45180"
WEB_CANDIDATE_SHA = "ecccf3b4a780d9de6ef2aa56522c6b65d06035c42a4a9050d72b95df530c40d0"
WEB_DIFF_SHA = "41efcd8d4ee744a962d24005924c7f6e1dd1d140b0410121a16229ad88348b00"
SOURCE_SNAPSHOT_SHA = "0fef77584ab717f2d0dbe70265cde46988a7426bea654d7772409dab7bee0bcc"

LOCKED_HASHES = {
    "core/foxai_web.py": WEB_BASELINE_SHA,
    "core/server.py":
        "238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81",
    "core/security_containment.py":
        "9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24",
    "core/engineer_agent.py":
        "f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19",
    "core/service_registry.py":
        "cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b",
    "ui/main_window.py":
        "2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3",
    "tests/test_boundary_watch.py":
        "b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382",
    "Config/FoxAI.ini":
        "677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41",
    "Config/application_registry.json":
        "6338e10b813460ee421e4cbf3d9d74fd82d5f24178347e35f4318ef3c4ef9022",
    "Config/fleet_registry.json":
        "18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6",
    "Engine/llama-server.exe":
        "936cfb77f011911f879a5af715013eb12141115547c1f731114d8e9c20ebd89e",
    "Extensions/Academy/Conversation/extension.json":
        "bd94beb278523891931272e1e7b00c72f6eae344493fa1fecb5c51b804097d5d",
    "Extensions/Engineering/Database/extension.json":
        "a487f38867411ae72abeb9427393b5847242c2181ade5ef841c7490f5e6360f8",
    "Extensions/Engineering/Everything/extension.json":
        "bbc5243aff38c74007ecfe777f5204bf80f119d44853e828c6e3186395176c86",
    "Extensions/Engineering/ripgrep/extension.json":
        "21d4e25c2a312ecaf13affd9df29229beae623d36e1f6396f3b6981e3508ea0b",
    "Extensions/Engineering/TreeSitter/extension.json":
        "feb9e78e193b1ae3a2d40dbf73f6b9e6692f386d9d670a2291c990d4120b0250",
    "Extensions/Engineering/WinMerge/extension.json":
        "a272f06a53c2788c3d36e3cf3c5be1480d06228c288326043bffc769cd6f8d02",
}

SCRIPT_RE = re.compile(
    r"<script[^>]*>(.*?)</script\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
HUNK_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)

INVENTORY_FUNCTIONS = {
    "_inventory_read_json",
    "_inventory_resolve_path",
    "_inventory_relative",
    "_inventory_file_details",
    "_inventory_manifest_candidates",
    "_inventory_manifest_records",
    "_inventory_status",
    "_inventory_item",
    "_inventory_application_items",
    "_inventory_fleet_items",
    "_inventory_manifest_items",
    "_inventory_core_items",
    "_inventory_model_items",
    "extension_inventory_snapshot",
    "_inventory_lookup",
    "_inventory_allowed_path",
}

INVENTORY_CONSTANTS = {
    "EXTENSION_INVENTORY_MODEL_SUFFIXES",
    "EXTENSION_INVENTORY_MAX_MODEL_FILES",
    "EXTENSION_INVENTORY_SAFE_FLEET_LAUNCH",
    "EXTENSION_INVENTORY_EXPECTED_SIZES",
    "EXTENSION_INVENTORY_CORE_FILES",
}

LEGACY_FUNCTIONS = {
    "toggle_extension",
    "validate_extensions",
    "create_sample_extension",
    "extension_report_export",
    "suggest_manifest_repair",
    "apply_manifest_repair",
}


class VerifyError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "size": 0,
            "mtime_ns": None,
            "sha256": None,
        }
    stat = path.stat()
    return {
        "exists": path.is_file(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256(path) if path.is_file() else None,
    }


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "core/foxai_web.py").is_file()
            and (candidate / "Config/application_registry.json").is_file()
            and (candidate / "Engine/llama-server.exe").is_file()
        ):
            return candidate
    raise VerifyError(
        r"FOXAI root not found. Extract the complete EMI1P folder directly inside Z:\FOXAI."
    )


def package_manifest(package: Path) -> dict[str, Any]:
    manifest = package / "PACKAGE_SHA256SUMS.txt"
    if not manifest.is_file():
        raise VerifyError("Package manifest is missing.")
    checks = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        target = package / relative
        actual = sha256(target) if target.is_file() else None
        checks.append({
            "path": relative,
            "expected": digest,
            "actual": actual,
            "ok": actual == digest,
        })
    if not checks or not all(item["ok"] for item in checks):
        raise VerifyError("Package manifest verification failed.")
    return {
        "passed": True,
        "files": checks,
        "apply_capability_present": False,
    }


def protected_snapshot(root: Path) -> dict[str, Any]:
    result = {
        relative: file_state(root / relative)
        for relative in LOCKED_HASHES
    }
    state_path = root / "Config/extension_state.json"
    result["Config/extension_state.json"] = file_state(state_path)
    security_root = root / "Logs/Security"
    if security_root.exists():
        for path in sorted(security_root.rglob("*")):
            if path.is_file():
                relative = str(path.relative_to(root)).replace("\\", "/")
                result[relative] = file_state(path)
    return result


def changed_paths(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[str]:
    return [
        key
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]


def live_baselines(root: Path) -> dict[str, Any]:
    checks = []
    for relative, expected in LOCKED_HASHES.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected": expected,
            "actual": actual,
            "ok": actual == expected,
        })
    if not all(item["ok"] for item in checks):
        raise VerifyError("A locked live FOXAI baseline changed.")
    return {"passed": True, "files": checks}


def apply_unified_diff(source: str, diff_text: str) -> str:
    source_lines = source.splitlines(keepends=True)
    diff_lines = diff_text.splitlines(keepends=True)
    output = []
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
            raise VerifyError("Diff hunks overlap or are out of order.")

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

            marker = patch_line[0]
            content = patch_line[1:]
            if marker == " ":
                if (
                    source_index >= len(source_lines)
                    or source_lines[source_index] != content
                ):
                    raise VerifyError("Diff context did not match baseline.")
                output.append(content)
                source_index += 1
            elif marker == "-":
                if (
                    source_index >= len(source_lines)
                    or source_lines[source_index] != content
                ):
                    raise VerifyError("Diff removal did not match baseline.")
                source_index += 1
            elif marker == "+":
                output.append(content)
            else:
                raise VerifyError("Unsupported diff line.")
            index += 1

    if hunks == 0:
        raise VerifyError("Exact diff contains no hunks.")

    output.extend(source_lines[source_index:])
    return "".join(output)


def exact_artifacts(package: Path) -> dict[str, Any]:
    baseline = package / "baseline/core/foxai_web.py"
    candidate = package / "candidate/core/foxai_web.py"
    diff = package / "diffs/foxai_web.py.diff"

    checks = {
        "baseline_hash": sha256(baseline) == WEB_BASELINE_SHA,
        "candidate_hash": sha256(candidate) == WEB_CANDIDATE_SHA,
        "diff_hash": sha256(diff) == WEB_DIFF_SHA,
    }
    if not all(checks.values()):
        raise VerifyError("Exact artifact identity failed.")

    baseline_text = baseline.read_text(encoding="utf-8")
    candidate_text = candidate.read_text(encoding="utf-8")
    reconstructed = apply_unified_diff(
        baseline_text,
        diff.read_text(encoding="utf-8"),
    )
    checks["diff_reconstructs_candidate"] = (
        reconstructed == candidate_text
    )
    if not checks["diff_reconstructs_candidate"]:
        raise VerifyError("Exact diff did not reconstruct the candidate.")

    compile(baseline_text, str(baseline), "exec")
    compile(candidate_text, str(candidate), "exec")
    checks["python_compile"] = True

    return {"passed": True, "checks": checks}


def source_snapshot_grounding(package: Path) -> dict[str, Any]:
    index_path = package / "grounding/SNAPSHOT_INDEX.json"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    if data.get("source_zip_sha256") != SOURCE_SNAPSHOT_SHA:
        raise VerifyError("Source snapshot identity changed.")

    checks = []
    for relative, contract in (
        data.get("selected_grounding") or {}
    ).items():
        path = package / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected": contract.get("sha256"),
            "actual": actual,
            "ok": actual == contract.get("sha256"),
        })
    if not checks or not all(item["ok"] for item in checks):
        raise VerifyError("Grounding snapshot verification failed.")

    return {
        "passed": True,
        "source_zip_sha256": SOURCE_SNAPSHOT_SHA,
        "provided_extension_state": data.get(
            "provided_extension_state"
        ) is True,
        "extension_state_absence_expected":
            data.get("provided_extension_state") is False,
        "files": checks,
    }


def node_and_browser(package: Path) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        raise VerifyError("Node.js was not found.")

    source = (
        package / "candidate/core/foxai_web.py"
    ).read_text(encoding="utf-8")
    scripts = SCRIPT_RE.findall(source)
    if not scripts:
        raise VerifyError("No embedded JavaScript was found.")

    node_results = []
    with tempfile.TemporaryDirectory(
        prefix="emi1p_node_"
    ) as temporary:
        base = Path(temporary)
        for index, script in enumerate(scripts, start=1):
            target = base / f"embedded_{index:03d}.js"
            target.write_text(script, encoding="utf-8")
            completed = subprocess.run(
                [node, "--check", str(target)],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            node_results.append({
                "index": index,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "passed": completed.returncode == 0,
            })

    if not all(item["passed"] for item in node_results):
        raise VerifyError("Embedded JavaScript failed node --check.")

    harness = package / "verification/browser_harness.js"
    completed = subprocess.run(
        [node, str(harness)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    browser = {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }
    if browser["passed"] is not True:
        raise VerifyError("Inventory browser harness failed.")

    return {
        "passed": True,
        "javascript_blocks": len(node_results),
        "node_check": node_results,
        "browser_harness": browser,
    }


def _inventory_nodes(source: str):
    tree = ast.parse(source)
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            ]
            if any(name in INVENTORY_CONSTANTS for name in names):
                nodes.append(node)
        elif (
            isinstance(node, ast.FunctionDef)
            and node.name in INVENTORY_FUNCTIONS
        ):
            nodes.append(node)
    found_functions = {
        node.name
        for node in nodes
        if isinstance(node, ast.FunctionDef)
    }
    if found_functions != INVENTORY_FUNCTIONS:
        missing = sorted(INVENTORY_FUNCTIONS - found_functions)
        raise VerifyError(
            "Inventory helper extraction is incomplete: "
            + ", ".join(missing)
        )
    return nodes


def _inventory_namespace(source: str, root: Path):
    nodes = _inventory_nodes(source)

    def slug(value):
        return re.sub(
            r"[^a-zA-Z0-9]+",
            "-",
            str(value or ""),
        ).strip("-")

    def extension_key_from_path(path):
        try:
            relative = path.parent.relative_to(root)
            return slug(str(relative).replace("\\", "/")).lower()
        except Exception:
            return slug(path.parent.name).lower()

    def local_check(url):
        try:
            with urllib.request.urlopen(url, timeout=0.6) as response:
                response.read(32)
            return True
        except Exception:
            return False

    namespace = {
        "Path": Path,
        "os": os,
        "json": json,
        "datetime": datetime,
        "importlib": importlib,
        "hashlib": hashlib,
        "ROOT": root,
        "DRIVE": Path(root.anchor),
        "VISION_PROJECTOR_FILENAME":
            "mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf",
        "WEB_MODEL_PROFILE_RUNTIME": {
            "fast_text": {
                "model_filename": "Qwen3.5-4B-Q4_K_M.gguf",
            },
            "balanced_text": {
                "model_filename": "Qwen3.5-9B-Q4_K_M.gguf",
            },
            "creative_text": {
                "model_filename": "PsyLLM-8B-Q5_K_M.gguf",
            },
            "fast_vision": {
                "model_filename":
                    "Qwen3VL-8B-Instruct-Q4_K_M.gguf",
            },
            "quality_vision": {
                "model_filename":
                    "Qwen3VL-8B-Instruct-Q8_0.gguf",
            },
        },
        "slug": slug,
        "extension_key_from_path": extension_key_from_path,
        "check": local_check,
        "now": lambda: datetime.now().isoformat(
            timespec="seconds"
        ),
    }
    exec(
        compile(
            ast.Module(body=nodes, type_ignores=[]),
            "extension_inventory_helpers",
            "exec",
        ),
        namespace,
    )
    return namespace


def _validate_inventory_report(
    report: dict[str, Any],
    state_before: dict[str, Any],
    state_after: dict[str, Any],
) -> dict[str, Any]:
    if report.get("ok") is not True:
        raise VerifyError("Inventory report did not return ok=true.")
    if report.get("read_only") is not True:
        raise VerifyError("Inventory report lost its read-only contract.")
    if report.get("configuration_modified") is not False:
        raise VerifyError("Inventory reported a configuration change.")
    if report.get("state_file_created") is not False:
        raise VerifyError("Inventory reported creating extension state.")
    if state_before != state_after:
        raise VerifyError(
            "Inventory changed Config/extension_state.json."
        )

    items = report.get("items") or []
    summary = report.get("summary") or {}
    if summary.get("total") != len(items):
        raise VerifyError("Inventory total does not match item count.")

    allowed = {
        "VERIFIED",
        "INSTALLED",
        "MISSING",
        "NEEDS_ATTENTION",
    }
    invalid_statuses = sorted({
        str(item.get("status"))
        for item in items
        if item.get("status") not in allowed
    })
    if invalid_statuses:
        raise VerifyError(
            "Inventory returned unsupported health states: "
            + ", ".join(invalid_statuses)
        )

    projector_items = [
        item
        for item in items
        if "mmproj" in str(item.get("name") or "").casefold()
        or item.get("kind") == "vision_projector"
    ]
    wrong_projectors = [
        item.get("id")
        for item in projector_items
        if item.get("category") != "Vision Projector"
        or item.get(
            "excluded_from_language_model_selector"
        ) is not True
    ]
    if wrong_projectors:
        raise VerifyError(
            "Projector files were not separated from language models."
        )

    model_scan = summary.get("model_scan") or {}
    if (
        model_scan.get(
            "projectors_filtered_from_language_models"
        )
        is not True
    ):
        raise VerifyError(
            "Model scan did not assert projector filtering."
        )

    required_problems = [
        item
        for item in items
        if item.get("required")
        and item.get("status")
        in {"MISSING", "NEEDS_ATTENTION"}
    ]
    if summary.get("required_problems") != len(
        required_problems
    ):
        raise VerifyError(
            "Required-problem count is inconsistent."
        )

    state_source = (
        (report.get("sources") or {})
        .get("extension_state")
        or {}
    )
    if (
        state_before.get("exists") is False
        and "manifest defaults"
        not in str(state_source.get("mode") or "").lower()
    ):
        raise VerifyError(
            "Missing extension state was not explained as manifest defaults."
        )

    return {
        "passed": True,
        "items": len(items),
        "summary": summary,
        "projectors": len(projector_items),
        "projectors_separate": not wrong_projectors,
        "state_file_unchanged": state_before == state_after,
        "state_file_exists": state_after.get("exists"),
        "required_problem_count": len(required_problems),
        "sources": report.get("sources") or {},
        "safety": report.get("safety") or {},
    }


def backend_harness(package: Path, root: Path) -> dict[str, Any]:
    source = (
        package / "candidate/core/foxai_web.py"
    ).read_text(encoding="utf-8")
    namespace = _inventory_namespace(source, root)
    state_path = root / "Config/extension_state.json"
    before = file_state(state_path)
    report = namespace["extension_inventory_snapshot"]()
    after = file_state(state_path)
    result = _validate_inventory_report(
        report,
        before,
        after,
    )
    result["report"] = report
    return result


def fake_backend_harness(package: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="emi1p_backend_"
    ) as temporary:
        root = Path(temporary)
        (root / "Config").mkdir(parents=True)
        (root / "core").mkdir()
        (root / "Engine").mkdir()
        (root / "Models/Chat").mkdir(parents=True)
        (
            root
            / "Extensions/Engineering/NestedTool"
        ).mkdir(parents=True)
        (
            root
            / "Departments/Engineering"
        ).mkdir(parents=True)
        (
            root
            / "ComfyUI/models/checkpoints"
        ).mkdir(parents=True)
        (
            root
            / "Hanger Bay/Everything"
        ).mkdir(parents=True)

        (root / "core/service_registry.py").write_text(
            "# service registry\n",
            encoding="utf-8",
        )
        (root / "Engine/llama-server.exe").write_bytes(
            b"engine"
        )
        executable = (
            root
            / "Hanger Bay/Everything/Everything.exe"
        )
        executable.write_bytes(b"exe")
        (root / "Models/Chat/TestModel.gguf").write_bytes(
            b"model"
        )
        (
            root
            / "Models/Chat/mmproj-Test.gguf"
        ).write_bytes(b"projector")
        (
            root
            / "ComfyUI/models/checkpoints/art.safetensors"
        ).write_bytes(b"art")

        nested_manifest = (
            root
            / "Extensions/Engineering/NestedTool/extension.json"
        )
        nested_manifest.write_text(
            json.dumps({
                "key": "nested",
                "name": "Nested Tool",
                "version": "1.0",
                "kind": "extension",
            }),
            encoding="utf-8",
        )
        (
            root
            / "Departments/Engineering/manifest.json"
        ).write_text(
            json.dumps({
                "id": "engineering",
                "name": "Engineering",
                "version": "0.1",
                "type": "department",
                "enabled": True,
                "tools": [
                    {"id": "json", "import": "json"},
                    {
                        "id": "missing",
                        "import":
                            "definitely_missing_pkg_emi1p",
                    },
                ],
            }),
            encoding="utf-8",
        )
        (
            root / "Config/application_registry.json"
        ).write_text(
            json.dumps({
                "applications": [
                    {
                        "id": "engine",
                        "name": "Engine",
                        "path": "Engine/llama-server.exe",
                        "lifecycle": "active",
                        "health_mode": "path",
                    },
                    {
                        "id": "planned",
                        "name": "Planned",
                        "lifecycle": "planned",
                        "health_mode": "static",
                    },
                    {
                        "id": "broken",
                        "name": "Broken Active",
                        "path": "missing.exe",
                        "lifecycle": "active",
                        "health_mode": "path",
                    },
                ]
            }),
            encoding="utf-8",
        )
        (
            root / "Config/fleet_registry.json"
        ).write_text(
            json.dumps({
                "mode": "passive",
                "shuttles": {
                    "everything": {
                        "key": "everything",
                        "name": "Everything",
                        "path": str(executable),
                        "manifest_path":
                            str(nested_manifest),
                        "installed": True,
                        "department": "Engineering",
                        "kind": "application",
                    }
                },
            }),
            encoding="utf-8",
        )

        result = backend_harness(package, root)
        items = result["report"].get("items") or []
        checks = {
            "recursive_nested_manifest_found":
                any(
                    item.get("name") == "Nested Tool"
                    or item.get("id") == "fleet:everything"
                    for item in items
                ),
            "fleet_manifest_merged_by_path":
                not any(
                    str(item.get("id") or "").startswith(
                        "manifest:nested"
                    )
                    for item in items
                ),
            "required_missing_needs_attention":
                any(
                    item.get("id") == "app:broken"
                    and item.get("status")
                        == "NEEDS_ATTENTION"
                    for item in items
                ),
            "optional_planned_missing":
                any(
                    item.get("id") == "app:planned"
                    and item.get("status") == "MISSING"
                    and item.get("required") is False
                    for item in items
                ),
            "projector_separate":
                any(
                    item.get("category")
                        == "Vision Projector"
                    for item in items
                ),
            "state_file_not_created":
                not (
                    root
                    / "Config/extension_state.json"
                ).exists(),
        }
        if not all(checks.values()):
            raise VerifyError(
                "Fake-root backend regression failed."
            )
        return {
            "passed": True,
            "checks": checks,
            "summary": result["summary"],
        }


def _function_segments(source: str, names: set[str]):
    tree = ast.parse(source)
    result = {}
    for node in tree.body:
        if (
            isinstance(node, ast.FunctionDef)
            and node.name in names
        ):
            segment = ast.get_source_segment(source, node)
            result[node.name] = hashlib.sha256(
                (segment or "").encode("utf-8")
            ).hexdigest()
    return result


def legacy_controls_unchanged(package: Path) -> dict[str, Any]:
    baseline = (
        package / "baseline/core/foxai_web.py"
    ).read_text(encoding="utf-8")
    candidate = (
        package / "candidate/core/foxai_web.py"
    ).read_text(encoding="utf-8")
    before = _function_segments(
        baseline,
        LEGACY_FUNCTIONS,
    )
    after = _function_segments(
        candidate,
        LEGACY_FUNCTIONS,
    )
    checks = {
        name: (
            name in before
            and name in after
            and before[name] == after[name]
        )
        for name in sorted(LEGACY_FUNCTIONS)
    }
    if not all(checks.values()):
        raise VerifyError(
            "A pre-existing manifest control function changed."
        )
    return {
        "passed": True,
        "functions": checks,
        "hashes": after,
    }


def static_contract(package: Path) -> dict[str, Any]:
    source = (
        package / "candidate/core/foxai_web.py"
    ).read_text(encoding="utf-8")
    start_marker = (
        "# EXTENSION_MANAGER_INVENTORY_PHASE1_BACKEND_START"
    )
    end_marker = (
        "# EXTENSION_MANAGER_INVENTORY_PHASE1_BACKEND_END"
    )
    start = source.find(start_marker)
    end = source.find(end_marker)
    if start < 0 or end < 0 or end <= start:
        raise VerifyError("Inventory backend markers are missing.")
    block = source[start:end]

    forbidden_writes = {
        "write_extension_state(":
            "extension state writer",
        "extension_state_file(":
            "legacy state-file creator",
        "jwrite(":
            "JSON writer",
        ".write_text(":
            "direct text writer",
        ".write_bytes(":
            "direct byte writer",
        ".mkdir(":
            "directory creator",
        ".unlink(":
            "file delete",
        "shutil.copy":
            "file copy",
        "os.replace(":
            "atomic file replacement",
    }
    found_forbidden = {
        token: label
        for token, label in forbidden_writes.items()
        if token in block
    }
    if found_forbidden:
        raise VerifyError(
            "Inventory backend contains a configuration/filesystem "
            "write primitive: "
            + ", ".join(found_forbidden.values())
        )

    checks = {
        "read_only_endpoint":
            "if path=='/api/extensions/inventory':"
            in source,
        "operator_folder_action":
            "/api/extensions/inventory/open_folder"
            in source,
        "operator_url_action":
            "/api/extensions/inventory/open_url"
            in source,
        "operator_launch_action":
            "/api/extensions/inventory/launch"
            in source,
        "no_install_endpoint":
            "/api/extensions/inventory/install"
            not in source,
        "no_remove_endpoint":
            "/api/extensions/inventory/remove"
            not in source,
        "no_update_endpoint":
            "/api/extensions/inventory/update"
            not in source,
        "state_file_not_created":
            "'state_file_created':False" in source,
        "configuration_unmodified":
            "'configuration_modified':False"
            in source,
        "recursive_manifest_discovery":
            ".rglob('*')" in block,
        "projector_separate":
            "'Vision Projector'" in block
            and "'excluded_from_language_model_selector':is_projector"
            in block,
        "safe_launch_allowlist":
            "EXTENSION_INVENTORY_SAFE_FLEET_LAUNCH"
            in block,
        "localhost_url_only":
            "http://127.0.0.1" in block
            and "http://localhost" in block,
        "ui_read_only_label":
            "PHASE 1 • READ ONLY" in source,
        "missing_state_explained":
            "manifest defaults; no state file created"
            in source,
        "legacy_controls_labeled":
            "Existing Manifest Controls" in source,
    }
    if not all(checks.values()):
        missing = [
            key for key, value in checks.items()
            if not value
        ]
        raise VerifyError(
            "Static inventory contract is incomplete: "
            + ", ".join(missing)
        )

    return {
        "passed": True,
        "checks": checks,
        "forbidden_write_primitives": [],
    }


def boundary_watch(root: Path) -> dict[str, Any]:
    code = (
        "import sys,unittest;"
        f"sys.path.insert(0,{str(root)!r});"
        "suite=unittest.defaultTestLoader.loadTestsFromName("
        "'tests.test_boundary_watch');"
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
    result = {
        "passed": (
            completed.returncode == 0
            and "Ran 5 tests" in combined
            and "OK" in combined
        ),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "tests": 5,
    }
    if result["passed"] is not True:
        raise VerifyError("Boundary Watch 5/5 failed.")
    return result


def main() -> int:
    package = Path(__file__).resolve().parent
    root = find_root(package)
    receipt_path = package / "LIVE_VERIFY_RECEIPT.json"

    before = protected_snapshot(root)
    receipt: dict[str, Any] = {
        "action":
            "extension_manager_inventory_health_phase1_exact_preview_verify",
        "created":
            datetime.now(timezone.utc).isoformat(),
        "state": "running",
        "verified": False,
        "root": str(root),
        "live_files_modified": False,
        "candidate_created": True,
        "apply_capability_present": False,
        "changed_files_proposed": [
            "core/foxai_web.py",
        ],
        "unchanged_files_explicit": [
            "core/server.py",
            "Config/application_registry.json",
            "Config/fleet_registry.json",
            "core/service_registry.py",
            "Config/extension_state.json",
        ],
        "delete_operations": [],
        "checks": {},
        "failure": None,
        "protected_changes": [],
    }

    try:
        receipt["checks"]["package_manifest"] = (
            package_manifest(package)
        )
        receipt["checks"]["source_snapshot"] = (
            source_snapshot_grounding(package)
        )
        receipt["checks"]["exact_artifacts"] = (
            exact_artifacts(package)
        )
        receipt["checks"]["live_baselines"] = (
            live_baselines(root)
        )
        receipt["checks"]["node_and_browser"] = (
            node_and_browser(package)
        )
        receipt["checks"]["backend_regression"] = (
            fake_backend_harness(package)
        )
        receipt["checks"]["live_inventory_preview"] = (
            backend_harness(package, root)
        )
        receipt["checks"]["legacy_controls_unchanged"] = (
            legacy_controls_unchanged(package)
        )
        receipt["checks"]["static_contract"] = (
            static_contract(package)
        )
        receipt["checks"]["boundary_watch"] = (
            boundary_watch(root)
        )

        after = protected_snapshot(root)
        changes = changed_paths(before, after)
        receipt["protected_changes"] = changes
        if changes:
            raise VerifyError(
                "Read-only verification changed protected files: "
                + repr(changes)
            )

        receipt.update({
            "state": "exact_preview_verified",
            "verified": True,
            "live_files_modified": False,
        })

    except Exception as exc:
        after = protected_snapshot(root)
        changes = changed_paths(before, after)
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

    receipt_path.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )

    live_preview = (
        receipt.get("checks") or {}
    ).get("live_inventory_preview") or {}
    summary = live_preview.get("summary") or {}

    print()
    print("=" * 72)
    print("FOXAI EXTENSION MANAGER")
    print("INVENTORY & HEALTH DASHBOARD — PHASE 1 EXACT PREVIEW")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Live files modified:", receipt["live_files_modified"])
    print("Apply capability present: False")
    print(
        "Live inventory items:",
        summary.get("total", "not completed"),
    )
    print(
        "Required problems:",
        summary.get("required_problems", "not completed"),
    )
    print(
        "Extension state file:",
        "present"
        if live_preview.get("state_file_exists")
        else "absent — manifest defaults",
    )
    print("Receipt:", receipt_path)
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    print()
    input("Press Enter to close...")

    return (
        0
        if receipt["state"] == "exact_preview_verified"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
