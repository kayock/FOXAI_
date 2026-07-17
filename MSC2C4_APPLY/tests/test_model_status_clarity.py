from __future__ import annotations

from pathlib import Path
import ast
import os
import unittest


class ModelStatusClarityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        target = os.environ.get("FOXAI_WEB_UNDER_TEST")
        if not target:
            raise RuntimeError("FOXAI_WEB_UNDER_TEST was not provided.")
        cls.path = Path(target)
        cls.text = cls.path.read_text(encoding="utf-8")

    def test_python_parses(self):
        ast.parse(self.text)

    def test_old_combined_status_removed(self):
        self.assertNotIn(
            "`ONLINE • ${s.chat_model_source_label||'LOCAL'}`",
            self.text,
        )
        self.assertNotIn(
            "<div class=lab>Runtime</div><div id=rt>",
            self.text,
        )

    def test_three_operator_labels_present(self):
        for expected in (
            "<div class=row><div class=lab>Engine</div><div id=rt>",
            "<div class=row><div class=lab>Model source</div><div id=msrc>",
            "<div class=row><div class=lab>Network use</div><div id=nuse>",
        ):
            self.assertIn(expected, self.text)

    def test_backend_engine_state_present(self):
        self.assertIn(
            "'chat_engine_state':'RUNNING' if chat_online else 'STOPPED'",
            self.text,
        )

    def test_backend_network_mapping_present(self):
        self.assertIn("active_source_type=='LAN_OPENAI_COMPATIBLE'", self.text)
        self.assertIn("chat_network_use='LAN'", self.text)
        self.assertIn("active_source_type=='ONLINE_PROVIDER'", self.text)
        self.assertIn("chat_network_use='INTERNET'", self.text)
        self.assertIn("chat_network_use='NONE'", self.text)

    def test_frontend_fields_are_separate(self):
        self.assertIn("q('rt').textContent=s.chat_engine_state", self.text)
        self.assertIn("q('msrc').textContent=s.chat_online?", self.text)
        self.assertIn("q('nuse').textContent=s.chat_network_use||'NONE'", self.text)

    def test_local_profiles_report_no_network(self):
        self.assertIn("else:\n        chat_network_use='NONE'", self.text)

    def test_quick_status_uses_running_stopped(self):
        self.assertIn("Chat ${s.chat_online?'Running':'Stopped'}", self.text)
        self.assertIn("ComfyUI ${s.comfy_online?'Running':'Stopped'}", self.text)

    def test_model_source_and_fallback_contract_preserved(self):
        for expected in (
            "Selected approved model is unavailable. No fallback or engine action occurred.",
            "'silent_fallback_used':False",
            "Selected model source does not match the requested ",
        ):
            self.assertIn(expected, self.text)

    def test_online_provider_not_enabled(self):
        self.assertNotIn("'online_sources_enabled': True", self.text)
        self.assertNotIn('"online_sources_enabled": true', self.text)


if __name__ == "__main__":
    unittest.main()
