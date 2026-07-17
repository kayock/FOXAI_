from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import ast
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
PLAN = json.loads(
    (PACKAGE / "EXACT_PREVIEW_PLAN.json").read_text(encoding="utf-8")
)
REPORT_ROOT = ROOT / "Reports" / "ModelStatusClarityPreview"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_unittest(pattern: str, expected_count: int) -> dict:
    runner = (
        "import sys,unittest;"
        "sys.dont_write_bytecode=True;"
        "sys.path.insert(0,sys.argv[1]);"
        "suite=unittest.defaultTestLoader.discover("
        "start_dir=sys.argv[2],pattern=sys.argv[3]);"
        "result=unittest.TextTestRunner(verbosity=2).run(suite);"
        "sys.exit(0 if result.wasSuccessful() else 1)"
    )
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [
            sys.executable,
            "-s",
            "-c",
            runner,
            str(ROOT),
            str(ROOT / "tests"),
            pattern,
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    combined = (process.stdout or "") + (process.stderr or "")
    passed = (
        process.returncode == 0
        and f"Ran {expected_count} tests" in combined
        and "\nOK" in combined
    )
    if not passed:
        raise RuntimeError(
            f"{pattern} failed: " + combined[-5000:]
        )
    return {
        "passed": True,
        "tests": expected_count,
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "bytecode_writes_disabled": True,
    }


def write_report(receipt: dict, path: Path) -> None:
    lines = [
        "# FOXAI Model Status Clarity Phase 2C4 — Exact Preview",
        "",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        "- Apply capability: **False**",
        "- Live files modified: **False**",
        "- Model files modified: **False**",
        "- Registry modified: **False**",
        "- Model server action: **None**",
        "- Network access: **False**",
        "- Deleted files: **None**",
        "",
        "## Exact proposed live change",
        "",
        "- Modify `core/foxai_web.py`.",
        "- Add no live files.",
        "- Delete no live files.",
        "",
        "## Display behavior",
        "",
        "A running host-PC model will display:",
        "",
        "```text",
        "Engine: RUNNING",
        "Model source: HOST PC",
        "Network use: NONE",
        "```",
        "",
        "A running USB model will display:",
        "",
        "```text",
        "Engine: RUNNING",
        "Model source: USB",
        "Network use: NONE",
        "```",
        "",
        "A stopped engine will display:",
        "",
        "```text",
        "Engine: STOPPED",
        "Model source: NONE",
        "Network use: NONE",
        "```",
        "",
        "## Preserved behavior",
        "",
    ]

    for item in PLAN["preserved"]:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Verification",
        "",
        f"- Exact replacement transformation: "
        f"**{receipt['checks'].get('exact_transformation', {}).get('passed')}**",
        f"- Status clarity tests: "
        f"**{receipt['checks'].get('status_clarity_tests', {}).get('tests', 0)}/10**",
        f"- Model-source tests: "
        f"**{receipt['checks'].get('model_source_tests', {}).get('tests', 0)}/10**",
        f"- Boundary Watch: "
        f"**{receipt['checks'].get('boundary_watch', {}).get('tests', 0)}/5**",
        f"- Embedded JavaScript blocks: "
        f"**{receipt['checks'].get('javascript', {}).get('blocks', 0)} passed**",
    ]

    if receipt.get("failure"):
        lines += [
            "",
            "## Failure",
            "",
            f"- `{receipt['failure']['type']}: "
            f"{receipt['failure']['message']}`",
        ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("MSC2C4_%Y%m%dT%H%M%SZ")
    report_dir = REPORT_ROOT / stamp
    report_dir.mkdir(parents=True, exist_ok=False)

    receipt = {
        "action": "foxai_model_status_clarity_phase2c4_exact_preview",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "root": str(ROOT),
        "apply_capability_present": False,
        "live_files_modified": False,
        "model_files_modified": False,
        "registry_modified": False,
        "automatic_model_launch": False,
        "model_server_action": False,
        "network_access": False,
        "delete_operations": [],
        "checks": {},
        "failure": None,
    }

    try:
        baseline_files = []
        for relative, expected in PLAN["locked_baselines"].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            baseline_files.append({
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            })

        if not all(item["ok"] for item in baseline_files):
            raise RuntimeError(
                "One or more protected live baselines changed."
            )

        receipt["checks"]["live_baselines"] = {
            "passed": True,
            "files": baseline_files,
        }

        live_path = ROOT / "core/foxai_web.py"
        candidate_path = PACKAGE / "candidate/core/foxai_web.py"
        live_text = live_path.read_text(encoding="utf-8")
        transformed = live_text
        replacement_results = []

        for item in PLAN["exact_replacements"]:
            count = transformed.count(item["old"])
            replacement_results.append({
                "id": item["id"],
                "occurrences": count,
                "expected": 1,
            })
            if count != 1:
                raise RuntimeError(
                    f"Replacement {item['id']} matched {count} times."
                )
            transformed = transformed.replace(
                item["old"],
                item["new"],
                1,
            )

        candidate_text = candidate_path.read_text(encoding="utf-8")
        if transformed != candidate_text:
            raise RuntimeError(
                "Candidate is not the exact approved transformation "
                "of the live WebUI."
            )

        receipt["checks"]["exact_transformation"] = {
            "passed": True,
            "replacements": replacement_results,
            "candidate_sha256": sha256(candidate_path),
        }

        ast.parse(candidate_text, filename=str(candidate_path))
        compile(candidate_text, str(candidate_path), "exec")
        receipt["checks"]["python_compile"] = {"passed": True}

        runner = (
            "import sys,unittest;"
            "sys.dont_write_bytecode=True;"
            "sys.path.insert(0,sys.argv[1]);"
            "suite=unittest.defaultTestLoader.discover("
            "start_dir=sys.argv[2],pattern='test_status_clarity_preview.py');"
            "result=unittest.TextTestRunner(verbosity=2).run(suite);"
            "sys.exit(0 if result.wasSuccessful() else 1)"
        )
        env = os.environ.copy()
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        status_tests = subprocess.run(
            [
                sys.executable,
                "-s",
                "-c",
                runner,
                str(PACKAGE),
                str(PACKAGE / "tests"),
            ],
            cwd=str(PACKAGE),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )

        status_output = (
            (status_tests.stdout or "")
            + (status_tests.stderr or "")
        )

        if (
            status_tests.returncode != 0
            or "Ran 10 tests" not in status_output
            or "\nOK" not in status_output
        ):
            raise RuntimeError(
                "Status clarity tests failed: "
                + status_output[-5000:]
            )

        receipt["checks"]["status_clarity_tests"] = {
            "passed": True,
            "tests": 10,
            "stdout": status_tests.stdout,
            "stderr": status_tests.stderr,
        }

        receipt["checks"]["model_source_tests"] = run_unittest(
            "test_model_sources.py",
            10,
        )
        receipt["checks"]["boundary_watch"] = run_unittest(
            "test_boundary_watch.py",
            5,
        )

        node = shutil.which("node") or shutil.which("node.exe")
        if not node:
            raise RuntimeError(
                "Node.js was not found for embedded JavaScript checking."
            )

        scripts = re.findall(
            r"<script[^>]*>(.*?)</script>",
            candidate_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not scripts:
            raise RuntimeError(
                "No embedded JavaScript blocks were found."
            )

        js_dir = report_dir / "javascript"
        js_dir.mkdir()
        js_results = []

        for index, script in enumerate(scripts, start=1):
            script_path = js_dir / f"embedded_script_{index:03d}.js"
            script_path.write_text(script, encoding="utf-8")
            process = subprocess.run(
                [node, "--check", str(script_path)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            js_results.append({
                "path": str(script_path),
                "returncode": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
            })

        if not all(item["returncode"] == 0 for item in js_results):
            raise RuntimeError(
                "One or more embedded JavaScript blocks failed node --check."
            )

        receipt["checks"]["javascript"] = {
            "passed": True,
            "blocks": len(js_results),
            "results": js_results,
        }

        after_files = []
        for relative, expected in PLAN["locked_baselines"].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            after_files.append({
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            })

        if not all(item["ok"] for item in after_files):
            raise RuntimeError(
                "A protected live baseline changed during preview."
            )

        receipt["checks"]["live_baselines_after"] = {
            "passed": True,
            "files": after_files,
        }

        receipt["state"] = "exact_preview_verified"
        receipt["verified"] = True
    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    receipt_path = report_dir / "receipt.json"
    report_path = report_dir / "report.md"

    receipt_path.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )
    write_report(receipt, report_path)

    results_zip = report_dir / "MSC2C4_RESULTS.zip"
    with zipfile.ZipFile(
        results_zip,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.write(receipt_path, arcname="receipt.json")
        archive.write(report_path, arcname="report.md")

    print("=" * 72)
    print("FOXAI MODEL STATUS CLARITY PHASE 2C4")
    print("EXACT PREVIEW")
    print("=" * 72)
    print(f"State: {receipt['state']}")
    print(f"Verified: {receipt['verified']}")
    print(f"Report: {report_dir}")
    print(f"Upload: {results_zip}")
    print("Apply capability present: False")
    print("Live files modified: False")
    print("Model files modified: False")
    print("Registry modified: False")
    print("Model server action: None")
    print("Network access: False")

    if receipt["failure"]:
        print(f"Failure: {receipt['failure']['message']}")

    return 0 if receipt["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
