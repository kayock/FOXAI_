from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

PACKAGE_NAME = "CREATOR_TYPE_1_2"
PLAN_NAME = "PLAN.json"
EXPECTED_BASELINE_SHA256 = "229d45ac0b7b10182bd4b6a45faf7e09deb8bd56e2da8ed002b8e502d762e086"
EXPECTED_PAYLOAD_SHA256 = "d46254c1d3d3e8315dd8ddcf20aac7c05bc8be492dd71113b38860593f3d72ee"

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def stop(message):
    print()
    print("BLOCKED — PLAN NOT CREATED")
    print(message)
    print()
    input("Press Enter to close...")
    raise SystemExit(1)

package_dir = Path(__file__).resolve().parent
if package_dir.name.casefold() != PACKAGE_NAME.casefold():
    stop("This package must be extracted directly to a folder named " + PACKAGE_NAME + ". Current folder: " + str(package_dir))

project_root = package_dir.parent
live_file = project_root / "core" / "foxai_web.py"
payload_file = package_dir / "payload" / "core" / "foxai_web.py"
portable_python = project_root / "Runtime" / "Desktop" / "python" / "python.exe"

for label, path in (("Current live source", live_file), ("Prepared payload", payload_file), ("Portable Python", portable_python)):
    if not path.is_file():
        stop(label + " was not found: " + str(path))

live_bytes = live_file.read_bytes()
payload_bytes = payload_file.read_bytes()
live_sha = sha256_bytes(live_bytes)
payload_sha = sha256_bytes(payload_bytes)

if live_sha != EXPECTED_BASELINE_SHA256:
    stop("The live source is not the exact installed Guided Creator V1.1 baseline.\nExpected: " + EXPECTED_BASELINE_SHA256 + "\nActual:   " + live_sha + "\nNothing was changed. A fresh comparison is required.")
if payload_sha != EXPECTED_PAYLOAD_SHA256:
    stop("The prepared payload hash does not match the verified package.\nExpected: " + EXPECTED_PAYLOAD_SHA256 + "\nActual:   " + payload_sha + "\nNothing was changed.")

try:
    payload_text = payload_bytes.decode("utf-8")
    compile(payload_text, str(payload_file), "exec")
except Exception as exc:
    stop("Prepared payload failed Python compilation: " + type(exc).__name__ + ": " + str(exc))

mission_id = input("Paste the staged Engineering Workshop Mission ID: ").strip()
if not re.fullmatch(r"ENG-[A-Za-z0-9_-]{8,80}", mission_id):
    stop("That does not look like a valid Engineering Workshop Mission ID.\nExpected a value beginning with ENG-, copied from the staged mission receipt.")

target_text = str(live_file)

validation_hash_python = f'''from pathlib import Path
import hashlib
p=Path({target_text!r})
b=p.read_bytes()
actual=hashlib.sha256(b).hexdigest()
expected={EXPECTED_PAYLOAD_SHA256!r}
assert actual==expected, f"installed hash mismatch: {{actual}}"
s=b.decode("utf-8")
compile(s,str(p),"exec")
required=(
    "FOXAI_CREATOR_TYPE_1_2_HTML_START",
    "FOXAI_CREATOR_TYPE_1_2_JS_START",
    "FOXAI_CREATOR_TYPE_1_2_TITLE_START",
    "FOXAI_CREATOR_TYPE_1_2_BACKEND_START",
    "FOXAI_CREATOR_TYPE_1_2_STORAGE_START",
    "FOLDERS['kayock_writer_short_story_drafts']",
    "id=poemWritingType",
    'value=short_story',
    "storyLengthMirror",
    "shortStoryFolderButton",
    "content_type:",
)
missing=[item for item in required if item not in s]
assert not missing, "missing Creator Type 1.2 markers: "+", ".join(missing)
print("CREATOR_TYPE_1_2_HASH_PYTHON_AND_FEATURE_MARKERS_OK")'''

validation_javascript = f'''from pathlib import Path
import ast, os, re, shutil, subprocess, sys, tempfile
p=Path({target_text!r})
source=p.read_text(encoding="utf-8")
tree=ast.parse(source)
html_value=None
for item in tree.body:
    if isinstance(item,(ast.Assign,ast.AnnAssign)):
        targets=item.targets if isinstance(item,ast.Assign) else [item.target]
        if any(isinstance(t,ast.Name) and t.id=="HTML" for t in targets):
            html_value=ast.literal_eval(item.value)
            break
assert isinstance(html_value,str), "HTML constant not found"
blocks=re.findall(r"<script(?:\\s[^>]*)?>(.*?)</script>",html_value,flags=re.I|re.S)
assert blocks, "No embedded JavaScript blocks found"
node=shutil.which("node") or shutil.which("node.exe")
if not node:
    candidate=Path(os.environ.get("ProgramFiles",r"C:\\Program Files"))/"nodejs"/"node.exe"
    if candidate.is_file():
        node=str(candidate)
assert node, "Node.js was not found for embedded JavaScript verification"
temp_path=None
try:
    with tempfile.NamedTemporaryFile("w",suffix=".js",encoding="utf-8",delete=False) as handle:
        handle.write("\\n;\\n".join(blocks))
        temp_path=handle.name
    result=subprocess.run([str(node),"--check",temp_path],capture_output=True,text=True,shell=False)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr,file=sys.stderr)
    assert result.returncode==0, f"Node syntax check failed with return code {{result.returncode}}"
finally:
    if temp_path:
        try:
            Path(temp_path).unlink()
        except FileNotFoundError:
            pass
print("CREATOR_TYPE_1_2_EMBEDDED_JAVASCRIPT_OK")'''

validation_preservation = f'''from pathlib import Path
p=Path({target_text!r})
s=p.read_text(encoding="utf-8")
required=(
    "def kayock_writer_poetry_create",
    "def kayock_writer_poetry_polish",
    "def kayock_writer_poetry_revise_selection",
    "def kayock_writer_poetry_archive",
    "KAYOCK_WRITER_CALM_GUIDED_V2_BROWSER_START",
    "KAYOCKS_STUDY_INTEGRATION_V1_HELPERS_START",
    "ERIC_POET_NARRATOR_PROFILE_V1_START",
    "FOLDERS['kayock_writer_poetry_drafts']",
    "FOLDERS['kayock_writer_poetry_recordings']",
    "FOLDERS['kayock_writer_poetry_legacy']",
    "FOLDERS['kayock_writer_short_story_drafts']",
)
missing=[item for item in required if item not in s]
assert not missing, "protected feature anchors missing: "+", ".join(missing)
assert "writing_type='poem'" in s
assert "writing_type=='short_story'" in s
print("CREATOR_TYPE_1_2_PROTECTED_FEATURES_AND_POEM_REGRESSION_ANCHORS_OK")'''

plan = {
    "schema": "foxai.engineering.plan.v1",
    "mission_id": mission_id,
    "title": "Creator Type 1.2 — Poem and Short Story",
    "project_root": str(project_root),
    "changes": [{
        "action": "write_file",
        "path": "core/foxai_web.py",
        "must_exist": True,
        "expected_before_sha256": EXPECTED_BASELINE_SHA256,
        "content": payload_text,
    }],
    "validations": [
        {"name": "Verify exact payload hash, Python syntax, and Poem/Short Story feature markers", "argv": [str(portable_python), "-I", "-B", "-S", "-c", validation_hash_python], "cwd": ".", "timeout_seconds": 300},
        {"name": "Verify embedded interface JavaScript syntax with Node", "argv": [str(portable_python), "-I", "-B", "-S", "-c", validation_javascript], "cwd": ".", "timeout_seconds": 300},
        {"name": "Verify existing poetry, Writer, Study, voice, and archive anchors remain present", "argv": [str(portable_python), "-I", "-B", "-S", "-c", validation_preservation], "cwd": ".", "timeout_seconds": 300},
    ],
    "constraints": {
        "changed_paths": ["core/foxai_web.py"],
        "writing_type_default": "poem",
        "short_story_save_folder": "Projects/KayockWriter/ShortStories/Drafts",
        "existing_poem_markdown_changed": False,
        "existing_short_story_markdown_changed": False,
        "poetry_archive_content_changed": False,
        "original_polished_separation_changed": False,
        "poem_polisher_removed": False,
        "selected_lines_workshop_removed": False,
        "rhyme_rhythm_coach_removed": False,
        "voice_profiles_removed": False,
        "kayock_writer_v2_removed": False,
        "bibliotheca_changed": False,
        "repair_bay_changed": False,
        "launchers_changed": False,
        "runtime_changed": False,
        "comfyui_changed": False,
        "red_canvas_changed": False,
        "models_changed": False,
        "network_used": False,
        "packages_installed": False,
        "moves": False,
        "renames": False,
        "deletions": False,
    },
}

plan_path = package_dir / PLAN_NAME
plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
plan_sha = sha256_bytes(canonical)
(package_dir / "PLAN_SHA256.txt").write_text(plan_sha + "\n", encoding="utf-8")

print()
print("ENGINEERING WORKSHOP PLAN CREATED")
print("Mission ID: " + mission_id)
print("Plan: " + str(plan_path))
print("Plan SHA-256: " + plan_sha)
print("Live paths proposed: 1")
print("  core\\foxai_web.py")
print()
print("Nothing has been applied.")
print()
print("Paste this exact command into FOXAI Mission Console:")
print()
print('/engineer workshop preview "' + str(plan_path) + '"')
print()
input("Press Enter to close...")
