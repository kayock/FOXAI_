from __future__ import annotations

from http.server import ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import sys
from threading import Thread
import urllib.error
import urllib.request

root = Path(sys.argv[1]).resolve()
web_path = Path(sys.argv[2]).resolve()
smoke_root = Path(sys.argv[3]).resolve()
sys.path.insert(0, str(root))

spec = importlib.util.spec_from_file_location("foxai_web_reset_method_smoke", web_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not import candidate WebUI.")
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)
web.web_mission_session = web.MissionSession(smoke_root, interface_name="Reset Method Smoke")

server = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f"http://127.0.0.1:{server.server_address[1]}/api/chat/reset"

try:
    get_request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(get_request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    assert payload.get("ok") is True, payload
    assert payload.get("session_receipt", {}).get("verified") is True, payload

    post_request = urllib.request.Request(
        url,
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(post_request, timeout=30)
        raise AssertionError("POST reset unexpectedly succeeded.")
    except urllib.error.HTTPError as error:
        assert error.code == 404, error.code

    print("reset_get_200=PASS")
    print("reset_post_404=PASS")
finally:
    server.shutdown()
    server.server_close()
