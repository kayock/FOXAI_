from __future__ import annotations
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
plan = json.loads((PACKAGE / "PLAN.json").read_text(encoding="utf-8"))

assert plan["schema"] == "foxai.engineering.plan.v1"
assert plan["mission_id"] == "ENG-20260723-031118-BF49AE"
assert len(plan["changes"]) == 3
assert len(plan["validations"]) == 6

replace = plan["changes"][0]
assert replace["action"] == "replace_text"
assert replace["path"] == "System/AgentFoxTechnicalCore/self_knowledge_chat_adapter_v1.py"
assert isinstance(replace.get("old"), str) and replace["old"]
assert isinstance(replace.get("new"), str)
assert "old_text" not in replace
assert "new_text" not in replace
assert replace["expected_before_sha256"] == "1563a0f3275eb7516006c8f608ef595f693a85fcb9cba60f2610ca053b25f275"

old = replace["old"]
new = replace["new"]
assert old.startswith('    if normalized_message.lstrip().startswith("/")')
assert new.startswith('    if normalized_message.lstrip().startswith("/")')
assert "# FOXAI_CURRENT_STATE_CLASSIFICATION_V1B3C_BEGIN" in new
assert "authorization=None" in new
assert "providers={}" in new

candidates = [
    PACKAGE.parent / "AGENT_FOX_V1B3A" / "current_state_request_broker_v1.py",
    Path("/mnt/data/AGENT_FOX_V1B3A/current_state_request_broker_v1.py"),
]
broker = next((path for path in candidates if path.is_file()), None)
assert broker is not None, candidates

prefix = (
    'from pathlib import Path\n'
    'SCHEMA_PREFIX="foxai.agent_fox.self_knowledge_chat_adapter"\n'
    'ADAPTER_ID="shared_self_knowledge_chat_adapter_v1"\n'
    'ADAPTER_VERSION="test"\n'
    'SUPPORTED_SURFACES=("webui","desktop")\n'
    'def _pass_through_result(surface,request_id,diagnostic):\n'
    ' return {"schema":"test","adapter_id":ADAPTER_ID,"adapter_version":ADAPTER_VERSION,'
    '"surface":surface,"request_id":request_id,"handled":False,"status":"pass_through",'
    '"model_bypass":False,"ordinary_chat_pass_through":True,"answer_text":"",'
    '"answer_packet":None,"diagnostic":diagnostic}\n'
    'def _normalize_selectors(selectors): return dict(selectors or {})\n'
    'def route_message(message,surface,request_id=None,selectors=None):\n'
    '    normalized_surface=str(surface).strip().lower()\n'
    "    normalized_message=str(message or '').strip()\n"
    "    slash_rid=str(request_id or 'TEST')\n"
)

route_block = new.replace(
    "    try:\n        normalized_selectors = _normalize_selectors(selectors)",
    "    normalized_selectors = _normalize_selectors(selectors)",
)
source = prefix + route_block + '\n    return _pass_through_result(normalized_surface, slash_rid, "OLD-ROUTE")\n'

tmp = Path(tempfile.mkdtemp(prefix="v1b3c_r1_package_test_"))
(tmp / "current_state_request_broker_v1.py").write_bytes(broker.read_bytes())
module_path = tmp / "adapter.py"
module_path.write_text(source, encoding="utf-8")
compile(source, str(module_path), "exec")

spec = importlib.util.spec_from_file_location("v1b3c_r1_package_adapter", module_path)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

for message, status in (
    ("How much memory is available right now?", "authorization_required"),
    ("What is my battery health right now?", "unsupported_live_category"),
):
    result = module.route_message(message, "webui", "PKG", {})
    assert result["status"] == status
    assert result["answer_packet"]["provider_invoked"] is False
    assert result["answer_packet"]["live_inspection_performed"] is False

assert module.route_message("/engineer workshop status", "webui", "PKG", {})["status"] == "pass_through"
assert module.route_message("Which Python currently runs Workshop Main?", "webui", "PKG", {})["status"] == "pass_through"

print("AGENT_FOX_V1B3C_R1_PACKAGE_AND_REPLACE_TEXT_SCHEMA_OK")
