
from __future__ import annotations

import argparse
import ast
import datetime as dt
import difflib
import hashlib
import json
from pathlib import Path
import traceback

KNOWN_HASHES = {'core/foxai_web.py': 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7', 'START_FOXAI_WEB_PORTABLE.bat': '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1', 'START_FOXAI_WORKSHOP_PORTABLE.bat': '1e6b4bb53b81ba53c88fb6d88bf91f35ac5f730744e3ebd7329c6ec79af6728f', 'START_FOXAI_DESKTOP_PORTABLE.bat': '89e906d805f99392b4ecc2ea85aa688577517a26e577de3542159a1f5eaf046c', 'ComfyUI/main.py': 'd2580be49e7abb3218b1e7056844b2c72a2e7d8711268849429ad3b418c38bc9', 'foxai.py': '423bb098170dbaad2b96c6b07e31beee171904d286b8364457ce6357551c33d0'}
SHORTCUT_HASHES = {'desktop': {'filename': 'Launch FOXAI Workshop.bat - Shortcut.lnk', 'sha256': '2a41fab836312e95e40d5404bc379b050f31b7cd61bd1ac26bb22ce902aeae02'}, 'web': {'filename': 'START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk', 'sha256': 'af0f79cfc583c51c4108cb2c1baa86634bf427e2eb881c64ed51a5994f2e40dd'}}
EVIDENCE_HASHES = {'receipt.json': '2dca87bae5a13b6fec2f2cdb3381d85d85a367db547c7821017efa2554ec39bc', 'host_python_comparison.json': '807e7582af909a2d0475877a5c35aeae79a8d075ff43a3c68f6b7f0895b9046c', 'web_launcher_environment.json': '7c11d37083790c684202d423f60fdcb0854ef8ff93e1f09470c5597b05309596', 'webui_risk.json': '0325cb742230c6dc2ddb2ddf4341a8b32fc67eed83d7bcc2690ef8d3043d2fe6'}
EXPECTED_SOURCE_HASH = "ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7"
EXPECTED_PROPOSED_HASH = "2ec7aff76529a9c9a477d247753227bde9f03930f1d3bd05111b3b9a2fd3be2f"

OLD_HELPER = """def launch(cmd,cwd): return subprocess.Popen(cmd,cwd=str(cwd),creationflags=subprocess.CREATE_NEW_CONSOLE if os.name=='nt' else 0)
def pycmd():
    for p in [ROOT/'env'/'python'/'python.exe',ROOT/'python'/'python.exe',ROOT/'ComfyUI'/'python_embeded'/'python.exe']:
        if p.exists(): return [str(p)]
    return [sys.executable]
"""

NEW_HELPER = """def launch(cmd,cwd,env=None): return subprocess.Popen(cmd,cwd=str(cwd),env=env,creationflags=subprocess.CREATE_NEW_CONSOLE if os.name=='nt' else 0)
def comfy_child_env():
    env=os.environ.copy()
    for key in ('PYTHONNOUSERSITE','PYTHONHOME','PYTHONPATH'):
        env.pop(key,None)
    env['PYTHONDONTWRITEBYTECODE']='1'
    return env
def pycmd():
    for command in ('python.exe','python'):
        resolved=shutil.which(command)
        if resolved: return [str(Path(resolved).resolve())]
    for p in [COMFY/'python_embeded'/'python.exe',ROOT/'env'/'python'/'python.exe',ROOT/'python'/'python.exe']:
        if p.exists(): return [str(p)]
    return [sys.executable]
"""

OLD_CALL = "launch(pycmd()+[str(COMFY_MAIN),'--cpu'],COMFY)"
NEW_CALL = "launch(pycmd()+[str(COMFY_MAIN),'--cpu'],COMFY,env=comfy_child_env())"


def now():
    return dt.datetime.now(dt.timezone.utc)


def sha256_file(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value):
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_manifest(bundle: Path):
    manifest = json.loads(
        (bundle / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8")
    )
    failures = []
    for relative, expected in manifest.items():
        path = bundle / relative
        actual_hash = sha256_file(path)
        actual_size = path.stat().st_size if path.is_file() else None
        if not (
            path.is_file()
            and actual_hash == expected["sha256"]
            and actual_size == expected["size_bytes"]
        ):
            failures.append(relative)
    return {"checked": len(manifest), "failures": failures, "passed": not failures}


def verify_evidence(bundle: Path):
    directory = bundle / "INSPECTION_EVIDENCE"
    file_checks = {}
    for name, expected in EVIDENCE_HASHES.items():
        actual = sha256_file(directory / name)
        file_checks[name] = actual == expected

    receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
    host = json.loads(
        (directory / "host_python_comparison.json").read_text(encoding="utf-8")
    )
    launcher = json.loads(
        (directory / "web_launcher_environment.json").read_text(encoding="utf-8")
    )
    risk = json.loads((directory / "webui_risk.json").read_text(encoding="utf-8"))

    set_text = "\n".join(
        item.get("text", "") for item in launcher.get("set_commands") or []
    ).lower()
    content = {
        "inspection_verified": receipt.get("verified") is True,
        "inspection_state": (
            receipt.get("state") == "inspection_verified_ready_for_patch_design"
        ),
        "risk_confirmed": (
            risk.get("risk")
            == "HIGH_CONFIDENCE_WEBUI_INHERITS_BROKEN_HOST_PYTHON_ENV"
        ),
        "host_comparison_confirmed": (
            host.get("classification")
            == "CONFIRMED_ENVIRONMENT_INHERITANCE_FAILURE"
        ),
        "clean_torch_visible": (
            (host.get("clean_probe") or {}).get("data", {}).get("torch_available")
            is True
        ),
        "inherited_torch_hidden": (
            (host.get("inherited_probe") or {}).get("data", {}).get("torch_available")
            is False
        ),
        "web_launcher_blocks_user_site": "pythonnousersite=1" in set_text,
    }
    return {
        "file_checks": file_checks,
        "content_checks": content,
        "passed": all(file_checks.values()) and all(content.values()),
    }


def snapshot(root: Path):
    files = []
    for relative, expected in sorted(KNOWN_HASHES.items()):
        actual = sha256_file(root / relative)
        files.append({
            "path": relative,
            "expected": expected,
            "actual": actual,
            "matches": actual == expected,
        })

    usb_root = Path(root.anchor)
    shortcuts = []
    for name, item in SHORTCUT_HASHES.items():
        actual = sha256_file(usb_root / item["filename"])
        shortcuts.append({
            "name": name,
            "path": str(usb_root / item["filename"]),
            "expected": item["sha256"],
            "actual": actual,
            "matches": actual == item["sha256"],
        })

    return {
        "files": files,
        "shortcuts": shortcuts,
        "passed": (
            all(item["matches"] for item in files)
            and all(item["matches"] for item in shortcuts)
        ),
    }


def create_proposal(source: str):
    if source.count(OLD_HELPER) != 1:
        raise RuntimeError(
            f"Expected one old helper block, found {source.count(OLD_HELPER)}."
        )
    if source.count(OLD_CALL) != 2:
        raise RuntimeError(
            f"Expected two old ComfyUI calls, found {source.count(OLD_CALL)}."
        )
    proposed = source.replace(OLD_HELPER, NEW_HELPER, 1)
    proposed = proposed.replace(OLD_CALL, NEW_CALL)

    checks = {
        "old_helper_removed": OLD_HELPER not in proposed,
        "old_calls_removed": OLD_CALL not in proposed,
        "new_helper_count": proposed.count(NEW_HELPER),
        "new_call_count": proposed.count(NEW_CALL),
        "host_python_path_first": "resolved=shutil.which(command)" in proposed,
        "child_env_isolated": (
            "'PYTHONNOUSERSITE','PYTHONHOME','PYTHONPATH'" in proposed
        ),
    }
    if not (
        checks["old_helper_removed"]
        and checks["old_calls_removed"]
        and checks["new_helper_count"] == 1
        and checks["new_call_count"] == 2
        and checks["host_python_path_first"]
        and checks["child_env_isolated"]
    ):
        raise RuntimeError("Proposed patch structural validation failed.")
    ast.parse(proposed)
    return proposed, checks


def report_text(receipt, plan):
    lines = [
        "# FOXAI Phase 4C-P",
        "## WebUI ComfyUI Exact Patch Preview",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        "- Preview only: **True**",
        "- Live files modified: **False**",
        "- Services launched: **False**",
    ]
    if plan:
        lines += [
            "",
            "## Exact one-file proposal",
            "",
            f"- File: `{plan['action']['destination']}`",
            f"- Before SHA-256: `{plan['action']['expected_before_sha256']}`",
            f"- After SHA-256: `{plan['action']['expected_after_sha256']}`",
            f"- Added lines: **{plan['diff_summary']['added_lines']}**",
            f"- Removed lines: **{plan['diff_summary']['removed_lines']}**",
            "",
            "## Behavior",
            "",
            "- Resolve PATH host Python first, matching the working combined BAT.",
            "- Clean only the ComfyUI child environment.",
            "- Keep the isolated WebUI controller unchanged.",
            "- Apply the clean child environment to both ComfyUI routes.",
            "",
            "## Approval",
            "",
            f"- Plan ID: `{plan['plan_id']}`",
            f"- Exact phrase: **`{plan['approval_phrase']}`**",
            "",
            "**No apply capability is present.**",
        ]
    elif receipt.get("failure"):
        lines += ["", f"- Failure: `{receipt['failure']['message']}`"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()

    started = now()
    root = Path(args.root).resolve()
    bundle = Path(args.bundle).resolve()
    output = bundle / "PREVIEW_OUTPUT" / started.strftime("%Y%m%dT%H%M%SZ")
    upload = output / "UPLOAD_THIS"
    proposed_dir = upload / "PROPOSED_FILES_NOT_APPLIED" / "core"
    proposed_dir.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_phase4c_webui_comfy_exact_patch_preview",
        "created": started.isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "preview_only": True,
        "apply_capability_present": False,
        "live_files_modified": False,
        "files_deleted": False,
        "files_overwritten": False,
        "shortcut_changes": False,
        "launcher_changes": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "comfyui_launched": False,
        "writes_limited_to": str(output),
    }
    plan = None
    rc = 1

    try:
        package = verify_manifest(bundle)
        receipt["package_integrity"] = package
        if not package["passed"]:
            raise RuntimeError("Preview package integrity failed.")

        evidence = verify_evidence(bundle)
        receipt["inspection_evidence"] = evidence
        if not evidence["passed"]:
            raise RuntimeError("Phase 4B evidence verification failed.")

        before = snapshot(root)
        receipt["integrity_before"] = before
        if not before["passed"]:
            raise RuntimeError("Known WebUI/launcher integrity failed before preview.")

        live = root / "core" / "foxai_web.py"
        source_bytes = live.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        if source_hash != EXPECTED_SOURCE_HASH:
            raise RuntimeError(
                f"Live foxai_web.py changed after inspection: {source_hash}"
            )

        source = source_bytes.decode("utf-8")
        proposed, structure = create_proposal(source)
        proposed_bytes = proposed.encode("utf-8")
        proposed_hash = hashlib.sha256(proposed_bytes).hexdigest()
        if proposed_hash != EXPECTED_PROPOSED_HASH:
            raise RuntimeError(
                f"Proposed source hash mismatch: {proposed_hash}"
            )

        proposed_path = proposed_dir / "foxai_web.py"
        proposed_path.write_bytes(proposed_bytes)

        diff_lines = list(difflib.unified_diff(
            source.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile="a/core/foxai_web.py",
            tofile="b/core/foxai_web.py",
        ))
        diff_path = upload / "EXACT_PATCH.diff"
        diff_path.write_text("".join(diff_lines), encoding="utf-8", newline="\n")

        added = sum(
            1 for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        removed = sum(
            1 for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )

        plan_core = {
            "format": "foxai_phase4c_webui_comfy_patch_plan_v1",
            "created": now().isoformat(),
            "foxai_root": str(root),
            "inspection_risk": (
                "HIGH_CONFIDENCE_WEBUI_INHERITS_BROKEN_HOST_PYTHON_ENV"
            ),
            "action": {
                "kind": "modify_existing_source",
                "destination": str(live),
                "relative_destination": "core/foxai_web.py",
                "expected_before_sha256": EXPECTED_SOURCE_HASH,
                "expected_after_sha256": EXPECTED_PROPOSED_HASH,
                "expected_before_size_bytes": len(source_bytes),
                "expected_after_size_bytes": len(proposed_bytes),
                "backup_required_before_apply": True,
                "proposed_source": str(proposed_path),
            },
            "diff": {
                "path": str(diff_path),
                "sha256": sha256_file(diff_path),
            },
            "diff_summary": {
                "added_lines": added,
                "removed_lines": removed,
            },
            "structural_validation": structure,
            "existing_files_to_modify": ["core/foxai_web.py"],
            "files_to_add": [],
            "files_to_delete": [],
            "shortcuts_to_change": [],
            "launchers_to_change": [],
            "test_after_apply": {
                "launch": "START_FOXAI_WEB_PORTABLE.bat",
                "operator_action": "Click the WebUI ComfyUI Launch control.",
                "expected": [
                    "Host Python is selected from PATH.",
                    "User-site PyTorch is visible to the ComfyUI child.",
                    "ComfyUI responds on 127.0.0.1:8188.",
                    "WebUI remains responsive.",
                ],
            },
        }
        plan_id = canonical_hash(plan_core)
        plan_core["plan_id"] = plan_id
        plan_core["approval_phrase"] = (
            f"APPROVE FOXAI4C {plan_id[:12].upper()}"
        )
        plan = plan_core

        (upload / "EXACT_PATCH_PLAN.json").write_text(
            json.dumps(plan, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        after = snapshot(root)
        receipt["integrity_after"] = after
        if not after["passed"]:
            raise RuntimeError("Known WebUI/launcher integrity failed after preview.")

        receipt.update({
            "state": "patch_preview_verified_ready_for_operator_review",
            "verified": True,
            "plan_id": plan_id,
            "approval_phrase": plan["approval_phrase"],
            "current_source_sha256": source_hash,
            "proposed_source_sha256": proposed_hash,
        })
        rc = 0

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        try:
            receipt["integrity_after"] = snapshot(root)
        except Exception as final_exc:
            receipt["integrity_after_error"] = (
                f"{type(final_exc).__name__}: {final_exc}"
            )

    finally:
        completed = now()
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = round(
            (completed - started).total_seconds(), 2
        )

        (upload / "receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (upload / "report.md").write_text(
            report_text(receipt, plan), encoding="utf-8"
        )
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this entire UPLOAD_THIS folder. "
            "No live patch was applied and no service was launched.\n",
            encoding="utf-8",
        )

        print()
        print("Phase 4C preview state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("approval_phrase"):
            print("Approval phrase:", receipt["approval_phrase"])
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("No apply capability is present.")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
