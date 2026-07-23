from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MISSION_ID = "ENG-20260722-225500-4D0517"
ROOT = Path(r"Z:\FOXAI")
TECH = ROOT / "System" / "AgentFoxTechnicalCore"
OUT = ROOT / "System" / "EngineeringWorkshop" / "missions" / f"{MISSION_ID}_V1B2E_R4_PARTIAL_APPLY_RECONCILIATION"

EXPECTED = {
    ROOT / "core" / "director.py": {
        "size": 7003,
        "sha256": "1397b0ce5d1e21b9fc49eabef76ffa64467d716061b12d1a2c670167597d7d55",
    },
    ROOT / "ui" / "main_window.py": {
        "size": 99139,
        "sha256": "c232ce7f14a9fc7e898c13afcdfc7e56be1826b51d18d3c71979ac3f0b2acdc9",
    },
}

PROTECTED = {
    TECH / "self_knowledge_chat_adapter_v1.py": "1563a0f3275eb7516006c8f608ef595f693a85fcb9cba60f2610ca053b25f275",
    TECH / "resource_evidence_provider_v1.py": "41a1663cd30af8a3800c8082d351f8d0338e75cd1df39d3c801a39cc3075f680",
    TECH / "webui_self_knowledge_integration_v1.py": "451f8b274dad5fae8c72df8fc6a51b0e360cf99a6a4174c000c66f3af9dd8b69",
    TECH / "desktop_self_knowledge_integration_v1.py": "1b3aa2e3ab0409112ca602209285e27df1ab6b0216f5d9a9480766e4509078c4",
    TECH / "SHARED_RESOURCE_PROVIDER_INTEGRATION_CONTRACT_V1.json": "60b6b5394849a5cd0a192be137deb01be39d2c3f8fd3e4fa75421b94ab5a9ab1",
    TECH / "SHARED_RESOURCE_PROVIDER_INTEGRATION_FIXTURES_V1.json": "f2fab44d7926a4f46706e369eb853b790137a29ff4b6df689deeab44e9327b13",
    ROOT / "core" / "foxai_web.py": "d7bf0a2042d55ef7f0a5869556015e42c7427e7ff88636b28e1795f3adf7b952",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    checks: list[dict] = []
    files: list[dict] = []

    for path, expected in EXPECTED.items():
        data = path.read_bytes()
        actual = {"path": str(path), "size": len(data), "sha256": sha256(data)}
        files.append(actual)
        ok = actual["size"] == expected["size"] and actual["sha256"] == expected["sha256"]
        checks.append({"id": f"intended_hash_{path.name}", "ok": ok, "actual": actual, "expected": expected})
        compile(data.decode("utf-8"), str(path), "exec")

    director_path = ROOT / "core" / "director.py"
    director_text = director_path.read_text(encoding="utf-8")
    director_lines = director_text.splitlines()
    checks.append({
        "id": "bare_evidence_trigger_removed",
        "ok": '    "evidence",' not in director_lines,
    })
    checks.append({
        "id": "ranked_evidence_preserved",
        "ok": '    "ranked evidence",' in director_lines,
    })

    sys.path.insert(0, str(ROOT))
    director = load_module("foxai_v1b2e_r4_director", director_path)
    ordinary = (
        "What evidence supports your answer about FOXAI resources?",
        "What are the limitations of this evidence?",
        "What does the shared resource evidence provider do?",
    )
    strong = (
        "/engineer workshop status",
        "Please review your code for technical debt.",
        "Show ranked evidence for this architecture review.",
        "Investigate this Python error traceback.",
    )
    checks.append({
        "id": "ordinary_evidence_routes_chat",
        "ok": all(director.classify(text, operator_approved=True, audit=False)["agent"] == "chat" for text in ordinary),
    })
    checks.append({
        "id": "strong_engineering_routes_preserved",
        "ok": all(director.classify(text, operator_approved=True, audit=False)["agent"] == "engineer" for text in strong),
    })

    desktop_path = ROOT / "ui" / "main_window.py"
    desktop_text = desktop_path.read_text(encoding="utf-8")
    desktop_lines = desktop_text.splitlines()
    guard = '            if not answer.lstrip().startswith("[Model:"):'
    nested = '                answer = f"[Model: {model_used}]\\n\\n{answer}"'
    unguarded = '            answer = f"[Model: {model_used}]\\n\\n{answer}"'
    checks.extend([
        {"id": "model_label_guard_exactly_once", "ok": desktop_lines.count(guard) == 1},
        {"id": "guarded_model_label_assignment_exactly_once", "ok": desktop_lines.count(nested) == 1},
        {"id": "unguarded_model_label_assignment_absent", "ok": desktop_lines.count(unguarded) == 0},
        {
            "id": "desktop_self_knowledge_before_director",
            "ok": desktop_text.index("route_desktop_message(text)") < desktop_text.index("self.format_director_analysis"),
        },
    ])

    for path, expected_hash in PROTECTED.items():
        data = path.read_bytes()
        checks.append({
            "id": f"protected_{path.name}",
            "ok": sha256(data) == expected_hash,
            "actual_sha256": sha256(data),
            "expected_sha256": expected_hash,
        })
        if path.suffix == ".py":
            compile(data.decode("utf-8"), str(path), "exec")

    desktop_helper = load_module("foxai_v1b2e_r4_desktop_helper", TECH / "desktop_self_knowledge_integration_v1.py")
    web_helper = load_module("foxai_v1b2e_r4_web_helper", TECH / "webui_self_knowledge_integration_v1.py")
    historical = "How much RAM did FOXAI use in the loaded capture?"
    current = "How much memory is my computer using right now?"
    dh = desktop_helper.route_desktop_message(historical)
    dc = desktop_helper.route_desktop_message(current)
    wh = web_helper.route_http_request(json.dumps({"message": historical}).encode("utf-8"), "/api/chat/send")
    wc = web_helper.route_http_request(json.dumps({"message": current}).encode("utf-8"), "/api/chat/send")
    checks.extend([
        {"id": "desktop_historical_intercept", "ok": dh.get("intercepted") is True and dh.get("model_bypass") is True},
        {"id": "desktop_current_live_pass_through", "ok": dc.get("intercepted") is False and dc.get("ordinary_chat_pass_through") is True},
        {"id": "webui_historical_intercept", "ok": wh.get("intercepted") is True},
        {"id": "webui_current_live_pass_through", "ok": wc.get("intercepted") is False},
    ])

    failed = [row for row in checks if not row.get("ok")]
    status = "reconciled_verified" if not failed else "reconciliation_failed"
    generated_at = datetime.now(timezone.utc).isoformat()
    detail = {
        "schema": "foxai.agent_fox.technical_core.v1b2e.partial_apply_reconciliation.v1",
        "mission_id": MISSION_ID,
        "status": status,
        "generated_at": generated_at,
        "finding": "Both intended V1B-2E cleanup edits are present despite the earlier blocked Workshop receipt.",
        "source_files_modified_by_this_check": 0,
        "model_calls": 0,
        "models_loaded": 0,
        "guis_launched": 0,
        "live_scans": 0,
        "network_used": False,
        "k_access": False,
        "verified_files": files,
        "checks": checks,
        "failed_check_ids": [row["id"] for row in failed],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    detail_path = OUT / "V1B2E_R4_PARTIAL_APPLY_RECONCILIATION.json"
    detail_bytes = (json.dumps(detail, indent=2, sort_keys=True) + "\n").encode("utf-8")
    detail_path.write_bytes(detail_bytes)
    receipt = {
        "mission_id": MISSION_ID,
        "status": status,
        "reconciliation_evidence": str(detail_path),
        "reconciliation_evidence_sha256": sha256(detail_bytes),
        "checks_total": len(checks),
        "checks_failed": len(failed),
        "source_files_modified": 0,
        "model_calls": 0,
        "live_scans": 0,
        "k_access": False,
    }
    receipt_path = OUT / "V1B2E_R4_RECONCILIATION_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
