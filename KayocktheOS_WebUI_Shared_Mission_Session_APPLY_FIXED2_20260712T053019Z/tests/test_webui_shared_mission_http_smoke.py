from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import sys
from threading import Thread
import urllib.request


def request_get_json(url: str) -> dict:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def request_post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


root = Path(sys.argv[1]).resolve()
live_web = Path(sys.argv[2]).resolve()
smoke_root = Path(sys.argv[3]).resolve()
sys.path.insert(0, str(root))

class FakeChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        messages = payload.get("messages") or []
        user_text = ""
        for item in reversed(messages):
            if item.get("role") == "user":
                user_text = str(item.get("content") or "")
                break
        if "claim guard smoke" in user_text.lower():
            answer = "I successfully deleted the smoke-test file."
        else:
            answer = "A software engineer designs, tests, and improves software systems."
        body = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": answer}}]}
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


fake_server = ThreadingHTTPServer(("127.0.0.1", 0), FakeChatHandler)
fake_thread = Thread(target=fake_server.serve_forever, daemon=True)
fake_thread.start()

spec = importlib.util.spec_from_file_location("foxai_web_apply_smoke", live_web)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load installed foxai_web.py")
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)

web.active_project = None
web.prof = "fox"
web.chat_model = None
web.chat_process = None
web.messages = [{"role": "system", "content": web.professor_system_prompt(web.prof)}]
web._web_engineer = None
web.web_mission_session = web.MissionSession(
    smoke_root,
    interface_name="WebUI Apply Smoke",
)
fake_base = f"http://127.0.0.1:{fake_server.server_address[1]}"
web.CHAT_HEALTH = fake_base + "/health"
web.CHAT_API = fake_base + "/v1/chat/completions"

web_server = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
web_thread = Thread(target=web_server.serve_forever, daemon=True)
web_thread.start()
base = f"http://127.0.0.1:{web_server.server_address[1]}"

try:
    reset = request_get_json(base + "/api/chat/reset")
    assert reset.get("ok") is True, reset
    assert reset.get("session_receipt", {}).get("verified") is True, reset
    print("chat_reset_get_route=PASS")

    ordinary = request_post_json(
        base + "/api/chat/send",
        {"message": "Please explain what an engineer does in one sentence."},
    )
    assert ordinary.get("ok") is True, ordinary
    assert ordinary.get("route") == "agent_fox", ordinary
    assert ordinary.get("speaker") == "AGENT FOX", ordinary
    assert ordinary.get("route_receipt", {}).get("verified") is True, ordinary
    assert ordinary.get("completion_receipt", {}).get("verified") is True, ordinary
    assert ordinary.get("archive_receipt", {}).get("verified") is True, ordinary
    assert ordinary.get("claim_guard", {}).get("flagged") is False, ordinary

    claim = request_post_json(
        base + "/api/chat/send",
        {"message": "Run the claim guard smoke test."},
    )
    assert claim.get("ok") is True, claim
    assert claim.get("route") == "agent_fox", claim
    assert claim.get("claim_guard", {}).get("flagged") is True, claim
    assert "UNVERIFIED ACTION CLAIM" in claim.get("answer", ""), claim
    assert claim.get("archive_receipt", {}).get("verified") is True, claim

    engineer = request_post_json(
        base + "/api/chat/send",
        {"message": "/engineer smart search for COMFY_MAIN"},
    )
    assert engineer.get("ok") is True, engineer
    assert engineer.get("route") == "engineer", engineer
    assert engineer.get("speaker") == "ENGINEER", engineer
    assert engineer.get("route_receipt", {}).get("verified") is True, engineer
    assert engineer.get("completion_receipt", {}).get("verified") is True, engineer
    assert engineer.get("archive_receipt", {}).get("verified") is True, engineer
    answer = engineer.get("answer", "")
    assert "Query: COMFY_MAIN" in answer, answer[:2400]
    assert "core/foxai_web.py" in answer.replace("\\", "/"), answer[:2400]

    denied = request_post_json(
        base + "/api/chat/send",
        {"message": "/engineer log lesson for FOXAI: Smoke Test - no write"},
    )
    assert denied.get("ok") is False, denied
    assert denied.get("speaker") == "SYSTEM", denied
    assert denied.get("route_receipt", {}).get("state") == "denied", denied
    assert denied.get("archive_receipt", {}).get("verified") is True, denied
    assert "read-only" in denied.get("answer", "").lower(), denied

    receipts = [
        ordinary["archive_receipt"],
        claim["archive_receipt"],
        engineer["archive_receipt"],
        denied["archive_receipt"],
    ]
    archive_paths = {
        item.get("details", {}).get("archive_path")
        for item in receipts
    }
    assert len(archive_paths) == 1, archive_paths
    archive_path = Path(next(iter(archive_paths))).resolve()
    expected_root = (smoke_root / "Mission Archive" / "Chats").resolve()
    archive_path.relative_to(expected_root)
    assert archive_path.is_file(), archive_path
    transcript = archive_path.read_text(encoding="utf-8")
    for marker in [
        "### ERIC",
        "### AGENT FOX",
        "### ENGINEER",
        "### SYSTEM",
        "Please explain what an engineer does",
        "/engineer smart search for COMFY_MAIN",
        "Query: COMFY_MAIN",
        "UNVERIFIED ACTION CLAIM",
        "WebUI Engineer is read-only",
    ]:
        assert marker in transcript, marker

    print("webui_http_smoke=PASS")
    print("ordinary_model_contract_route=PASS")
    print("claim_guard_http_route=PASS")
    print("explicit_engineer_http_route=PASS")
    print("webui_engineer_write_denial=PASS")
    print("stable_archive_path=PASS")
    print("archive_readback=PASS")
    print("smoke_archive=" + str(archive_path))
finally:
    web_server.shutdown()
    web_server.server_close()
    fake_server.shutdown()
    fake_server.server_close()
