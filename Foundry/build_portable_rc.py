from pathlib import Path
import subprocess
import datetime
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "Foundry" / "Reports"
REPORTS.mkdir(parents=True, exist_ok=True)

def run_python_script(rel):
    path = ROOT / rel
    if not path.exists():
        return {"script": rel, "ok": False, "message": "missing"}
    try:
        result = subprocess.run([sys.executable, str(path)], cwd=ROOT, capture_output=True, text=True, timeout=300)
        return {
            "script": rel,
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:]
        }
    except Exception as exc:
        return {"script": rel, "ok": False, "message": str(exc)}

def build_release_candidate():
    steps = [
        "System/Registry/build_registry.py",
        "AI/scan_ai_assets.py",
        "Foundry/release_check.py",
        "Foundry/package_release.py",
    ]

    results = []
    for step in steps:
        results.append(run_python_script(step))

    ok = all(r.get("ok") for r in results)
    report = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "name": "KayocktheOS Portable Release Candidate",
        "ship_ready": ok,
        "steps": results,
    }

    (REPORTS / "portable_rc_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# KayocktheOS Portable Release Candidate Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Ship ready: {'YES' if ok else 'NO'}",
        "",
        "## Steps",
        ""
    ]
    for r in results:
        symbol = "✅" if r.get("ok") else "❌"
        lines.append(f"- {symbol} `{r.get('script')}`")
    (REPORTS / "PORTABLE_RC_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"ship_ready": ok, "steps": len(results)}, indent=2))
    return report

if __name__ == "__main__":
    build_release_candidate()
