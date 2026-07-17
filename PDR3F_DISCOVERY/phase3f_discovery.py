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
import traceback

EXPECTED_BASELINES = {'Config/fleet_registry.json': '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6', 'Config/model_sources.json': 'c17eb3b8b6c93734f7e117522213c95af6c105fe26400d0560768fe586e21c91', 'core/engineer_agent.py': 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19', 'core/foxai_web.py': 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7', 'core/model_sources.py': 'e00a861265eff8826c4d7eeb89b3765e719b88f349811a2e608525d8a3f91ea2', 'core/security_containment.py': '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24', 'core/server.py': '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81', 'core/service_registry.py': 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b', 'env/python/python314._pth': '48d77ccee161647ef7053cb563d3b37b4053938d5ad92ae64ccedc2165bcd42d', 'Launch FOXAI Workshop.bat': '7f974eeeaa66c6fd331b6b3e8cb5f312d25a410761817ad35408ccb47acd4480', 'START_FOXAI_WEB_PORTABLE.bat': '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1', 'tests/test_boundary_watch.py': 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382', 'tests/test_model_sources.py': 'ec94f8b8d90d36f05385db74400dd99b436cd4e488b1b517bcb77442a16fc6f2', 'ui/main_window.py': '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3'}
EXPECTED_SHORTCUTS = {'desktop': {'filename': 'Launch FOXAI Workshop.bat - Shortcut.lnk', 'sha256': '2a41fab836312e95e40d5404bc379b050f31b7cd61bd1ac26bb22ce902aeae02'}, 'web': {'filename': 'START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk', 'sha256': 'af0f79cfc583c51c4108cb2c1baa86634bf427e2eb881c64ed51a5994f2e40dd'}}

SCRIPT_EXTENSIONS = {".bat", ".cmd", ".ps1", ".py"}
MATCH_TERMS = (
    "comfy", "8188", "main.py", "--cpu", "popen", "subprocess",
    "start ", "python.exe", "pythonw.exe", "launch"
)

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

def snapshot_protected(root: Path):
    baselines = []
    for relative, expected in sorted(EXPECTED_BASELINES.items()):
        path = root / Path(relative)
        actual = sha256_file(path)
        baselines.append({
            "path": relative,
            "exists": path.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })

    usb_root = Path(root.anchor)
    shortcuts = {}
    for key, item in EXPECTED_SHORTCUTS.items():
        path = usb_root / item["filename"]
        actual = sha256_file(path)
        shortcuts[key] = {
            "path": str(path),
            "exists": path.is_file(),
            "expected_sha256": item["sha256"],
            "actual_sha256": actual,
            "matches_expected": actual == item["sha256"],
        }

    return {
        "baselines": baselines,
        "shortcuts": shortcuts,
        "passed": (
            all(item["matches_expected"] for item in baselines)
            and all(item["matches_expected"] for item in shortcuts.values())
        ),
    }

def powershell_path():
    candidates = [
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Sysnative" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None

def run_shortcut_probe(root: Path, bundle: Path, output: Path):
    ps = powershell_path()
    result = {
        "powershell_path": str(ps) if ps else None,
        "ran": False,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "output_exists": False,
        "data": None,
    }
    if ps is None:
        return result

    command = [
        str(ps),
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-File", str(bundle / "probe_shortcuts.ps1"),
        "-UsbRoot", root.anchor,
        "-OutputPath", str(output),
    ]
    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    result.update({
        "ran": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
        "output_exists": output.is_file(),
    })
    if output.is_file():
        result["data"] = json.loads(output.read_text(encoding="utf-8-sig"))
    return result

def root_listing(root: Path):
    items = []
    for path in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if path.name.startswith("."):
            continue
        try:
            items.append({
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "size_bytes": path.stat().st_size if path.is_file() else None,
                "sha256": sha256_file(path) if path.is_file() else None,
            })
        except OSError as exc:
            items.append({
                "name": path.name,
                "type": "error",
                "error": f"{type(exc).__name__}: {exc}",
            })
    return items

def list_shallow_directory(path: Path):
    result = {
        "path": str(path),
        "exists": path.is_dir(),
        "items": [],
    }
    if not path.is_dir():
        return result
    for child in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        try:
            result["items"].append({
                "name": child.name,
                "type": "directory" if child.is_dir() else "file",
                "size_bytes": child.stat().st_size if child.is_file() else None,
                "sha256": sha256_file(child) if child.is_file() and child.stat().st_size <= 20_000_000 else None,
            })
        except OSError as exc:
            result["items"].append({
                "name": child.name,
                "type": "error",
                "error": f"{type(exc).__name__}: {exc}",
            })
    return result

def snapshot_script(path: Path, snapshot_root: Path, root: Path):
    text, encoding = read_text_safe(path)
    relative = path.relative_to(root)
    out = snapshot_root / relative
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    lines = text.splitlines()
    matches = []
    for number, line in enumerate(lines, start=1):
        lower = line.lower()
        if any(term in lower for term in MATCH_TERMS):
            matches.append({"line": number, "text": line})
    return {
        "path": str(path),
        "relative_path": str(relative),
        "exists": True,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "source_encoding": encoding,
        "line_count": len(lines),
        "matching_lines": matches,
        "snapshot_path": str(out),
    }

def extract_set_variables(text: str, script_dir: Path):
    variables = {
        "~dp0": str(script_dir) + os.sep,
        "CD": str(script_dir),
    }
    set_re = re.compile(r'^\s*set\s+"?([A-Za-z_][A-Za-z0-9_]*)=(.*?)"?\s*$', re.I)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = set_re.match(line)
        if not match:
            continue
        name, value = match.group(1), match.group(2)
        value = value.rstrip('"')
        value = value.replace("%~dp0", str(script_dir) + os.sep)
        for key, known in list(variables.items()):
            value = re.sub(
                rf"%{re.escape(key)}%",
                lambda _: known,
                value,
                flags=re.I,
            )
        variables[name.upper()] = value
    return variables

def expand_known_variables(value: str, variables: dict[str, str], script_dir: Path):
    expanded = value.replace("%~dp0", str(script_dir) + os.sep)
    for _ in range(5):
        before = expanded
        for key, known in variables.items():
            expanded = re.sub(
                rf"%{re.escape(key)}%",
                lambda _: known,
                expanded,
                flags=re.I,
            )
        if expanded == before:
            break
    return os.path.expandvars(expanded)

def discover_script_references(path: Path, root: Path):
    text, _ = read_text_safe(path)
    variables = extract_set_variables(text, path.parent)
    refs = []
    unresolved = []

    quoted = re.compile(r'"([^"\r\n]+\.(?:bat|cmd|ps1|py))"', re.I)
    unquoted = re.compile(r'(?<![\w.])([A-Za-z0-9_%~:\\/ .-]+\.(?:bat|cmd|ps1|py))(?![\w.])', re.I)

    candidates = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern in (quoted, unquoted):
            for match in pattern.finditer(line):
                candidates.append((line_number, line, match.group(1).strip()))

    seen = set()
    for line_number, line, token in candidates:
        expanded = expand_known_variables(token, variables, path.parent).strip()
        expanded = expanded.strip('"').strip("'")
        if "%" in expanded:
            unresolved.append({
                "source": str(path),
                "line": line_number,
                "token": token,
                "expanded": expanded,
                "text": line,
            })
            continue

        candidate = Path(expanded)
        if not candidate.is_absolute():
            candidate = (path.parent / candidate).resolve()
        else:
            candidate = candidate.resolve()

        try:
            candidate.relative_to(root)
        except ValueError:
            unresolved.append({
                "source": str(path),
                "line": line_number,
                "token": token,
                "expanded": str(candidate),
                "reason": "outside_foxai_root",
                "text": line,
            })
            continue

        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        seen.add(key)
        refs.append({
            "source": str(path),
            "line": line_number,
            "token": token,
            "resolved": str(candidate),
            "exists": candidate.is_file(),
            "extension": candidate.suffix.lower(),
            "text": line,
        })
    return refs, unresolved

def bounded_launch_chain(root: Path, start_files: list[Path], snapshot_root: Path):
    queue = [(path, 0) for path in start_files if path.is_file()]
    visited = set()
    files = []
    edges = []
    unresolved = []
    max_depth = 5
    max_files = 40

    while queue and len(visited) < max_files:
        path, depth = queue.pop(0)
        key = os.path.normcase(str(path.resolve()))
        if key in visited:
            continue
        visited.add(key)

        if path.suffix.lower() not in SCRIPT_EXTENSIONS:
            continue
        try:
            snap = snapshot_script(path, snapshot_root, root)
        except Exception as exc:
            files.append({
                "path": str(path),
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue

        snap["depth"] = depth
        files.append(snap)
        if depth >= max_depth:
            continue

        refs, unresolved_refs = discover_script_references(path, root)
        edges.extend(refs)
        unresolved.extend(unresolved_refs)
        for ref in refs:
            child = Path(ref["resolved"])
            if child.is_file() and child.suffix.lower() in SCRIPT_EXTENSIONS:
                queue.append((child, depth + 1))

    return {
        "start_files": [str(p) for p in start_files],
        "max_depth": max_depth,
        "max_files": max_files,
        "visited_file_count": len(files),
        "files": files,
        "reference_edges": edges,
        "unresolved_references": unresolved,
        "truncated": bool(queue),
    }

def targeted_source_matches(root: Path):
    targets = [
        root / "foxai.py",
        root / "ui" / "main_window.py",
        root / "core" / "foxai_web.py",
    ]
    results = []
    terms = ("comfy", "8188", "subprocess", "popen", "startfile", "launch")
    for path in targets:
        item = {
            "path": str(path),
            "exists": path.is_file(),
            "sha256": sha256_file(path),
            "matches": [],
        }
        if path.is_file():
            text, encoding = read_text_safe(path)
            item["encoding"] = encoding
            lines = text.splitlines()
            for number, line in enumerate(lines, start=1):
                if any(term in line.lower() for term in terms):
                    item["matches"].append({
                        "line": number,
                        "text": line,
                    })
        results.append(item)
    return results

def make_report(receipt):
    lines = [
        "# FOXAI Portable Desktop Runtime Phase 3F",
        "## Combined Startup Read-Only Discovery",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        "- Live FOXAI files modified: **False**",
        "- Shortcuts modified: **False**",
        "- FOXAI launched: **False**",
        "- ComfyUI launched: **False**",
        "- Network used: **False**",
        "",
    ]

    shortcut = receipt.get("shortcut_probe") or {}
    data = shortcut.get("data") or {}
    items = data.get("items") or []
    if items:
        lines += ["## Shortcut details", ""]
        for item in items:
            lines += [
                f"### {item.get('name')}",
                f"- Exists: **{item.get('exists')}**",
                f"- Target: `{item.get('target_path')}`",
                f"- Arguments: `{item.get('arguments')}`",
                f"- Working directory: `{item.get('working_directory')}`",
                "",
            ]

    chain = receipt.get("launch_chain") or {}
    lines += [
        "## Launch-chain capture",
        "",
        f"- Script files captured: **{chain.get('visited_file_count', 0)}**",
        f"- Reference edges: **{len(chain.get('reference_edges') or [])}**",
        f"- Unresolved references: **{len(chain.get('unresolved_references') or [])}**",
        f"- Truncated: **{chain.get('truncated')}**",
        "",
        "Exact script snapshots and matching ComfyUI/startup lines are included in `SOURCE_SNAPSHOTS` and `launch_chain.json`.",
        "",
        "## Next gate",
        "",
        "Upload this discovery evidence. No combined launcher has been proposed or applied yet.",
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
    output = bundle / "DISCOVERY_OUTPUT" / started.strftime("%Y%m%dT%H%M%SZ")
    upload = output / "UPLOAD_THIS"
    snapshots = upload / "SOURCE_SNAPSHOTS"
    upload.mkdir(parents=True, exist_ok=True)
    snapshots.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_pdr_phase3f_combined_startup_read_only_discovery",
        "created": started.isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "read_only_discovery": True,
        "live_files_modified": False,
        "shortcut_changes": False,
        "existing_launcher_changes": False,
        "source_changes": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "desktop_gui_launched": False,
        "comfyui_launched": False,
        "browser_launched": False,
        "recursive_drive_scan": False,
        "powershell_used_only_for_shortcut_metadata": True,
        "writes_limited_to": str(output),
    }
    exit_code = 1

    try:
        protected_before = snapshot_protected(root)
        receipt["protected_before"] = protected_before
        if not protected_before["passed"]:
            raise RuntimeError("Protected FOXAI state failed before discovery.")

        shortcut_json = upload / "shortcut_details.json"
        shortcut_probe = run_shortcut_probe(root, bundle, shortcut_json)
        receipt["shortcut_probe"] = shortcut_probe
        if (
            not shortcut_probe["ran"]
            or shortcut_probe["returncode"] != 0
            or not shortcut_probe["output_exists"]
        ):
            raise RuntimeError("Shortcut metadata probe failed.")

        shortcut_items = (shortcut_probe.get("data") or {}).get("items") or []
        desktop_items = [
            item for item in shortcut_items
            if item.get("name") == EXPECTED_SHORTCUTS["desktop"]["filename"]
        ]
        if not desktop_items or not desktop_items[0].get("exists"):
            raise RuntimeError("The working Desktop shortcut was not resolved.")
        desktop_target = Path(desktop_items[0].get("target_path") or "")
        if not desktop_target.is_file():
            raise RuntimeError("The Desktop shortcut target does not exist.")

        root_info = root_listing(root)
        (upload / "foxai_root_listing.json").write_text(
            json.dumps(root_info, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        shallow_paths = [
            root / "ComfyUI",
            root / "comfyui",
            root / "System",
            root / "Scripts",
            root / "Runtime",
        ]
        shallow = [list_shallow_directory(path) for path in shallow_paths]
        (upload / "shallow_candidate_directories.json").write_text(
            json.dumps(shallow, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        start_files = [
            desktop_target.resolve(),
            root / "Launch FOXAI Workshop.bat",
            root / "START_FOXAI_WEB_PORTABLE.bat",
            root / "START_FOXAI_DESKTOP_PORTABLE.bat",
        ]
        unique_starts = []
        seen = set()
        for path in start_files:
            if path.is_file():
                key = os.path.normcase(str(path.resolve()))
                if key not in seen:
                    seen.add(key)
                    unique_starts.append(path.resolve())

        chain = bounded_launch_chain(root, unique_starts, snapshots)
        receipt["launch_chain"] = chain
        (upload / "launch_chain.json").write_text(
            json.dumps(chain, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        targeted = targeted_source_matches(root)
        receipt["targeted_source_matches"] = targeted
        (upload / "targeted_source_matches.json").write_text(
            json.dumps(targeted, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Summarize likely ComfyUI startup evidence without guessing.
        comfy_evidence = []
        for file_item in chain["files"]:
            for match in file_item.get("matching_lines") or []:
                if any(
                    term in match["text"].lower()
                    for term in ("comfy", "8188", "main.py", "--cpu")
                ):
                    comfy_evidence.append({
                        "source": file_item.get("path"),
                        "line": match["line"],
                        "text": match["text"],
                    })
        for source_item in targeted:
            for match in source_item.get("matches") or []:
                if any(
                    term in match["text"].lower()
                    for term in ("comfy", "8188", "main.py", "--cpu")
                ):
                    comfy_evidence.append({
                        "source": source_item.get("path"),
                        "line": match["line"],
                        "text": match["text"],
                    })
        receipt["comfyui_startup_evidence_count"] = len(comfy_evidence)
        (upload / "comfyui_startup_evidence.json").write_text(
            json.dumps(comfy_evidence, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        protected_after = snapshot_protected(root)
        receipt["protected_after"] = protected_after
        if not protected_after["passed"]:
            raise RuntimeError("Protected FOXAI state failed after discovery.")

        receipt["state"] = "discovery_verified_ready_for_combined_launcher_design"
        receipt["verified"] = True
        exit_code = 0

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        try:
            receipt["protected_after"] = snapshot_protected(root)
        except Exception as final_exc:
            receipt["protected_after_error"] = (
                f"{type(final_exc).__name__}: {final_exc}"
            )
    finally:
        completed = utc_now()
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = round((completed - started).total_seconds(), 2)

        (upload / "receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (upload / "report.md").write_text(
            make_report(receipt), encoding="utf-8"
        )
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this UPLOAD_THIS folder only. "
            "No launcher or shortcut was changed, and nothing was launched.\n",
            encoding="utf-8",
        )

        print()
        print("Phase 3F discovery state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("No combined launcher was proposed or applied.")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
