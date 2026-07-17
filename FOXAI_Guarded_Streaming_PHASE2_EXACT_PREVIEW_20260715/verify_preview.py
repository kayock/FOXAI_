from __future__ import annotations
import ast, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

BASELINE = "b94ac8e3b3a01b86cf34a509a64178e5efe047f38ac48e8ab5d08306ddf7ea48"
CANDIDATE = "e4d5811f14ae3ffb0b3f8b59369bee5c0a1218d19459f2decc875589540d04fb"
DIFF = "33da716cd9e6065a8d4b8eaec21253e15a75d4b1c7f39cf4a5a45aebf4662123"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def find_root(start):
    for candidate in (start, *start.parents):
        if (candidate / "core/foxai_web.py").is_file():
            return candidate
    raise RuntimeError(r"FOXAI root not found. Extract this folder directly inside Z:\FOXAI.")

package = Path(__file__).resolve().parent
root = find_root(package)
live = root / "core/foxai_web.py"
candidate = package / "candidate/core/foxai_web.py"
diff = package / "diffs/core_foxai_web.py.diff"

result = {
    "state": "stopped_fail_closed",
    "verified": False,
    "live_files_modified": False,
    "apply_capability_present": False,
    "checks": {},
    "failure": None,
}
before = sha(live)
try:
    result["checks"]["live_baseline"] = before == BASELINE
    result["checks"]["candidate_hash"] = sha(candidate) == CANDIDATE
    result["checks"]["diff_hash"] = sha(diff) == DIFF
    compile(live.read_text(encoding="utf-8"), str(live), "exec")
    compile(candidate.read_text(encoding="utf-8"), str(candidate), "exec")
    result["checks"]["python_compile"] = True
    scripts = re.findall(
        r"<script[^>]*>(.*?)</script\s*>",
        candidate.read_text(encoding="utf-8"),
        flags=re.I|re.S,
    )
    node = shutil.which("node")
    if not node or not scripts:
        raise RuntimeError("Node.js or embedded JavaScript was not found.")
    js_dir = package / "verification/live_node_check"
    js_dir.mkdir(parents=True, exist_ok=True)
    for index, body in enumerate(scripts, 1):
        target = js_dir / f"embedded_{index:03d}.js"
        target.write_text(body, encoding="utf-8")
        completed = subprocess.run(
            [node, "--check", str(target)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if completed.returncode:
            raise RuntimeError(completed.stderr)
    result["checks"]["javascript_node_check"] = True
    if not all(result["checks"].values()):
        raise RuntimeError("One or more exact-preview checks failed.")
    result["state"] = "exact_preview_verified"
    result["verified"] = True
except Exception as exc:
    result["failure"] = f"{type(exc).__name__}: {exc}"
finally:
    after = sha(live)
    result["live_files_modified"] = before != after
    if result["live_files_modified"]:
        result["verified"] = False
        result["state"] = "stopped_fail_closed"
    output = package / "LIVE_VERIFY_RECEIPT.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print()
    print("State:", result["state"])
    print("Verified:", result["verified"])
    print("Live files modified:", result["live_files_modified"])
    print("Apply capability present: False")
    if result["failure"]:
        print("Failure:", result["failure"])
    print("Receipt:", output)
    input("Press Enter to close...")
sys.exit(0 if result["verified"] else 1)
