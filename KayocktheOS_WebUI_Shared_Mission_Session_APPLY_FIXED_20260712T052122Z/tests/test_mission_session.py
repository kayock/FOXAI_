from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.mission_session import MissionSession


class MissionSessionTests(unittest.TestCase):
    def test_stable_path_and_multi_turn_archive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            session = MissionSession(root, interface_name="WebUI")
            start = session.start(project="FOXAI", professor="Agent Fox", model="model.gguf")
            self.assertTrue(start["verified"])
            first_path = session.archive_path
            session.add("ERIC", "First message")
            session.add("AGENT FOX", "First answer")
            first = session.save()
            self.assertTrue(first["verified"])
            self.assertEqual(session.archive_path, first_path)

            session.add("ERIC", "Second message")
            session.add("ENGINEER", "Second answer")
            second = session.save()
            self.assertTrue(second["verified"])
            self.assertEqual(session.archive_path, first_path)

            text = first_path.read_text(encoding="utf-8")
            self.assertIn("First message", text)
            self.assertIn("First answer", text)
            self.assertIn("Second message", text)
            self.assertIn("Second answer", text)
            self.assertIn("Interface: WebUI", text)

    def test_archive_is_under_mission_archive_chats(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            session = MissionSession(root, interface_name="WebUI")
            session.start()
            path = session.archive_path.resolve()
            expected = (root / "Mission Archive" / "Chats").resolve()
            path.relative_to(expected)

    def test_context_change_starts_new_session(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            session = MissionSession(root, interface_name="WebUI")
            session.start(project="One", professor="Agent Fox", model="A")
            first = session.archive_path
            session.ensure_started(project="Two", professor="Agent Fox", model="A")
            self.assertNotEqual(first, session.archive_path)

    def test_empty_transcript_cannot_claim_archive_success(self):
        with tempfile.TemporaryDirectory() as td:
            session = MissionSession(td, interface_name="WebUI")
            session.start()
            receipt = session.save()
            self.assertFalse(receipt["verified"])
            self.assertEqual(receipt["state"], "failed")

    def test_replace_failure_never_claims_success(self):
        with tempfile.TemporaryDirectory() as td:
            session = MissionSession(td, interface_name="WebUI")
            session.start()
            session.add("ERIC", "Test")
            with patch("core.mission_session.os.replace", side_effect=OSError("simulated failure")):
                receipt = session.save()
            self.assertFalse(receipt["verified"])
            self.assertEqual(receipt["state"], "failed")

    def test_existing_session_reused_when_context_is_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            session = MissionSession(td, interface_name="WebUI")
            session.start(project="FOXAI", professor="Agent Fox", model="A")
            first = session.archive_path
            receipt = session.ensure_started(project="FOXAI", professor="Agent Fox", model="A")
            self.assertTrue(receipt["verified"])
            self.assertEqual(first, session.archive_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
