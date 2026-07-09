from pathlib import Path
import json
import datetime
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "Foundry" / "Reports"
RELEASES = ROOT / "Foundry" / "Releases"

REQUIRED_FOR_FINAL = [
    "manifest.yaml",
    "Start_KayocktheOS.bat",
    "System/API/core_api.py",
    "System/Services/service_bus.py",
    "System/Registry/build_registry.py",
    "AI/scan_ai_assets.py",
    "Foundry/release_check.py",
    "Foundry/package_release.py",
    "Foundry/build_portable_rc.py",
    "Shell/KayockBrowser/index.html",
    "Shell/KayockBrowser/renderer.js",
    "Docs",
    "Forge/Decisions",
]

def exists(rel):
    return (ROOT / rel).exists()

def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace") if Path(path).exists() else ""

def write_text(path, content):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")

def update_manifest_final():
    path = ROOT / "manifest.yaml"
    text = read_text(path)
    if not text:
        return False
    text = re.sub(r"version: .*", "version: 1.0.0", text, count=1)
    text = re.sub(r"codename: .*", "codename: Portable Foundation", text, count=1)
    if "portable_foundation: enabled" not in text:
        text += "\n  portable_foundation: enabled\n" if "features:" in text else "\nfeatures:\n  portable_foundation: enabled\n"
    write_text(path, text)
    return True

def run_optional(rel):
    path = ROOT / rel
    if not path.exists():
        return {"script": rel, "ok": False, "message": "missing"}
    try:
        result = subprocess.run([sys.executable, str(path)], cwd=ROOT, capture_output=True, text=True, timeout=300)
        return {
            "script": rel,
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:]
        }
    except Exception as exc:
        return {"script": rel, "ok": False, "message": str(exc)}

def finalize_release():
    missing = [rel for rel in REQUIRED_FOR_FINAL if not exists(rel)]
    preflight_ok = not missing

    report = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "version": "1.0.0",
        "codename": "Portable Foundation",
        "preflight_ok": preflight_ok,
        "missing": missing,
        "actions": []
    }

    if preflight_ok:
        report["actions"].append({"action": "manifest_finalized", "ok": update_manifest_final()})
        report["actions"].append(run_optional("System/Registry/build_registry.py"))
        report["actions"].append(run_optional("AI/scan_ai_assets.py"))
        report["actions"].append(run_optional("Foundry/release_check.py"))
        report["actions"].append(run_optional("Foundry/package_release.py"))
        final_ready = all(a.get("ok", False) for a in report["actions"] if "script" in a) and report["actions"][0].get("ok")
    else:
        final_ready = False

    report["final_ready"] = final_ready

    REPORTS.mkdir(parents=True, exist_ok=True)
    RELEASES.mkdir(parents=True, exist_ok=True)

    write_text(REPORTS / "final_release_report.json", json.dumps(report, indent=2))

    lines = [
        "# KayocktheOS v1.0.0 Final Release Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Final ready: {'YES' if final_ready else 'NO'}",
        "",
        "## Preflight",
        ""
    ]

    if missing:
        lines.append("Missing required items:")
        lines += [f"- `{m}`" for m in missing]
    else:
        lines.append("All required foundation files are present.")

    lines += ["", "## Actions", ""]
    for action in report["actions"]:
        label = action.get("script") or action.get("action")
        symbol = "✅" if action.get("ok") else "❌"
        lines.append(f"- {symbol} `{label}`")

    write_text(REPORTS / "FINAL_RELEASE_REPORT.md", "\n".join(lines) + "\n")

    release_notes = """# KayocktheOS v1.0.0 - Portable Foundation

## What this release is

KayocktheOS v1.0.0 establishes the portable foundation:

- Core launcher
- Local Core API
- Browser Shell integration
- Bridge Desktop
- Dynamic module registry
- Living system scanner
- AI asset scanner
- Service Bus
- Foundry release checker
- Git baseline helpers
- Release packager
- Portable release candidate builder

## What this release is not yet

This is not the final AI Academy.
This is not the finished Repair Bay.
This is not the finished Creative Studio.

It is the foundation those systems will plug into.
"""
    write_text(RELEASES / "KayocktheOS_v1.0.0_FINAL_RELEASE_NOTES.md", release_notes)

    print(json.dumps({"final_ready": final_ready, "missing": missing}, indent=2))
    return report

if __name__ == "__main__":
    finalize_release()
