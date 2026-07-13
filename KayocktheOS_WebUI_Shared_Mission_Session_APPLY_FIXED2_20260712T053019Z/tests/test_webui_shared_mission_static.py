from __future__ import annotations

import sys
import unittest
from pathlib import Path

SOURCE = Path(sys.argv[1]).resolve()
sys.argv[:] = [sys.argv[0]]
TEXT = SOURCE.read_text(encoding="utf-8")
SEND_START = TEXT.index("if path=='/api/chat/send':")
SEND_END = TEXT.index("self.send_response(404); self.end_headers()", SEND_START)
SEND_BLOCK = TEXT[SEND_START:SEND_END]
INTEGRATION_START = TEXT.index("from core.director import direct as direct_mission")
INTEGRATION_END = TEXT.index("FOLDERS=", INTEGRATION_START)
INTEGRATION_BLOCK = TEXT[INTEGRATION_START:INTEGRATION_END] + SEND_BLOCK


class WebUICandidateTests(unittest.TestCase):
    def test_mission_session_imported(self):
        self.assertIn("from core.mission_session import MissionSession", TEXT)

    def test_current_director_is_used(self):
        self.assertIn("from core.director import direct as direct_mission", TEXT)
        self.assertIn("direct_mission(text,actor='operator',operator_approved=True)", TEXT)

    def test_explicit_engineer_gate_is_used(self):
        self.assertIn("explicit_engineer=is_explicit_engineer_command(text)", TEXT)
        self.assertIn("route.get('agent')=='engineer'", TEXT)
        self.assertIn("engineering_airlock_allowed", TEXT)

    def test_engineer_is_read_only_analysis(self):
        self.assertIn("return _web_engineer.analyze(text)", TEXT)
        self.assertIn("'repair_authority_not_granted','ok':True", TEXT)

    def test_project_memory_write_commands_are_denied(self):
        self.assertIn("WEB_ENGINEER_WRITE_COMMANDS=", TEXT)
        self.assertIn("web_engineer_read_only_allowed(text)", SEND_BLOCK)
        self.assertIn("'webui_engineer_read_only_request','ok':read_only_allowed", SEND_BLOCK)
        self.assertIn("Project-memory write commands are not allowed", SEND_BLOCK)

    def test_archive_receipt_controls_success(self):
        self.assertGreaterEqual(TEXT.count("archived=bool(archive_receipt.get('verified'))"), 2)
        self.assertIn("'ok':archived", TEXT)

    def test_claim_guard_remains(self):
        self.assertIn("claim_guard=guard_model_action_claims(raw_ans)", TEXT)

    def test_frontend_uses_returned_speaker(self):
        self.assertIn("d.speaker||q('ap').textContent.toUpperCase()", TEXT)

    def test_new_integration_does_not_connect_parallel_core(self):
        self.assertNotIn("core_v10", INTEGRATION_BLOCK)
        self.assertNotIn("MissionBus", INTEGRATION_BLOCK)
        self.assertNotIn("archive_chat_legacy", INTEGRATION_BLOCK)

    def test_bare_engineer_text_not_used_as_route_trigger(self):
        self.assertNotIn("'engineer' in text.lower()", SEND_BLOCK)
        self.assertIn("is_explicit_engineer_command(text)", SEND_BLOCK)

    def test_chat_start_begins_session(self):
        start_block = TEXT[TEXT.index("def start_chat(model_path):"):TEXT.index("def stop_chat():")]
        self.assertEqual(start_block.count("session_receipt=begin_web_mission_session()"), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
