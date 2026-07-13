from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(os.environ["FOXAI_LIVE_ROOT"]).resolve()
sys.path.insert(0, str(ROOT))

from core import director
from core.security_containment import (
    authorize_repair_action,
    guard_model_action_claims,
    is_protected_path,
    make_tool_receipt,
    redact_secrets,
)
from core.smart_search import SmartSearch


class RoutingTests(unittest.TestCase):
    def test_bare_engineer_word_does_not_route(self):
        result = director.classify("Engineer is the name of a department.")
        self.assertEqual(result["agent"], "chat")

    def test_delegation_phrase_does_not_route_by_bare_word(self):
        result = director.classify("Agent Fox, tell Engineer hello.")
        self.assertEqual(result["agent"], "chat")

    def test_explicit_operator_engineer_command_routes(self):
        result = director.classify("/engineer investigate timeout", actor="operator")
        self.assertEqual(result["agent"], "engineer")
        self.assertTrue(result["authorization"]["allowed"])

    def test_agent_fox_cannot_route_engineer(self):
        result = director.classify("/engineer investigate timeout", actor="agent_fox")
        self.assertEqual(result["agent"], "chat")
        self.assertFalse(result["authorization"]["allowed"])


class RepairAuthorizationTests(unittest.TestCase):
    def test_agent_fox_cannot_apply(self):
        decision = authorize_repair_action("agent_fox", "ui_operator", "APPLY refresh_root_manifest", "refresh_root_manifest")
        self.assertFalse(decision.allowed)

    def test_yes_is_not_enough(self):
        decision = authorize_repair_action("operator", "ui_operator", "YES", "refresh_root_manifest")
        self.assertFalse(decision.allowed)

    def test_exact_operator_phrase_is_allowed(self):
        decision = authorize_repair_action("operator", "ui_operator", "APPLY refresh_root_manifest", "refresh_root_manifest")
        self.assertTrue(decision.allowed)


class RedactionTests(unittest.TestCase):
    def test_protected_paths(self):
        self.assertTrue(is_protected_path(Path("Secrets") / "token.txt"))
        self.assertTrue(is_protected_path(Path("Config") / ".env"))
        self.assertTrue(is_protected_path(Path("Keys") / "server.pem"))
        self.assertFalse(is_protected_path(Path("core") / "director.py"))

    def test_secret_redaction(self):
        clean, count = redact_secrets('api_key = "sk-proj-abcdefghijklmnopqrstuvwxyz123456"\npassword=hunter2')
        self.assertGreaterEqual(count, 2)
        self.assertNotIn("hunter2", clean)
        self.assertNotIn("sk-proj-abcdefghijklmnopqrstuvwxyz123456", clean)

    def test_smart_search_excludes_and_redacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "core").mkdir()
            (root / "Secrets").mkdir()
            (root / "core" / "a.py").write_text('needle = "yes"\napi_key = "sk-proj-abcdefghijklmnopqrstuvwxyz123456"', encoding="utf-8")
            (root / "Secrets" / "hidden.txt").write_text("needle secret", encoding="utf-8")
            results = SmartSearch(root).search("needle", include_history=True)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["file"], "core/a.py")
            self.assertNotIn("sk-proj-abcdefghijklmnopqrstuvwxyz123456", results[0]["snippet"])


class ReceiptTests(unittest.TestCase):
    def test_verified_requires_passing_checks(self):
        receipt = make_tool_receipt("x", "verified", checks=[])
        self.assertEqual(receipt["state"], "unverified")
        receipt = make_tool_receipt("x", "verified", checks=[{"ok": True}])
        self.assertTrue(receipt["verified"])

    def test_model_claim_is_flagged(self):
        guarded = guard_model_action_claims("I successfully deleted the file.")
        self.assertTrue(guarded["flagged"])
        self.assertIn("UNVERIFIED ACTION CLAIM", guarded["text"])


class WebStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = (ROOT / "core" / "foxai_web.py").read_text(encoding="utf-8")

    def test_grouped_navigation_present(self):
        self.assertIn("initDepartmentNav", self.web)
        self.assertIn("Ctrl+K", self.web)
        self.assertIn("NAV_GROUPS", self.web)

    def test_repair_gate_present(self):
        self.assertIn("approval_source:'ui_operator'", self.web)
        self.assertIn("authorize_repair_action", self.web)
        self.assertIn("repair_chamber.apply", self.web)

    def test_search_protection_present(self):
        self.assertIn("is_protected_path", self.web)
        self.assertIn("redact_secrets", self.web)


if __name__ == "__main__":
    unittest.main(verbosity=2)
