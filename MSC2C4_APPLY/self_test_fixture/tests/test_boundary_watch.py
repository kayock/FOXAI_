from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from core.security_containment import (
    AuthorizationDecision,
    _canonical_json,
    airlock_chain_alert,
    record_authorization_decision,
    record_boundary_denial,
    record_trip_sentry_test_event,
    validate_airlock_route_receipt,
    verify_airlock_audit_log,
)


class BoundaryWatchTests(unittest.TestCase):
    def test_legacy_event_remains_valid_and_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            legacy = {
                "event_id": "evt_legacy",
                "correlation_id": "corr_legacy",
                "mission_id": "mission_legacy",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "actor": "operator",
                "object": "engineering_airlock",
                "action": "route",
                "decision": "allow",
                "reason": "legacy",
                "policy_source": "legacy",
                "approval_id": "",
                "receipt_id": "",
                "previous_hash": "",
                "test_event": False,
            }
            legacy["event_hash"] = hashlib.sha256(
                _canonical_json(legacy).encode("utf-8")
            ).hexdigest()
            original_line = _canonical_json(legacy) + "\n"
            path.write_text(original_line, encoding="utf-8")
            self.assertTrue(verify_airlock_audit_log(path)["valid"])

            decision = AuthorizationDecision(
                True, "operator", "engineering_airlock", "route", "allowed"
            )
            receipt = record_authorization_decision(
                decision,
                correlation_id="corr_new",
                mission_id="mission_new",
                log_path=path,
            )
            self.assertTrue(receipt["verified"])
            self.assertTrue(path.read_text(encoding="utf-8").startswith(original_line))
            self.assertTrue(verify_airlock_audit_log(path)["valid"])

    def test_repeated_denial_escalates_without_rewriting(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            first = record_boundary_denial(
                actor="operator",
                obj="engineering_airlock",
                action="inspect_path",
                reason="protected",
                incident_kind="protected_resource_denial",
                correlation_id="corr_one",
                mission_id="mission_repeat",
                log_path=path,
            )
            first_line = path.read_text(encoding="utf-8").splitlines()[0]
            second = record_boundary_denial(
                actor="operator",
                obj="engineering_airlock",
                action="inspect_path",
                reason="protected again",
                incident_kind="protected_resource_denial",
                correlation_id="corr_two",
                mission_id="mission_repeat",
                log_path=path,
            )
            self.assertTrue(first["verified"])
            self.assertTrue(second["verified"])
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0]["severity"], "NOTICE")
            self.assertEqual(events[0]["attempt_count"], 1)
            self.assertEqual(events[1]["severity"], "WARNING")
            self.assertEqual(events[1]["attempt_count"], 2)
            self.assertEqual(path.read_text(encoding="utf-8").splitlines()[0], first_line)

    def test_route_receipt_context_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            route = record_authorization_decision(
                AuthorizationDecision(
                    True, "operator", "engineering_airlock", "route", "allowed"
                ),
                correlation_id="corr_route",
                mission_id="mission_route",
                log_path=path,
            )
            valid = validate_airlock_route_receipt(
                route,
                expected_actor="operator",
                expected_object="engineering_airlock",
                expected_action="route",
                correlation_id="corr_route",
                mission_id="mission_route",
            )
            mismatch = validate_airlock_route_receipt(
                route,
                expected_actor="operator",
                expected_object="engineering_airlock",
                expected_action="route",
                correlation_id="corr_route",
                mission_id="other_mission",
            )
            self.assertTrue(valid["verified"])
            self.assertFalse(mismatch["verified"])

    def test_trip_sentry_remains_test(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            receipt = record_trip_sentry_test_event(
                correlation_id="corr_test",
                mission_id="mission_test",
                log_path=path,
            )
            event = receipt["details"]["event"]
            self.assertTrue(receipt["verified"])
            self.assertEqual(event["severity"], "TEST")
            self.assertEqual(event["incident_kind"], "trip_sentry_test")
            self.assertTrue(event["test_event"])

    def test_invalid_chain_fails_closed_and_creates_synthetic_alert(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            path.write_text('{"broken":true}\n', encoding="utf-8")
            before = path.read_bytes()
            receipt = record_boundary_denial(
                actor="operator",
                obj="engineering_airlock",
                action="inspect_path",
                reason="blocked",
                incident_kind="protected_resource_denial",
                correlation_id="corr_bad",
                mission_id="mission_bad",
                log_path=path,
            )
            verification = verify_airlock_audit_log(path)
            alert = airlock_chain_alert(verification)
            self.assertFalse(receipt["verified"])
            self.assertEqual(path.read_bytes(), before)
            self.assertTrue(alert["active"])
            self.assertEqual(alert["severity"], "CRITICAL")


if __name__ == "__main__":
    unittest.main()
