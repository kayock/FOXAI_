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

change = plan["changes"][0]
assert change["action"] == "replace_text"
assert isinstance(change.get("old"), str) and change["old"]
assert isinstance(change.get("new"), str) and change["new"]
assert "old_text" not in change and "new_text" not in change
assert change["expected_before_sha256"] == "1563a0f3275eb7516006c8f608ef595f693a85fcb9cba60f2610ca053b25f275"

new = change["new"]
assert "# FOXAI_CURRENT_STATE_CLASSIFICATION_V1B3C_BEGIN" in new
assert "authorization=None" in new
assert "providers={}" in new
assert "_v1b3c_result = _pass_through_result(" in new
assert "ADAPTER_ID" not in new
assert "ADAPTER_VERSION" not in new
assert "SCHEMA_PREFIX" not in new

broker_candidates = (
    PACKAGE.parent / "AGENT_FOX_V1B3A" / "current_state_request_broker_v1.py",
    Path("/mnt/data/AGENT_FOX_V1B3A/current_state_request_broker_v1.py"),
)
broker = next((p for p in broker_candidates if p.is_file()), None)
assert broker is not None, broker_candidates

prefix = (
    'from pathlib import Path\n'
    'SUPPORTED_SURFACES=("webui","desktop")\n'
    'def _pass_through_result(surface,request_id,diagnostic):\n'
    ' return {"schema":"canonical.test.result.v1",'
    '"adapter_id":"canonical_test_adapter",'
    '"adapter_version":"canonical-test-version",'
    '"surface":surface,"request_id":request_id,"handled":False,'
    '"status":"pass_through","model_bypass":False,'
    '"ordinary_chat_pass_through":True,"answer_text":"",'
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

tmp = Path(tempfile.mkdtemp(prefix="v1b3c_r2_pkg_"))
(tmp / "current_state_request_broker_v1.py").write_bytes(broker.read_bytes())
module_path = tmp / "adapter.py"
module_path.write_text(source, encoding="utf-8")
compile(source, str(module_path), "exec")

spec = importlib.util.spec_from_file_location("v1b3c_r2_adapter", module_path)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

for surface in ("webui", "desktop"):
    result = module.route_message("How much memory is available right now?", surface, "R2", {})
    assert result["handled"] is True
    assert result["status"] == "authorization_required"
    assert result["schema"] == "canonical.test.result.v1"
    assert result["adapter_id"] == "canonical_test_adapter"
    assert result["adapter_version"] == "canonical-test-version"
    assert result["answer_packet"]["provider_invoked"] is False
    assert result["answer_packet"]["live_inspection_performed"] is False

    unsupported = module.route_message("What is my battery health right now?", surface, "R2", {})
    assert unsupported["status"] == "unsupported_live_category"

    slash = module.route_message("/engineer workshop status", surface, "R2", {})
    assert slash["status"] == "pass_through"
    assert slash["ordinary_chat_pass_through"] is True

    architecture = module.route_message("Which Python currently runs Workshop Main?", surface, "R2", {})
    assert architecture["status"] == "pass_through"

print("AGENT_FOX_V1B3C_R2_PACKAGE_HARNESS_OK")
