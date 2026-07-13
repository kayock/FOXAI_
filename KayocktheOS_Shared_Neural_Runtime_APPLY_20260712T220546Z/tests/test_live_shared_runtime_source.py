from __future__ import annotations
import ast
import os
from pathlib import Path
import unittest

ROOT = Path(os.environ["FOXAI_LIVE_ROOT"]).resolve()
SERVER = (ROOT / "core" / "server.py").read_text(encoding="utf-8")
WEB = (ROOT / "core" / "foxai_web.py").read_text(encoding="utf-8")
UI = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")

class SharedRuntimeSourceTests(unittest.TestCase):
    def test_candidates_parse(self):
        ast.parse(SERVER)
        ast.parse(WEB)
        ast.parse(UI)

    def test_server_has_shared_state_and_lock(self):
        self.assertIn("shared_llama_runtime.json", SERVER)
        self.assertIn("shared_llama_runtime.lock", SERVER)
        self.assertIn("def _runtime_lock(", SERVER)

    def test_server_tracks_interface_clients(self):
        self.assertIn("def _register_client(", SERVER)
        self.assertIn("def _unregister_client(", SERVER)
        self.assertIn("remaining_clients", SERVER)

    def test_server_checks_health_port_and_model_identity(self):
        self.assertIn('/health', SERVER)
        self.assertIn('/v1/models', SERVER)
        self.assertIn("def _port_open(", SERVER)
        self.assertIn("def _model_matches_ids(", SERVER)

    def test_desktop_uses_shared_manager(self):
        self.assertIn('LlamaServer(interface_name="Desktop")', UI)
        self.assertIn("self.server.ensure_running(", UI)
        self.assertIn("self.server.wait_until_ready(timeout=90)", UI)
        self.assertNotIn("if self.server.is_running():\n            self.status.set(\"ONLINE\")", UI)

    def test_desktop_close_releases_shared_client(self):
        self.assertIn("self.server.release()", UI)
        self.assertNotIn("if self.server.is_running():\n            self.server.stop()", UI)

    def test_webui_uses_shared_manager(self):
        self.assertIn("from core.server import LlamaServer", WEB)
        self.assertIn("LlamaServer(interface_name='WebUI',new_console=True)", WEB)
        self.assertIn("web_llama_server.ensure_running(", WEB)
        self.assertIn("web_llama_server.wait_until_ready(timeout=90)", WEB)

    def test_webui_direct_llama_popen_removed(self):
        self.assertNotIn("chat_process=launch([str(ENGINE),'--model'", WEB)
        self.assertIn("result=web_llama_server.stop()", WEB)

    def test_webui_uses_desktop_server_context_and_threads(self):
        self.assertIn("def chat_server_settings():", WEB)
        self.assertIn("FoxAI.ini", WEB)
        self.assertIn("context=config.get('Server','context'", WEB)
        self.assertIn("threads=config.get('Server','threads'", WEB)

if __name__ == "__main__":
    unittest.main(verbosity=2)
