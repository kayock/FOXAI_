from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
from datetime import datetime, timezone

BUNDLE = Path(__file__).resolve().parents[1]
PAYLOAD = BUNDLE / "payload"
BASELINE = BUNDLE / "baseline"
MANIFEST = BUNDLE / "baseline_manifest.json"
TEST_FILE = BUNDLE / "tests" / "test_phase1_security.py"
TARGETS = [
    "core/agents.py",
    "core/director.py",
    "core/engineer_agent.py",
    "core/smart_search.py",
    "core/foxai_web.py",
    "core/security_containment.py",
    "Config/engineering_airlock_model.conf",
    "Config/engineering_airlock_policy.csv",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def locate_root(arg: str | None) -> Path:
    candidates = []
    if arg:
        candidates.append(Path(arg))
    if os.environ.get("FOXAI_ROOT"):
        candidates.append(Path(os.environ["FOXAI_ROOT"]))
    candidates += [Path.cwd(), BUNDLE.parent, BUNDLE.parent.parent]
    for p in candidates:
        p = p.resolve()
        if (p / "core" / "foxai_web.py").exists() and (p / "START_FOXAI_WEB_PORTABLE.bat").exists():
            return p
    raise SystemExit("FOXAI root not found. Pass it as the first argument, for example: PREVIEW_PHASE1.bat Z:\\FOXAI")


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def validate_baseline(root: Path) -> list[str]:
    manifest = load_manifest()
    problems = []
    for rel, expected in manifest["baseline"].items():
        live = root / rel
        if not live.exists():
            problems.append(f"MISSING: {rel}")
        else:
            actual = sha(live)
            if actual != expected:
                problems.append(f"HASH MISMATCH: {rel}\n  expected {expected}\n  actual   {actual}")
    for rel in manifest.get("expected_absent", []):
        if (root / rel).exists():
            problems.append(f"EXPECTED ABSENT BUT EXISTS: {rel}")
    return problems


def compile_payload() -> list[str]:
    errors = []
    for rel in TARGETS:
        p = PAYLOAD / rel
        if p.suffix == ".py":
            try:
                py_compile.compile(str(p), doraise=True)
            except Exception as exc:
                errors.append(f"{rel}: {exc}")
    return errors


def run_tests() -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(TEST_FILE)], cwd=str(BUNDLE), text=True, capture_output=True)
    return proc.returncode, proc.stdout + proc.stderr


def write_diff(root: Path, out: Path) -> None:
    chunks = []
    for rel in TARGETS:
        old = root / rel
        new = PAYLOAD / rel
        old_text = old.read_text(encoding="utf-8", errors="replace").splitlines(True) if old.exists() else []
        new_text = new.read_text(encoding="utf-8", errors="replace").splitlines(True)
        chunks.extend(difflib.unified_diff(old_text, new_text, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
    out.write_text("".join(chunks), encoding="utf-8")


def preview(root: Path) -> int:
    out = BUNDLE / "preview_output"
    out.mkdir(exist_ok=True)
    problems = validate_baseline(root)
    compile_errors = compile_payload()
    test_code, test_output = run_tests()
    write_diff(root, out / "PHASE1_EXACT.diff")
    report = {
        "mode": "preview_only",
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "foxai_root": str(root),
        "baseline_ok": not problems,
        "baseline_problems": problems,
        "compile_ok": not compile_errors,
        "compile_errors": compile_errors,
        "tests_ok": test_code == 0,
        "test_output": test_output,
        "changed_or_added": TARGETS,
        "writes_to_live_tree": False,
        "diff": str(out / "PHASE1_EXACT.diff"),
    }
    (out / "PREVIEW_RECEIPT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nKAYOCKTHEOS PHASE 1 PREVIEW")
    print("=" * 72)
    print(f"FOXAI root: {root}")
    print(f"Baseline hashes: {'PASS' if not problems else 'BLOCKED'}")
    for item in problems:
        print(item)
    print(f"Proposed Python compile: {'PASS' if not compile_errors else 'FAIL'}")
    for item in compile_errors:
        print(item)
    print(f"Security tests: {'PASS' if test_code == 0 else 'FAIL'}")
    print(test_output)
    print(f"Exact diff: {out / 'PHASE1_EXACT.diff'}")
    print("No live file was changed.")
    return 0 if not problems and not compile_errors and test_code == 0 else 2


def git_targets_safe(root: Path) -> tuple[bool, str]:
    """
    Protect only the files this reviewed bundle will touch.

    A globally clean repository is not required because FOXAI may contain known,
    unrelated Git anomalies or the extracted patch bundle itself. Safety comes
    from exact baseline hashes plus blocking staged/unstaged changes to the
    reviewed target files.
    """
    if not (root / ".git").exists():
        return True, "No .git directory detected; exact baseline hashes and timestamped backup remain active."

    manifest = load_manifest()
    reviewed_paths = list(manifest["baseline"].keys()) + list(manifest.get("expected_absent", []))

    try:
        unstaged = subprocess.run(
            ["git", "diff", "--name-status", "--", *reviewed_paths],
            cwd=str(root), text=True, capture_output=True,
        )
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-status", "--", *reviewed_paths],
            cwd=str(root), text=True, capture_output=True,
        )
        advisory = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=str(root), text=True, capture_output=True,
        )
    except FileNotFoundError:
        return False, "Git repository exists but git.exe was not found."

    for proc, label in ((unstaged, "unstaged target check"), (staged, "staged target check"), (advisory, "status advisory")):
        if proc.returncode != 0:
            return False, proc.stderr.strip() or f"git {label} failed."

    target_changes = []
    if unstaged.stdout.strip():
        target_changes.append("Unstaged changes to reviewed target files:\n" + unstaged.stdout.strip())
    if staged.stdout.strip():
        target_changes.append("Staged changes to reviewed target files:\n" + staged.stdout.strip())

    if target_changes:
        return False, "\n\n".join(target_changes)

    message = (
        "Reviewed target files have no staged or unstaged Git changes. "
        "Exact baseline hashes also match."
    )
    if advisory.stdout.strip():
        message += (
            "\nUnrelated Git entries are present and will be preserved, not modified:\n"
            + advisory.stdout.rstrip()
        )
    return True, message


def restore_backup(root: Path, backup: Path, created_files: list[str]) -> tuple[bool, list[str]]:
    errors = []
    manifest = load_manifest()
    for rel in manifest["baseline"]:
        src = backup / rel
        dst = root / rel
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        except Exception as exc:
            errors.append(f"restore {rel}: {exc}")
    for rel in created_files:
        try:
            p = root / rel
            if p.exists():
                p.unlink()
        except Exception as exc:
            errors.append(f"remove new {rel}: {exc}")
    errors.extend(validate_baseline(root))
    return not errors, errors


def apply(root: Path) -> int:
    phrase = input("Type exactly APPLY KAYOCK PHASE1 to continue: ").strip()
    if phrase != "APPLY KAYOCK PHASE1":
        print("Approval phrase did not match. No changes made.")
        return 3
    problems = validate_baseline(root)
    if problems:
        print("Baseline mismatch. Refusing to apply.")
        print("\n".join(problems))
        return 4
    compile_errors = compile_payload()
    test_code, test_output = run_tests()
    if compile_errors or test_code != 0:
        print("Proposed payload failed preflight. No changes made.")
        print("\n".join(compile_errors))
        print(test_output)
        return 5
    clean, git_message = git_targets_safe(root)
    print(git_message)
    if not clean:
        print("Refusing to apply because a reviewed target file has a Git change.")
        return 6

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = root / "Backups" / "SecurityMilestone" / f"Phase1_{stamp}"
    report_dir = root / "Reports" / "SecurityMilestone"
    backup.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    for rel in manifest["baseline"]:
        src = root / rel
        dst = backup / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    created_files = [rel for rel in TARGETS if not (root / rel).exists()]
    receipt = {
        "action": "kayock_phase1_apply",
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "state": "started",
        "backup": str(backup),
        "files": TARGETS,
        "before": {rel: sha(root / rel) for rel in manifest["baseline"]},
        "checks": [],
    }
    try:
        for rel in TARGETS:
            src = PAYLOAD / rel
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        for rel in TARGETS:
            p = root / rel
            if p.suffix == ".py":
                py_compile.compile(str(p), doraise=True)
        live_test = subprocess.run([sys.executable, str(TEST_FILE)], cwd=str(BUNDLE), text=True, capture_output=True)
        if live_test.returncode != 0:
            raise RuntimeError("Security tests failed after copy:\n" + live_test.stdout + live_test.stderr)
        payload_hashes = {rel: sha(PAYLOAD / rel) for rel in TARGETS}
        live_hashes = {rel: sha(root / rel) for rel in TARGETS}
        mismatches = [rel for rel in TARGETS if payload_hashes[rel] != live_hashes[rel]]
        if mismatches:
            raise RuntimeError("Post-copy hash mismatch: " + ", ".join(mismatches))
        receipt.update({
            "state": "verified",
            "verified": True,
            "after": live_hashes,
            "tests": live_test.stdout + live_test.stderr,
            "checks": [
                {"id": "backup_created", "ok": backup.exists()},
                {"id": "python_compile", "ok": True},
                {"id": "security_tests", "ok": True},
                {"id": "payload_hashes_match", "ok": True},
            ],
        })
        path = report_dir / f"Phase1_Apply_Receipt_{stamp}.json"
        path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"VERIFIED: Phase 1 applied. Receipt: {path}")
        return 0
    except Exception as exc:
        rollback_ok, rollback_errors = restore_backup(root, backup, created_files)
        receipt.update({
            "state": "rolled_back" if rollback_ok else "failed",
            "verified": False,
            "error": str(exc),
            "rollback_verified": rollback_ok,
            "rollback_errors": rollback_errors,
        })
        path = report_dir / f"Phase1_Failure_Receipt_{stamp}.json"
        path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"Apply failed: {exc}")
        print("Rollback " + ("verified." if rollback_ok else "FAILED verification."))
        print(f"Receipt: {path}")
        return 7


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["preview", "apply"])
    parser.add_argument("root", nargs="?")
    args = parser.parse_args()
    root = locate_root(args.root)
    return preview(root) if args.mode == "preview" else apply(root)


if __name__ == "__main__":
    raise SystemExit(main())
