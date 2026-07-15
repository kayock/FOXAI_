from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASELINE_HASHES = {
    "core/foxai_web.py": "8b1ea52ac61a7d1dcf44a94cc64b6643ea0e74a6ca93ec734edb5f0f4d82e513",
    "core/server.py": "6d2b43616d6130469c057da070f8c4cf7ee3a965b563d1f704b0cc8ce6a49505",
    "core/security_containment.py": "9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24",
    "core/engineer_agent.py": "f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19",
    "ui/main_window.py": "2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3",
    "tests/test_boundary_watch.py": "b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382",
    "Config/FoxAI.ini": "677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41",
    "Engine/llama-server.exe": "936cfb77f011911f879a5af715013eb12141115547c1f731114d8e9c20ebd89e",
}
CANDIDATE_HASHES = {
    "core/foxai_web.py": "b94ac8e3b3a01b86cf34a509a64178e5efe047f38ac48e8ab5d08306ddf7ea48",
    "core/server.py": "9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07",
}
DIFF_HASHES = {
    "core/foxai_web.py": "565c21a8f3fd1589398586810bb2de7c0d4091228f93d25f7c89c07cf174b7a5",
    "core/server.py": "613d595f9495946b2775f6cadac31ee1e79a5a2ef7bd3b4a092acc299a3129ad",
}

SCRIPT_RE = re.compile(
    r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)

WEB_PRESERVED_MARKERS = (
    "performance.now()",
    "model_ms",
    "guard_model_action_claims(raw_ans)",
    "archive_receipt=web_mission_session.save()",
    "'chat_completion'",
    "initDepartmentNav()",
    "focusNavGroup(id)",
    "/api/security/incidents",
    "/api/security/trip_sentry_test",
)
SERVER_PRESERVED_MARKERS = (
    "def wait_until_ready(",
    "def stop(",
    "def release(",
    "def _runtime_lock(",
    "def _terminate_managed_process(",
    "def _probe_model_ids(",
)


class PreviewError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "sha256": None, "size_bytes": 0}
    if not path.is_file():
        return {"exists": True, "sha256": None, "not_file": True}
    return {
        "exists": True,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "core" / "foxai_web.py").is_file()
            and (candidate / "core" / "server.py").is_file()
        ):
            return candidate
    raise PreviewError(
        r"FOXAI root not found. Extract this complete folder directly inside Z:\FOXAI."
    )


def snapshot(root: Path) -> dict[str, Any]:
    result = {rel: file_state(root / rel) for rel in BASELINE_HASHES}
    security = root / "Logs" / "Security"
    if security.exists():
        for path in sorted(security.rglob("*")):
            if path.is_file():
                rel = str(path.relative_to(root)).replace("\\", "/")
                result[rel] = file_state(path)
    return result


def changed(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return [
        key
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]


def runtime_html_strings(source: str) -> list[str]:
    tree = ast.parse(source)
    values = []
    unresolved = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lower = node.value.lower()
            if any(token in lower for token in ("<script", "<body", "<html")):
                values.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            segment = ast.get_source_segment(source, node) or ""
            if any(token in segment.lower() for token in ("<script", "<body", "<html")):
                unresolved.append(getattr(node, "lineno", None))
    if unresolved:
        raise PreviewError("Runtime WebUI HTML contains unresolved Python f-strings.")
    if not values:
        raise PreviewError("No runtime WebUI HTML was found.")
    return values


def extract_scripts(source: str) -> list[str]:
    scripts = [
        match.group("body") or ""
        for html in runtime_html_strings(source)
        for match in SCRIPT_RE.finditer(html)
    ]
    if not scripts:
        raise PreviewError("No embedded JavaScript was found.")
    return scripts


def node_check(blocks: list[str], output: Path, label: str) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        raise PreviewError("Node.js was not found.")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for index, body in enumerate(blocks, start=1):
        target = output / f"embedded_script_{index:03d}.js"
        target.write_text(body, encoding="utf-8", newline="\n")
        completed = subprocess.run(
            [node, "--check", str(target)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        results.append({
            "file": target.name,
            "sha256": sha256(target),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "passed": completed.returncode == 0,
        })
    if any(item["passed"] is not True for item in results):
        raise PreviewError(f"{label} JavaScript failed node --check.")
    return {
        "label": label,
        "node": node,
        "javascript_blocks": len(results),
        "passed": True,
        "results": results,
    }


def expected_diff(baseline: str, candidate: str, relative: str) -> str:
    return "".join(difflib.unified_diff(
        baseline.splitlines(keepends=True),
        candidate.splitlines(keepends=True),
        fromfile=f"a/{relative}",
        tofile=f"b/{relative}",
    ))


def run_js_behavior_harness(
    candidate_scripts: list[str],
    output: Path,
) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        raise PreviewError("Node.js was not found.")
    script = "\n".join(candidate_scripts)
    registry = re.search(
        r"/\* MODEL_PROFILE_SELECTOR_PHASE2_REGISTRY_START \*/.*?"
        r"/\* MODEL_PROFILE_SELECTOR_PHASE2_REGISTRY_END \*/",
        script,
        re.DOTALL,
    )
    behavior = re.search(
        r"/\* MODEL_PROFILE_SELECTOR_PHASE2_BEHAVIOR_START \*/.*?"
        r"/\* MODEL_PROFILE_SELECTOR_PHASE2_BEHAVIOR_END \*/",
        script,
        re.DOTALL,
    )
    start_chat = re.search(
        r"async function startChat\(\)\{.*?\}\n",
        script,
        re.DOTALL,
    )
    if not registry or not behavior or not start_chat:
        raise PreviewError("Profile selector JavaScript markers were not found.")

    harness = r'''
let apiCalls=[];
async function api(url,opt){apiCalls.push({url,opt});return {ok:true,message:'started'}}
let log=[];
function logline(...args){log.push(args)}
function loadMemory(){}
function toast(){}
function esc(value){return String(value).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
const storage={};
global.localStorage={
 getItem:key=>Object.prototype.hasOwnProperty.call(storage,key)?storage[key]:null,
 setItem:(key,value)=>{storage[key]=String(value)}
};
const elements={
 model:{value:'',innerHTML:''},
 modelProfileGrid:{innerHTML:''},
 modelProfileStatus:{textContent:''}
};
function q(id){return elements[id]||null}
let activeProject=null,curLib='',missionData=null,modelCatalog=[],selectedProfileId='';
''' + registry.group(0) + "\n" + behavior.group(0) + "\n" + start_chat.group(0) + r'''
modelCatalog=[
 {name:'Qwen3.5-4B-Q4_K_M.gguf',path:'Z:\\FOXAI\\Models\\Chat\\Qwen3.5-4B-Q4_K_M.gguf'},
 {name:'Qwen3.5-9B-Q4_K_M.gguf',path:'Z:\\FOXAI\\Models\\Chat\\Qwen3.5-9B-Q4_K_M.gguf'},
 {name:'PsyLLM-8B-Q5_K_M.gguf',path:'Z:\\FOXAI\\Models\\Chat\\PsyLLM-8B-Q5_K_M.gguf'},
 {name:'Qwen3VL-8B-Instruct-Q4_K_M.gguf',path:'Z:\\FOXAI\\Models\\Chat\\Qwen3VL-8B-Instruct-Q4_K_M.gguf'},
 {name:'Qwen3VL-8B-Instruct-Q8_0.gguf',path:'Z:\\FOXAI\\Models\\Chat\\Qwen3VL-8B-Instruct-Q8_0.gguf'}
];
if(MODEL_PROFILES.length!==5)throw new Error('profile count');
selectModelProfile('fast_text');
if(apiCalls.length!==0)throw new Error('card selection called API');
if(elements.model.value!==modelCatalog[0].path)throw new Error('fast text path');
if(!elements.modelProfileStatus.textContent.includes('No engine action has occurred'))throw new Error('operator status');
await startChat();
if(apiCalls.length!==1)throw new Error('explicit start call count');
let payload=JSON.parse(apiCalls[0].opt.body);
if(payload.profile!=='fast_text')throw new Error('fast profile payload');
if(payload.model!==modelCatalog[0].path)throw new Error('fast model payload');
selectModelProfile('quality_vision');
if(apiCalls.length!==1)throw new Error('vision card selection called API');
await startChat();
payload=JSON.parse(apiCalls[1].opt.body);
if(payload.profile!=='quality_vision')throw new Error('vision profile payload');
if(!elements.modelProfileGrid.innerHTML.includes('Runtime launches with reasoning off and budget 0'))throw new Error('runtime note');
console.log('profile_count=PASS');
console.log('selection_no_api=PASS');
console.log('explicit_start_profile_payload=PASS');
console.log('silent_auto_switch_absent=PASS');
console.log('runtime_reasoning_note=PASS');
'''
    path = output / "MODEL_PROFILE_SELECTOR_RUNTIME_JS_HARNESS.mjs"
    path.write_text(harness, encoding="utf-8", newline="\n")
    completed = subprocess.run(
        [node, str(path)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    required = [
        "profile_count=PASS",
        "selection_no_api=PASS",
        "explicit_start_profile_payload=PASS",
        "silent_auto_switch_absent=PASS",
        "runtime_reasoning_note=PASS",
    ]
    passed = completed.returncode == 0 and all(
        item in completed.stdout for item in required
    )
    if not passed:
        raise PreviewError(
            "Profile JavaScript harness failed: "
            + completed.stdout
            + completed.stderr
        )
    return {
        "passed": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "required_markers": required,
        "sha256": sha256(path),
    }


def run_web_backend_registry_harness(
    candidate_source: str,
    output: Path,
) -> dict[str, Any]:
    tree = ast.parse(candidate_source)
    selected = []
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "WEB_MODEL_PROFILE_RUNTIME"
                for target in node.targets
            )
        ):
            selected.append(node)
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "web_model_profile_runtime"
        ):
            selected.append(node)
    if len(selected) != 2:
        raise PreviewError("Backend profile registry/helper extraction failed.")

    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"Path": Path}
    exec(compile(module, "web_profile_registry_harness", "exec"), namespace)
    resolver = namespace["web_model_profile_runtime"]

    fast = resolver(
        r"Z:\FOXAI\Models\Chat\Qwen3.5-4B-Q4_K_M.gguf",
        "fast_text",
    )
    vision = resolver(
        r"Z:\FOXAI\Models\Chat\Qwen3VL-8B-Instruct-Q8_0.gguf",
        "quality_vision",
    )
    mismatch = resolver(
        r"Z:\FOXAI\Models\Chat\Qwen3.5-9B-Q4_K_M.gguf",
        "fast_text",
    )
    raw = resolver(r"Z:\FOXAI\Models\Chat\Other.gguf", "")
    unknown = resolver(r"Z:\FOXAI\Models\Chat\Other.gguf", "unknown")

    checks = {
        "fast_text_reasoning_off": (
            fast.get("ok")
            and fast.get("reasoning_mode") == "off"
            and fast.get("reasoning_budget") == 0
            and fast.get("require_verified_settings") is True
        ),
        "quality_vision_current": (
            vision.get("ok")
            and vision.get("reasoning_mode") == "current"
            and vision.get("reasoning_budget") is None
            and vision.get("require_verified_settings") is True
        ),
        "profile_model_mismatch_fails": mismatch.get("ok") is False,
        "raw_fallback_preserved": (
            raw.get("ok")
            and raw.get("profile_id") == ""
            and raw.get("require_verified_settings") is False
        ),
        "unknown_profile_fails": unknown.get("ok") is False,
    }
    if not all(checks.values()):
        raise PreviewError("Backend profile registry harness failed.")

    path = output / "WEB_BACKEND_PROFILE_REGISTRY_HARNESS.json"
    path.write_text(
        json.dumps(
            {
                "passed": True,
                "checks": checks,
                "fast": fast,
                "vision": vision,
                "mismatch": mismatch,
                "raw": raw,
                "unknown": unknown,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "passed": True,
        "checks": checks,
        "sha256": sha256(path),
    }


def load_candidate_server(source: str):
    temp = tempfile.TemporaryDirectory()
    base = Path(temp.name)
    engine = base / "Engine" / "llama-server.exe"
    engine.parent.mkdir(parents=True)
    engine.write_bytes(b"preview-fake-engine")

    core_module = types.ModuleType("core")
    paths_module = types.ModuleType("core.paths")
    paths_module.ENGINE = engine
    module_name = "foxai_candidate_server_preview"
    module = types.ModuleType(module_name)
    module.__file__ = str(base / "candidate_server.py")

    previous = {
        "core": sys.modules.get("core"),
        "core.paths": sys.modules.get("core.paths"),
        module_name: sys.modules.get(module_name),
    }
    sys.modules["core"] = core_module
    sys.modules["core.paths"] = paths_module
    sys.modules[module_name] = module
    try:
        exec(compile(source, module.__file__, "exec"), module.__dict__)
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value

    module._preview_temp = temp
    return module


def run_server_runtime_harness(
    candidate_source: str,
    output: Path,
) -> dict[str, Any]:
    module = load_candidate_server(candidate_source)
    temp_root = Path(module._preview_temp.name)
    model = temp_root / "Qwen3.5-4B-Q4_K_M.gguf"
    model.write_bytes(b"fake-model")

    server = module.LlamaServer(
        interface_name="PreviewHarness",
        state_file=temp_root / "state.json",
    )
    current = server._target(
        model, "127.0.0.1", "8080", "8192", "12"
    )
    reasoning_off = server._target(
        model,
        "127.0.0.1",
        "8080",
        "8192",
        "12",
        "off",
        0,
        True,
    )

    invalid_checks = {}
    for key, mode, budget in (
        ("invalid_mode", "unsupported", None),
        ("nonzero_reasoning_budget", "off", 1),
        ("current_with_budget", "current", 0),
    ):
        try:
            server._target(
                model,
                "127.0.0.1",
                "8080",
                "8192",
                "12",
                mode,
                budget,
                True,
            )
            invalid_checks[key] = False
        except ValueError:
            invalid_checks[key] = True

    captured = []
    class DummyProcess:
        pid = 4242
        def poll(self):
            return None

    original_popen = module.subprocess.Popen
    def fake_popen(command, cwd=None, creationflags=0):
        captured.append(
            {
                "command": list(command),
                "cwd": str(cwd),
                "creationflags": creationflags,
            }
        )
        return DummyProcess()

    module.subprocess.Popen = fake_popen
    try:
        server._launch_process(current)
        server._launch_process(reasoning_off)
    finally:
        module.subprocess.Popen = original_popen

    current_command = captured[0]["command"]
    off_command = captured[1]["command"]
    command_checks = {
        "current_has_no_reasoning_override": (
            "--reasoning" not in current_command
            and "--reasoning-budget" not in current_command
        ),
        "off_has_reasoning_flags": (
            "--reasoning" in off_command
            and off_command[off_command.index("--reasoning") + 1] == "off"
            and "--reasoning-budget" in off_command
            and off_command[
                off_command.index("--reasoning-budget") + 1
            ] == "0"
        ),
    }

    exact_state = {
        "model_path": reasoning_off["model_path"],
        "model_name": reasoning_off["model_name"],
        "context": "8192",
        "threads": "12",
        "reasoning_mode": "off",
        "reasoning_budget": 0,
    }
    wrong_reasoning = dict(
        exact_state,
        reasoning_mode="current",
        reasoning_budget=None,
    )
    wrong_context = dict(exact_state, context="4096")
    compatibility_checks = {
        "exact_profile_matches": server._same_model(
            exact_state, reasoning_off
        ),
        "wrong_reasoning_conflicts": not server._same_model(
            wrong_reasoning, reasoning_off
        ),
        "wrong_context_conflicts": not server._same_model(
            wrong_context, reasoning_off
        ),
        "raw_fallback_keeps_model_only_compatibility": server._same_model(
            wrong_reasoning, current
        ),
    }

    external_server = module.LlamaServer(
        interface_name="ExternalProfileHarness",
        state_file=temp_root / "external_profile_state.json",
    )
    external_server._probe_model_ids = lambda host, port: [model.name]
    external_server._model_matches_ids = (
        lambda model_path, model_ids: True
    )
    exact_external_result = external_server._attach_to_healthy_runtime(
        None,
        reasoning_off,
    )

    raw_server = module.LlamaServer(
        interface_name="ExternalRawHarness",
        state_file=temp_root / "external_raw_state.json",
    )
    raw_server._probe_model_ids = lambda host, port: [model.name]
    raw_server._model_matches_ids = lambda model_path, model_ids: True
    raw_external_result = raw_server._attach_to_healthy_runtime(
        None,
        current,
    )
    external_checks = {
        "profile_external_runtime_fails_closed": (
            exact_external_result.ok is False
            and exact_external_result.action == "conflict"
            and exact_external_result.details.get("settings_verified")
            is False
        ),
        "raw_external_runtime_compatibility_preserved": (
            raw_external_result.ok is True
            and raw_external_result.action == "attached"
        ),
    }

    launch_server = module.LlamaServer(
        interface_name="StateHarness",
        state_file=temp_root / "launch_state.json",
    )
    launch_server._health_ok = lambda host, port: False
    launch_server._port_open = lambda host, port: False
    launch_server._pid_exists = lambda pid: False
    original_launch = launch_server._launch_process
    launch_server._launch_process = lambda target: DummyProcess()
    try:
        launched = launch_server.ensure_running(
            model,
            host="127.0.0.1",
            port="8080",
            context="8192",
            threads="12",
            reasoning_mode="off",
            reasoning_budget=0,
            require_verified_settings=True,
        )
    finally:
        launch_server._launch_process = original_launch
    launch_state = json.loads(
        (temp_root / "launch_state.json").read_text(encoding="utf-8")
    )
    state_checks = {
        "launch_result_verified_settings": (
            launched.ok
            and launched.action == "launched"
            and launched.details.get("settings_verified") is True
        ),
        "state_tracks_reasoning_mode": (
            launch_state.get("reasoning_mode") == "off"
        ),
        "state_tracks_reasoning_budget": (
            launch_state.get("reasoning_budget") == 0
        ),
        "state_tracks_context_threads": (
            launch_state.get("context") == "8192"
            and launch_state.get("threads") == "12"
        ),
    }

    checks = {
        **invalid_checks,
        **command_checks,
        **compatibility_checks,
        **external_checks,
        **state_checks,
    }
    if not all(checks.values()):
        raise PreviewError("Shared runtime reasoning harness failed.")

    result_path = output / "SERVER_RUNTIME_REASONING_HARNESS.json"
    result_path.write_text(
        json.dumps(
            {
                "passed": True,
                "checks": checks,
                "current_target": current,
                "reasoning_off_target": reasoning_off,
                "current_command": current_command,
                "reasoning_off_command": off_command,
                "profile_external_result": exact_external_result.to_dict(),
                "raw_external_result": raw_external_result.to_dict(),
                "launch_result": launched.to_dict(),
                "launch_state": launch_state,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    module._preview_temp.cleanup()
    return {
        "passed": True,
        "checks": checks,
        "sha256": sha256(result_path),
    }


def run_boundary_watch(root: Path) -> dict[str, Any]:
    test_path = root / "tests" / "test_boundary_watch.py"
    runner = (
        "import runpy,sys;"
        f"sys.path.insert(0,{str(root)!r});"
        f"runpy.run_path({str(test_path)!r},run_name='__main__')"
    )
    completed = subprocess.run(
        [sys.executable, "-c", runner],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "project_root_inserted_into_child_sys_path": True,
        "passed": completed.returncode == 0,
    }


def main() -> int:
    package_dir = Path(__file__).resolve().parent
    payload_dir = package_dir / "payload"
    root = find_root(package_dir)
    created = datetime.now(timezone.utc)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    output = (
        package_dir
        / f"MODEL_PROFILE_SELECTOR_RUNTIME_PHASE3_PREVIEW_OUTPUT_{stamp}"
    )
    output.mkdir(parents=True, exist_ok=False)

    receipt: dict[str, Any] = {
        "action": "model_profile_selector_runtime_phase3_combined_exact_preview",
        "created": created.isoformat(),
        "root": str(root),
        "state": "running",
        "verified": False,
        "candidate_included": True,
        "apply_capability_present": False,
        "live_files_modified": False,
        "configuration_modified": False,
        "default_model_changed": False,
        "engine_started": False,
        "model_loaded": False,
        "proposed_files": ["core/foxai_web.py", "core/server.py"],
        "delete_operations": [],
        "failure": None,
        "checks": [],
    }

    before = snapshot(root)

    try:
        baseline_checks = []
        for relative, expected in BASELINE_HASHES.items():
            path = root / relative
            actual = sha256(path) if path.is_file() else None
            baseline_checks.append({
                "path": relative,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "ok": actual == expected,
            })
        if not all(item["ok"] for item in baseline_checks):
            raise PreviewError("A locked live baseline changed.")

        live_web = root / "core" / "foxai_web.py"
        live_server = root / "core" / "server.py"
        web_candidate = payload_dir / "candidate" / "core" / "foxai_web.py"
        server_candidate = payload_dir / "candidate" / "core" / "server.py"
        web_diff = payload_dir / "diffs" / "core_foxai_web.py.diff"
        server_diff = payload_dir / "diffs" / "core_server.py.diff"

        payload_checks = []
        for relative, path in (
            ("core/foxai_web.py", web_candidate),
            ("core/server.py", server_candidate),
        ):
            actual = sha256(path)
            payload_checks.append({
                "path": relative,
                "expected_sha256": CANDIDATE_HASHES[relative],
                "actual_sha256": actual,
                "ok": actual == CANDIDATE_HASHES[relative],
            })
        for relative, path in (
            ("core/foxai_web.py", web_diff),
            ("core/server.py", server_diff),
        ):
            actual = sha256(path)
            payload_checks.append({
                "path": relative + ".diff",
                "expected_sha256": DIFF_HASHES[relative],
                "actual_sha256": actual,
                "ok": actual == DIFF_HASHES[relative],
            })
        if not all(item["ok"] for item in payload_checks):
            raise PreviewError("Candidate payload or exact diff hash changed.")

        live_web_source = live_web.read_text(encoding="utf-8")
        live_server_source = live_server.read_text(encoding="utf-8")
        candidate_web_source = web_candidate.read_text(encoding="utf-8")
        candidate_server_source = server_candidate.read_text(encoding="utf-8")

        if expected_diff(
            live_web_source,
            candidate_web_source,
            "core/foxai_web.py",
        ) != web_diff.read_text(encoding="utf-8"):
            raise PreviewError("WebUI diff does not reproduce the candidate.")
        if expected_diff(
            live_server_source,
            candidate_server_source,
            "core/server.py",
        ) != server_diff.read_text(encoding="utf-8"):
            raise PreviewError("Server diff does not reproduce the candidate.")

        compile(live_web_source, str(live_web), "exec")
        compile(live_server_source, str(live_server), "exec")
        compile(candidate_web_source, "candidate_core_foxai_web.py", "exec")
        compile(candidate_server_source, "candidate_core_server.py", "exec")

        baseline_js = node_check(
            extract_scripts(live_web_source),
            output / "baseline_javascript",
            "baseline",
        )
        candidate_scripts = extract_scripts(candidate_web_source)
        candidate_js = node_check(
            candidate_scripts,
            output / "candidate_javascript",
            "candidate",
        )
        js_harness = run_js_behavior_harness(candidate_scripts, output)
        web_backend_harness = run_web_backend_registry_harness(
            candidate_web_source,
            output,
        )
        server_harness = run_server_runtime_harness(
            candidate_server_source,
            output,
        )

        preserved = []
        for marker in WEB_PRESERVED_MARKERS:
            before_count = live_web_source.count(marker)
            after_count = candidate_web_source.count(marker)
            preserved.append({
                "file": "core/foxai_web.py",
                "marker": marker,
                "before": before_count,
                "after": after_count,
                "ok": before_count > 0 and before_count == after_count,
            })
        for marker in SERVER_PRESERVED_MARKERS:
            before_count = live_server_source.count(marker)
            after_count = candidate_server_source.count(marker)
            preserved.append({
                "file": "core/server.py",
                "marker": marker,
                "before": before_count,
                "after": after_count,
                "ok": before_count > 0 and before_count == after_count,
            })
        if not all(item["ok"] for item in preserved):
            raise PreviewError("A locked behavior marker changed or disappeared.")

        boundary = run_boundary_watch(root)
        if not boundary["passed"]:
            raise PreviewError(
                "Boundary Watch tests failed: "
                + boundary["stdout"]
                + boundary["stderr"]
            )

        baseline_output = output / "baseline" / "core"
        candidate_output = output / "candidate" / "core"
        diff_output = output / "diffs"
        baseline_output.mkdir(parents=True)
        candidate_output.mkdir(parents=True)
        diff_output.mkdir(parents=True)

        shutil.copy2(live_web, baseline_output / "foxai_web.py")
        shutil.copy2(live_server, baseline_output / "server.py")
        shutil.copy2(web_candidate, candidate_output / "foxai_web.py")
        shutil.copy2(server_candidate, candidate_output / "server.py")
        shutil.copy2(web_diff, diff_output / "core_foxai_web.py.diff")
        shutil.copy2(server_diff, diff_output / "core_server.py.diff")
        shutil.copy2(
            package_dir / "PATCH_CONTRACT.json",
            output / "PATCH_CONTRACT.json",
        )

        validation = {
            "baseline_hashes": {
                "core/foxai_web.py": sha256(live_web),
                "core/server.py": sha256(live_server),
            },
            "candidate_hashes": CANDIDATE_HASHES,
            "diff_hashes": DIFF_HASHES,
            "proposed_files": ["core/foxai_web.py", "core/server.py"],
            "delete_operations": [],
            "profile_cards": 5,
            "raw_gguf_fallback_preserved": True,
            "browser_arbitrary_engine_flags_allowed": False,
            "profile_model_mismatch_fails_closed": True,
            "unverified_external_profile_runtime_fails_closed": True,
            "selection_only_until_explicit_start": True,
            "baseline_javascript": baseline_js,
            "candidate_javascript": candidate_js,
            "javascript_behavior_harness": js_harness,
            "web_backend_registry_harness": web_backend_harness,
            "server_runtime_harness": server_harness,
            "boundary_watch": boundary,
            "preserved_markers": preserved,
        }
        (output / "MODEL_PROFILE_SELECTOR_RUNTIME_PHASE3_VALIDATION.json").write_text(
            json.dumps(validation, indent=2),
            encoding="utf-8",
        )

        report = [
            "# FOXAI Model Profile Selector + Verified Runtime — Phase 3 Exact Preview",
            "",
            "- State: **combined_exact_preview_ready**",
            "- Verified: **True**",
            "- Live files modified: **False**",
            "- Candidate included: **True**",
            "- Apply capability present: **False**",
            "- Proposed files: **core/foxai_web.py, core/server.py**",
            f"- WebUI candidate SHA-256: `{CANDIDATE_HASHES['core/foxai_web.py']}`",
            f"- Server candidate SHA-256: `{CANDIDATE_HASHES['core/server.py']}`",
            "",
            "## Combined behavior",
            "",
            "The five profile cards remain pending-selection-only. Clicking a card",
            "does not call an API or affect the running engine. Starting remains an",
            "explicit operator button action.",
            "",
            "A backend-owned allowlist validates each profile/model pairing and",
            "selects its runtime settings. Browser-supplied arbitrary engine flags",
            "are not accepted.",
            "",
            "### Profile settings",
            "",
            "- ⚡ Fast Text: reasoning off, budget 0",
            "- ⚖️ Balanced Text: reasoning off, budget 0",
            "- 🎭 Creative Text: reasoning off, budget 0",
            "- 👁️ Fast Vision: current engine reasoning behavior",
            "- 🔎 Quality Vision: current engine reasoning behavior",
            "",
            "The raw-GGUF fallback remains available.",
            "",
            "Profile launches track model, context, threads, reasoning mode, and",
            "reasoning budget. Different or unverifiable profile settings conflict",
            "fail-closed instead of silently attaching.",
            "",
            "## Verification passed",
            "",
            "- Exact live, candidate, and diff hashes",
            "- Exact diff-to-candidate reconstruction",
            "- Baseline and candidate Python compilation",
            "- Complete embedded JavaScript node checks",
            "- Selection/no-API and explicit-start payload harness",
            "- Backend profile allowlist harness",
            "- Shared runtime reasoning/state/compatibility harness",
            "- Boundary Watch tests",
            "- Locked Chat Timing, archive, receipt, navigation, accordion, and Sentry markers",
            "- Live source, configuration, and security-log immutability",
            "",
            "No apply mechanism is present.",
        ]
        (output / "MODEL_PROFILE_SELECTOR_RUNTIME_PHASE3_PREVIEW_REPORT.md").write_text(
            "\n".join(report) + "\n",
            encoding="utf-8",
        )

        after = snapshot(root)
        live_changes = changed(before, after)
        if live_changes:
            raise PreviewError(
                "Protected live state changed during preview: "
                + repr(live_changes)
            )

        receipt.update({
            "state": "combined_exact_preview_ready",
            "verified": True,
            "candidate_hashes": CANDIDATE_HASHES,
            "diff_hashes": DIFF_HASHES,
            "checks": [
                {
                    "id": "locked_live_baselines_match",
                    "ok": True,
                    "detail": baseline_checks,
                },
                {
                    "id": "candidate_and_diff_payload_hashes_match",
                    "ok": True,
                    "detail": payload_checks,
                },
                {
                    "id": "exact_diffs_reconstruct_candidates",
                    "ok": True,
                },
                {
                    "id": "baseline_and_candidate_python_compile",
                    "ok": True,
                },
                {
                    "id": "complete_embedded_javascript_node_check",
                    "ok": True,
                    "detail": {
                        "baseline": baseline_js,
                        "candidate": candidate_js,
                    },
                },
                {
                    "id": "profile_selection_and_explicit_start_payload",
                    "ok": True,
                    "detail": js_harness,
                },
                {
                    "id": "backend_owned_profile_registry",
                    "ok": True,
                    "detail": web_backend_harness,
                },
                {
                    "id": "shared_runtime_reasoning_identity",
                    "ok": True,
                    "detail": server_harness,
                },
                {
                    "id": "boundary_watch_tests",
                    "ok": True,
                    "detail": boundary,
                },
                {
                    "id": "locked_behavior_markers_preserved",
                    "ok": True,
                    "detail": preserved,
                },
                {
                    "id": "two_file_scope_no_deletes",
                    "ok": True,
                    "detail": ["core/foxai_web.py", "core/server.py"],
                },
                {
                    "id": "live_sources_configs_and_security_logs_unchanged",
                    "ok": True,
                    "detail": live_changes,
                },
            ],
            "live_snapshot_before": before,
            "live_snapshot_after": after,
        })

    except Exception as exc:
        after = snapshot(root)
        live_changes = changed(before, after)
        receipt.update({
            "state": "stopped_fail_closed",
            "verified": not live_changes,
            "live_files_modified": bool(live_changes),
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
            "live_snapshot_before": before,
            "live_snapshot_after": after,
        })

    (output / "MODEL_PROFILE_SELECTOR_RUNTIME_PHASE3_PREVIEW_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )

    print()
    print("FOXAI MODEL PROFILE SELECTOR + VERIFIED RUNTIME")
    print("PHASE 3 COMBINED EXACT PREVIEW")
    print()
    print("Output:", output)
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Candidate included: True")
    print("Apply capability present: False")
    print("Live files modified:", receipt["live_files_modified"])
    print("Proposed files:", receipt["proposed_files"])
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    print()
    input("Press Enter to close...")
    return 0 if receipt["state"] == "combined_exact_preview_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
