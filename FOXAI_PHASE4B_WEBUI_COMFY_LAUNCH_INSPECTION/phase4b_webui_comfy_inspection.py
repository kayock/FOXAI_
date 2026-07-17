
from __future__ import annotations

import argparse
import ast
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

KNOWN_HASHES = {'core/foxai_web.py': 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7', 'core/server.py': '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81', 'core/service_registry.py': 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b', 'START_FOXAI_WEB_PORTABLE.bat': '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1', 'START_FOXAI_WORKSHOP_PORTABLE.bat': '1e6b4bb53b81ba53c88fb6d88bf91f35ac5f730744e3ebd7329c6ec79af6728f', 'START_FOXAI_DESKTOP_PORTABLE.bat': '89e906d805f99392b4ecc2ea85aa688577517a26e577de3542159a1f5eaf046c', 'ComfyUI/main.py': 'd2580be49e7abb3218b1e7056844b2c72a2e7d8711268849429ad3b418c38bc9', 'foxai.py': '423bb098170dbaad2b96c6b07e31beee171904d286b8364457ce6357551c33d0'}
SHORTCUT_HASHES = {'desktop': {'filename': 'Launch FOXAI Workshop.bat - Shortcut.lnk', 'sha256': '2a41fab836312e95e40d5404bc379b050f31b7cd61bd1ac26bb22ce902aeae02'}, 'web': {'filename': 'START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk', 'sha256': 'af0f79cfc583c51c4108cb2c1baa86634bf427e2eb881c64ed51a5994f2e40dd'}}

TARGET_TERMS = (
    "comfy",
    "8188",
    "main.py",
    "--cpu",
    "/api/launch/comfy",
    "/api/comfy/start",
    "subprocess",
    "popen",
    "pythonhome",
    "pythonpath",
    "pythonnousersite",
    "cwd=",
    "env=",
)

SCAN_ROOTS = ("core", "ui", "web", "static", "templates")
MAX_SCAN_FILES = 1200
MAX_FILE_BYTES = 2_000_000


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


def read_text_safe(path: Path):
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace"), "latin-1-replace"


def is_under(path: Path, root: Path):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def source_label(path_value, root: Path):
    if not path_value:
        return "NOT_FOUND"
    try:
        path = Path(path_value).resolve()
    except (OSError, TypeError, ValueError):
        return "UNKNOWN"
    return "USB" if is_under(path, root) else "HOST_PC"


def verify_package(bundle: Path):
    manifest_path = bundle / "PACKAGE_MANIFEST.json"
    result = {
        "manifest_exists": manifest_path.is_file(),
        "checked": 0,
        "failed": [],
        "passed": False,
    }
    if not manifest_path.is_file():
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in manifest.items():
        path = bundle / Path(relative)
        actual_hash = sha256_file(path)
        actual_size = path.stat().st_size if path.is_file() else None
        result["checked"] += 1
        if not (
            path.is_file()
            and actual_hash == expected["sha256"]
            and actual_size == expected["size_bytes"]
        ):
            result["failed"].append({
                "path": relative,
                "expected_sha256": expected["sha256"],
                "actual_sha256": actual_hash,
                "expected_size_bytes": expected["size_bytes"],
                "actual_size_bytes": actual_size,
            })
    result["passed"] = not result["failed"]
    return result


def snapshot_integrity(root: Path):
    files = []
    for relative, expected in sorted(KNOWN_HASHES.items()):
        path = root / Path(relative)
        actual = sha256_file(path)
        files.append({
            "path": relative,
            "source": "USB",
            "exists": path.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })

    usb_root = Path(root.anchor)
    shortcuts = []
    for name, item in SHORTCUT_HASHES.items():
        path = usb_root / item["filename"]
        actual = sha256_file(path)
        shortcuts.append({
            "name": name,
            "path": str(path),
            "source": "USB",
            "exists": path.is_file(),
            "expected_sha256": item["sha256"],
            "actual_sha256": actual,
            "matches_expected": actual == item["sha256"],
        })

    return {
        "files": files,
        "shortcuts": shortcuts,
        "failed_files": [x for x in files if not x["matches_expected"]],
        "failed_shortcuts": [x for x in shortcuts if not x["matches_expected"]],
        "passed": (
            all(x["matches_expected"] for x in files)
            and all(x["matches_expected"] for x in shortcuts)
        ),
    }


def snapshot_file(path: Path, root: Path, snapshot_root: Path):
    text, encoding = read_text_safe(path)
    relative = path.relative_to(root)
    output = snapshot_root / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")

    matches = []
    for number, line in enumerate(text.splitlines(), start=1):
        lower = line.lower()
        if any(term in lower for term in TARGET_TERMS):
            matches.append({"line": number, "text": line})

    return {
        "path": str(path),
        "relative_path": str(relative),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "encoding": encoding,
        "line_count": len(text.splitlines()),
        "matching_lines": matches,
        "snapshot_path": str(output),
    }


def bounded_targeted_search(root: Path, snapshot_root: Path):
    results = []
    files_seen = 0
    truncated = False
    extensions = {".py", ".bat", ".cmd", ".ps1", ".js", ".html", ".htm"}

    candidates = [
        root / "START_FOXAI_WEB_PORTABLE.bat",
        root / "START_FOXAI_WORKSHOP_PORTABLE.bat",
        root / "START_FOXAI_DESKTOP_PORTABLE.bat",
        root / "core" / "foxai_web.py",
        root / "core" / "server.py",
        root / "core" / "service_registry.py",
    ]

    for dirname in SCAN_ROOTS:
        scan_root = root / dirname
        if not scan_root.is_dir():
            continue
        stack = [(scan_root, 0)]
        while stack and files_seen < MAX_SCAN_FILES:
            current, depth = stack.pop()
            if depth > 6:
                continue
            try:
                for child in current.iterdir():
                    if child.is_dir():
                        stack.append((child, depth + 1))
                    elif child.is_file() and child.suffix.lower() in extensions:
                        candidates.append(child)
                        files_seen += 1
                        if files_seen >= MAX_SCAN_FILES:
                            truncated = bool(stack)
                            break
            except OSError:
                continue

    unique = {}
    for path in candidates:
        if not path.is_file():
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        unique[os.path.normcase(str(path.resolve()))] = path.resolve()

    for path in sorted(unique.values(), key=lambda p: str(p).lower()):
        text, encoding = read_text_safe(path)
        matches = []
        for number, line in enumerate(text.splitlines(), start=1):
            lower = line.lower()
            if any(term in lower for term in TARGET_TERMS):
                matches.append({"line": number, "text": line})
        if matches or path.name in {
            "START_FOXAI_WEB_PORTABLE.bat",
            "foxai_web.py",
        }:
            results.append({
                "path": str(path),
                "relative_path": str(path.relative_to(root)),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "encoding": encoding,
                "matching_lines": matches,
            })
            snapshot_file(path, root, snapshot_root)

    return {
        "scan_roots": list(SCAN_ROOTS),
        "max_scan_files": MAX_SCAN_FILES,
        "files_seen": files_seen,
        "result_file_count": len(results),
        "truncated": truncated,
        "results": results,
    }


class LaunchVisitor(ast.NodeVisitor):
    def __init__(self, source_lines):
        self.source_lines = source_lines
        self.route_functions = []
        self.process_calls = []
        self.env_assignments = []
        self.constants = []

    def text(self, node):
        if hasattr(ast, "get_source_segment"):
            return ast.get_source_segment(
                "\n".join(self.source_lines), node
            )
        return None

    def visit_FunctionDef(self, node):
        decorators = [self.text(dec) for dec in node.decorator_list]
        joined = " ".join(x or "" for x in decorators).lower()
        body_text = "\n".join(
            self.source_lines[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)]
        )
        lower = body_text.lower()
        if (
            "comfy" in joined
            or "comfy" in node.name.lower()
            or "8188" in lower
            or "main.py" in lower
        ):
            self.route_functions.append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "decorators": decorators,
                "source": body_text,
            })
        self.generic_visit(node)

    def visit_Assign(self, node):
        text = self.text(node) or ""
        lower = text.lower()
        if any(term in lower for term in (
            "pythonhome", "pythonpath", "pythonnousersite", "os.environ", "env"
        )):
            self.env_assignments.append({
                "line": node.lineno,
                "source": text,
            })
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            value = node.value.value
            if any(term in value.lower() for term in ("comfy", "8188", "main.py", "--cpu")):
                self.constants.append({
                    "line": node.lineno,
                    "value": value,
                    "source": text,
                })
        self.generic_visit(node)

    def visit_Call(self, node):
        func_text = self.text(node.func) or ""
        lower = func_text.lower()
        if any(name in lower for name in (
            "subprocess.popen",
            "subprocess.run",
            "os.startfile",
            "create_subprocess",
        )):
            call_text = self.text(node) or ""
            call_lower = call_text.lower()
            if any(term in call_lower for term in ("comfy", "main.py", "--cpu", "8188")):
                keywords = {
                    kw.arg: self.text(kw.value)
                    for kw in node.keywords
                    if kw.arg
                }
                self.process_calls.append({
                    "line": node.lineno,
                    "function": func_text,
                    "source": call_text,
                    "keywords": keywords,
                    "has_explicit_env": "env" in keywords,
                    "has_explicit_cwd": "cwd" in keywords,
                })
        self.generic_visit(node)


def ast_inspect_web_source(root: Path):
    path = root / "core" / "foxai_web.py"
    result = {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": sha256_file(path),
        "syntax_passed": False,
        "route_functions": [],
        "process_calls": [],
        "env_assignments": [],
        "constants": [],
        "error": None,
    }
    if not path.is_file():
        return result

    text, _ = read_text_safe(path)
    try:
        tree = ast.parse(text, filename=str(path))
        visitor = LaunchVisitor(text.splitlines())
        visitor.visit(tree)
        result.update({
            "syntax_passed": True,
            "route_functions": visitor.route_functions,
            "process_calls": visitor.process_calls,
            "env_assignments": visitor.env_assignments,
            "constants": visitor.constants,
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def parse_batch_environment(root: Path):
    path = root / "START_FOXAI_WEB_PORTABLE.bat"
    result = {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": sha256_file(path),
        "set_commands": [],
        "python_commands": [],
        "passed": False,
    }
    if not path.is_file():
        return result

    text, _ = read_text_safe(path)
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("set "):
            result["set_commands"].append({
                "line": number,
                "text": stripped,
            })
        if "python" in lower or "foxai_web.py" in lower:
            result["python_commands"].append({
                "line": number,
                "text": stripped,
            })
    result["passed"] = True
    return result


def run_host_probe(executable: Path, root: Path, mode: str, env):
    code = (
        "import json,site,sys;"
        "out={'mode':" + repr(mode) + ","
        "'executable':sys.executable,"
        "'enable_user_site':site.ENABLE_USER_SITE,"
        "'user_site':site.getusersitepackages(),"
        "'sys_path':sys.path};"
        "\ntry:\n"
        " import torch\n"
        " out.update({'torch_available':True,"
        "'torch_version':getattr(torch,'__version__',None),"
        "'torch_origin':getattr(torch,'__file__',None),"
        "'cuda_available':bool(torch.cuda.is_available()),"
        "'error':None})\n"
        "except Exception as exc:\n"
        " out.update({'torch_available':False,"
        "'torch_version':None,'torch_origin':None,"
        "'cuda_available':None,"
        "'error':type(exc).__name__+': '+str(exc)})\n"
        "print(json.dumps(out))"
    )

    result = {
        "mode": mode,
        "executable": str(executable),
        "source": source_label(executable, root),
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "data": None,
        "passed": False,
    }
    try:
        completed = subprocess.run(
            [str(executable), "-c", code],
            cwd=str(root / "ComfyUI"),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        result["returncode"] = completed.returncode
        result["stdout"] = completed.stdout[-12000:]
        result["stderr"] = completed.stderr[-12000:]
        if completed.stdout.strip():
            result["data"] = json.loads(completed.stdout.strip().splitlines()[-1])
        result["passed"] = (
            completed.returncode == 0
            and isinstance(result["data"], dict)
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def host_python_comparison(root: Path):
    resolved = shutil.which("python.exe") or shutil.which("python")
    result = {
        "resolved_path": (
            str(Path(resolved).resolve()) if resolved else None
        ),
        "source": source_label(resolved, root),
        "exists": bool(resolved and Path(resolved).is_file()),
        "inherited_probe": None,
        "clean_probe": None,
        "classification": "HOST_PYTHON_NOT_FOUND",
    }
    if not result["exists"]:
        return result

    executable = Path(result["resolved_path"])

    inherited_env = os.environ.copy()
    inherited_env["PYTHONDONTWRITEBYTECODE"] = "1"

    clean_env = os.environ.copy()
    clean_env.pop("PYTHONNOUSERSITE", None)
    clean_env["PYTHONHOME"] = ""
    clean_env["PYTHONPATH"] = ""
    clean_env["PYTHONDONTWRITEBYTECODE"] = "1"

    inherited = run_host_probe(
        executable, root, "INHERITED_CONTROLLER_ENV", inherited_env
    )
    clean = run_host_probe(
        executable, root, "CLEAN_WORKING_LAUNCHER_ENV", clean_env
    )
    result["inherited_probe"] = inherited
    result["clean_probe"] = clean

    inherited_torch = bool(
        inherited.get("data", {}).get("torch_available")
    )
    clean_torch = bool(clean.get("data", {}).get("torch_available"))

    if not inherited_torch and clean_torch:
        result["classification"] = "CONFIRMED_ENVIRONMENT_INHERITANCE_FAILURE"
    elif inherited_torch and clean_torch:
        result["classification"] = "TORCH_VISIBLE_IN_BOTH_ENVIRONMENTS"
    elif not inherited_torch and not clean_torch:
        result["classification"] = "HOST_TORCH_UNAVAILABLE_IN_BOTH_ENVIRONMENTS"
    else:
        result["classification"] = "INHERITED_VISIBLE_CLEAN_HIDDEN_UNEXPECTED"

    return result


def infer_webui_risk(batch_env, ast_report, host_compare):
    evidence = []
    risk = "UNDETERMINED"

    set_text = "\n".join(
        item["text"] for item in batch_env.get("set_commands") or []
    ).lower()

    batch_blocks_user_site = "pythonnousersite=1" in set_text
    batch_sets_pythonhome = "pythonhome=" in set_text
    batch_sets_pythonpath = "pythonpath=" in set_text

    process_calls = ast_report.get("process_calls") or []
    comfy_calls = [call for call in process_calls]
    any_explicit_env = any(call.get("has_explicit_env") for call in comfy_calls)
    any_explicit_cwd = any(call.get("has_explicit_cwd") for call in comfy_calls)

    evidence.append({
        "check": "web_launcher_blocks_user_site",
        "value": batch_blocks_user_site,
    })
    evidence.append({
        "check": "web_launcher_sets_pythonhome",
        "value": batch_sets_pythonhome,
    })
    evidence.append({
        "check": "web_launcher_sets_pythonpath",
        "value": batch_sets_pythonpath,
    })
    evidence.append({
        "check": "web_source_comfy_call_has_explicit_env",
        "value": any_explicit_env,
    })
    evidence.append({
        "check": "web_source_comfy_call_has_explicit_cwd",
        "value": any_explicit_cwd,
    })
    evidence.append({
        "check": "host_probe_classification",
        "value": host_compare.get("classification"),
    })

    inherited_failure = (
        host_compare.get("classification")
        == "CONFIRMED_ENVIRONMENT_INHERITANCE_FAILURE"
    )

    if inherited_failure and batch_blocks_user_site and not any_explicit_env:
        risk = "HIGH_CONFIDENCE_WEBUI_INHERITS_BROKEN_HOST_PYTHON_ENV"
    elif inherited_failure and batch_blocks_user_site:
        risk = "LIKELY_ENVIRONMENT_BUG_VERIFY_EXPLICIT_ENV_CONTENT"
    elif inherited_failure:
        risk = "HOST_ENVIRONMENT_SENSITIVE_SOURCE_REVIEW_REQUIRED"
    elif (
        host_compare.get("classification")
        == "TORCH_VISIBLE_IN_BOTH_ENVIRONMENTS"
    ):
        risk = "ENVIRONMENT_NOT_REPRODUCED_CHECK_COMMAND_CWD_AND_ERROR_CAPTURE"
    else:
        risk = "HOST_BACKEND_OR_SOURCE_ISSUE"

    return {
        "risk": risk,
        "evidence": evidence,
        "recommended_patch_scope": (
            "No patch applied. Likely future scope is limited to the WebUI "
            "ComfyUI child-process environment, working directory, command, "
            "and stderr/port-8188 diagnostics."
        ),
    }


def make_report(receipt, results):
    host = results.get("host_python_comparison") or {}
    web_risk = results.get("webui_risk") or {}
    ast_report = results.get("ast_report") or {}
    batch = results.get("web_launcher_environment") or {}

    lines = [
        "# FOXAI Phase 4B",
        "## WebUI ComfyUI Launch Read-Only Inspection",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        "- Live files modified: **False**",
        "- FOXAI/WebUI/ComfyUI launched: **False**",
        "- Network used: **False**",
        "",
        "## Host Python comparison",
        "",
        f"- Resolved host Python: `{host.get('resolved_path')}`",
        f"- Classification: **{host.get('classification')}**",
        f"- Inherited environment sees torch: "
        f"**{(host.get('inherited_probe') or {}).get('data', {}).get('torch_available')}**",
        f"- Clean launcher environment sees torch: "
        f"**{(host.get('clean_probe') or {}).get('data', {}).get('torch_available')}**",
        "",
        "## Web launcher/source inspection",
        "",
        f"- Web launcher SET commands captured: "
        f"**{len(batch.get('set_commands') or [])}**",
        f"- Comfy-related process calls found in `core/foxai_web.py`: "
        f"**{len(ast_report.get('process_calls') or [])}**",
        f"- WebUI risk classification: **{web_risk.get('risk')}**",
        "",
        "## Next gate",
        "",
        "Review this evidence before creating any exact WebUI patch preview.",
    ]

    if receipt.get("failure"):
        lines += [
            "",
            "## Failure",
            "",
            f"`{receipt['failure'].get('message')}`",
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
    output = (
        bundle / "INSPECTION_OUTPUT" / started.strftime("%Y%m%dT%H%M%SZ")
    )
    upload = output / "UPLOAD_THIS"
    snapshots = upload / "SOURCE_SNAPSHOTS"
    snapshots.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_phase4b_webui_comfy_launch_read_only_inspection",
        "created": started.isoformat(),
        "root": str(root),
        "state": "stopped_fail_closed",
        "verified": False,
        "read_only_inspection": True,
        "live_files_modified": False,
        "files_deleted": False,
        "files_overwritten": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "comfyui_launched": False,
        "browser_launched": False,
        "model_loaded": False,
        "entire_drive_recursive_scan": False,
        "child_process_policy": (
            "Only two local host-Python import probes; no service launch."
        ),
        "writes_limited_to": str(output),
    }
    results = {"root": str(root)}
    exit_code = 1

    try:
        print("1/7 Verifying inspection package...", flush=True)
        results["package_integrity"] = verify_package(bundle)
        if not results["package_integrity"]["passed"]:
            raise RuntimeError("Inspection package integrity failed.")

        print("2/7 Verifying known WebUI/launcher integrity...", flush=True)
        results["integrity_before"] = snapshot_integrity(root)
        if not results["integrity_before"]["passed"]:
            raise RuntimeError(
                "A known WebUI/launcher/source file or shortcut changed before inspection."
            )

        print("3/7 Capturing exact targeted source evidence...", flush=True)
        results["targeted_search"] = bounded_targeted_search(
            root, snapshots
        )

        print("4/7 Parsing WebUI ComfyUI launch code...", flush=True)
        results["ast_report"] = ast_inspect_web_source(root)
        if not results["ast_report"]["syntax_passed"]:
            raise RuntimeError("core/foxai_web.py AST inspection failed.")

        print("5/7 Parsing Web launcher environment...", flush=True)
        results["web_launcher_environment"] = parse_batch_environment(root)
        if not results["web_launcher_environment"]["passed"]:
            raise RuntimeError("Web launcher environment inspection failed.")

        print("6/7 Comparing inherited and clean host-Python environments...", flush=True)
        results["host_python_comparison"] = host_python_comparison(root)

        print("7/7 Classifying WebUI ComfyUI launch risk...", flush=True)
        results["webui_risk"] = infer_webui_risk(
            results["web_launcher_environment"],
            results["ast_report"],
            results["host_python_comparison"],
        )

        results["integrity_after"] = snapshot_integrity(root)
        if not results["integrity_after"]["passed"]:
            raise RuntimeError(
                "A known WebUI/launcher/source file or shortcut changed during inspection."
            )

        receipt["state"] = "inspection_verified_ready_for_patch_design"
        receipt["verified"] = True
        receipt["risk"] = results["webui_risk"]["risk"]
        exit_code = 0

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        try:
            results["integrity_after"] = snapshot_integrity(root)
        except Exception as final_exc:
            receipt["integrity_after_error"] = (
                f"{type(final_exc).__name__}: {final_exc}"
            )

    finally:
        completed = utc_now()
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = round(
            (completed - started).total_seconds(), 2
        )

        outputs = {
            "receipt.json": receipt,
            "integrity_before.json": results.get("integrity_before", {}),
            "integrity_after.json": results.get("integrity_after", {}),
            "targeted_search.json": results.get("targeted_search", {}),
            "ast_report.json": results.get("ast_report", {}),
            "web_launcher_environment.json": results.get(
                "web_launcher_environment", {}
            ),
            "host_python_comparison.json": results.get(
                "host_python_comparison", {}
            ),
            "webui_risk.json": results.get("webui_risk", {}),
        }
        for filename, data in outputs.items():
            (upload / filename).write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        (upload / "report.md").write_text(
            make_report(receipt, results), encoding="utf-8"
        )
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this entire UPLOAD_THIS folder. "
            "No live file was changed and no service was launched.\n",
            encoding="utf-8",
        )

        print()
        print("Phase 4B state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("risk"):
            print("Risk:", receipt["risk"])
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("No patch was proposed or applied.")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
