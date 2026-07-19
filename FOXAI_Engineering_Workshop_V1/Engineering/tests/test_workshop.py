from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from Departments.Engineering.mission_router import classify_mission
from Departments.Engineering.models import MissionState
from Departments.Engineering.source_locator import SourceLocator
from Departments.Engineering.workshop import EngineeringWorkshop, WorkshopError


class RouterTests(unittest.TestCase):
    def test_find_routes_to_search(self) -> None:
        self.assertEqual(classify_mission("Find the Study launcher").mission_type, "search")

    def test_inspect_routes_to_diagnose(self) -> None:
        self.assertEqual(
            classify_mission("Inspect why Study fails to start").mission_type,
            "diagnose",
        )

    def test_implement_routes_to_implementation(self) -> None:
        decision = classify_mission("Implement Kayock's Study V1.6. Proceed with targeted source changes.")
        self.assertEqual(decision.mission_type, "implement")
        self.assertTrue(decision.authorized)

    def test_continue_resumes_active_implementation(self) -> None:
        active = MissionState("m1", "Build", "implement", True, stage="previewed")
        decision = classify_mission("continue", active)
        self.assertEqual(decision.mission_type, "implement")
        self.assertTrue(decision.authorized)
        self.assertEqual(decision.confidence, 100)


class LocatorTests(unittest.TestCase):
    def test_excludes_docs_quarantine_and_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "live").mkdir()
            (root / "live" / "study.py").write_text("research desk", encoding="utf-8")
            for folder in ("Doc", "quarantine", "snapshots"):
                (root / folder).mkdir()
                (root / folder / "fake.py").write_text("research desk", encoding="utf-8")
            results = SourceLocator().locate(root, ["research desk"])
            self.assertEqual([r.relative_path for r in results], ["live/study.py"])


class WorkshopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.project / "test_app.py").write_text(
            "import unittest\nimport app\n\n"
            "class TestApp(unittest.TestCase):\n"
            "    def test_value(self):\n"
            "        self.assertEqual(app.VALUE, 2)\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n",
            encoding="utf-8",
        )
        self.workshop = EngineeringWorkshop(self.root / "workshop_data")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _plan(self, replacement: str = "VALUE = 2\n", passing: bool = True) -> Path:
        plan = {
            "schema": "foxai.engineering.plan.v1",
            "mission_id": "fixture-build",
            "title": "Fixture implementation",
            "project_root": str(self.project),
            "changes": [
                {
                    "action": "replace_text",
                    "path": "app.py",
                    "old": "VALUE = 1\n",
                    "new": replacement,
                    "expected_occurrences": 1,
                }
            ],
            "validations": [
                {
                    "name": "fixture unittest",
                    "argv": [sys.executable, "-m", "unittest", "test_app.py"],
                    "cwd": ".",
                    "timeout_seconds": 30,
                }
            ],
        }
        if not passing:
            plan["validations"][0]["argv"] = [sys.executable, "-c", "import sys; sys.exit(7)"]
        path = self.root / ("passing_plan.json" if passing else "failing_plan.json")
        path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        return path

    def _begin(self) -> None:
        self.workshop.begin_mission(
            "fixture-build",
            "Fixture implementation",
            "Implement the approved fixture. Proceed with targeted source changes.",
            self.project,
        )

    def test_full_inspect_snapshot_modify_test_receipt_flow(self) -> None:
        self._begin()
        plan_path = self._plan()
        preview = self.workshop.preview_plan(plan_path)
        self.assertIn("app.py", preview["changed_paths"])
        receipt = self.workshop.apply_plan(plan_path, preview["plan_sha256"])
        self.assertEqual(receipt["result"], "applied_verified")
        self.assertEqual((self.project / "app.py").read_text(encoding="utf-8"), "VALUE = 2\n")
        self.assertTrue(Path(receipt["snapshot_path"]).exists())
        self.assertTrue(Path(receipt["receipt_path"]).exists())
        self.assertEqual(receipt["validations"][0]["returncode"], 0)

    def test_validation_failure_rolls_back(self) -> None:
        self._begin()
        plan_path = self._plan(replacement="VALUE = 99\n", passing=False)
        preview = self.workshop.preview_plan(plan_path)
        receipt = self.workshop.apply_plan(plan_path, preview["plan_sha256"])
        self.assertEqual(receipt["result"], "rolled_back")
        self.assertEqual((self.project / "app.py").read_text(encoding="utf-8"), "VALUE = 1\n")

    def test_wrong_approval_hash_makes_no_change(self) -> None:
        self._begin()
        plan_path = self._plan()
        self.workshop.preview_plan(plan_path)
        with self.assertRaises(WorkshopError):
            self.workshop.apply_plan(plan_path, "0" * 64)
        self.assertEqual((self.project / "app.py").read_text(encoding="utf-8"), "VALUE = 1\n")

    def test_plan_cannot_delete_or_rename(self) -> None:
        self._begin()
        plan = {
            "schema": "foxai.engineering.plan.v1",
            "mission_id": "fixture-build",
            "project_root": str(self.project),
            "changes": [{"action": "delete", "path": "app.py"}],
        }
        path = self.root / "delete_plan.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaises(Exception):
            self.workshop.preview_plan(path)

    def test_receipt_is_not_created_before_real_apply(self) -> None:
        self._begin()
        plan_path = self._plan()
        self.workshop.preview_plan(plan_path)
        self.assertFalse(any((self.root / "workshop_data" / "receipts").rglob("*.receipt.json")))


if __name__ == "__main__":
    unittest.main()
