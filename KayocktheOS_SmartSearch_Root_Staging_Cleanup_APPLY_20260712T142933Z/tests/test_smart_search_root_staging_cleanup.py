from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "payload"
sys.path.insert(0, str(ROOT))

from core.smart_search import SmartSearch


class SmartSearchRootStagingCleanupTests(unittest.TestCase):
    def write(self, root: Path, relative: str, text: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_root_candidate_payload_and_baseline_are_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "core/live.py", "needle = 'live'")
            self.write(root, "candidate/core/live.py", "needle = 'candidate'")
            self.write(root, "payload/core/live.py", "needle = 'payload'")
            self.write(root, "baseline/core/live.py", "needle = 'baseline'")

            data = SmartSearch(root).layered_search("needle")
            self.assertEqual(data["scope"], "Executable/source evidence")
            self.assertEqual(
                [item["file"] for item in data["primary"]],
                ["core/live.py"],
            )
            self.assertEqual(data["history"], [])
            self.assertEqual(data["vendor"], [])

    def test_root_staging_dirs_are_excluded_in_broad_search(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "candidate/a.py", "stage_only_marker = True")
            self.write(root, "payload/b.py", "stage_only_marker = True")
            self.write(root, "baseline/c.py", "stage_only_marker = True")
            results = SmartSearch(root).search(
                "stage_only_marker",
                include_vendor=True,
                include_history=True,
            )
            self.assertEqual(results, [])

    def test_nested_legitimate_names_remain_searchable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(
                root,
                "Projects/Example/candidate_notes.md",
                "nested_candidate_marker = True",
            )
            data = SmartSearch(root).layered_search("nested_candidate_marker")
            self.assertEqual(
                data["scope"],
                "Project knowledge / history fallback",
            )
            self.assertEqual(
                data["history"][0]["file"],
                "Projects/Example/candidate_notes.md",
            )

    def test_live_source_priority_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "ui/main_window.py", "input_box = 'live'")
            self.write(
                root,
                "Memory/ui/main_window.py",
                "input_box = 'memory'",
            )
            data = SmartSearch(root).layered_search("input_box =")
            self.assertEqual(
                data["primary"][0]["file"],
                "ui/main_window.py",
            )
            self.assertTrue(
                all(
                    not item["file"].startswith("Memory/")
                    for item in data["primary"]
                )
            )

    def test_generated_named_bundle_exclusion_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "core/live.py", "bundle_marker = 'live'")
            self.write(
                root,
                "KayocktheOS_Test_APPLY_20260712/candidate/core/live.py",
                "bundle_marker = 'copy'",
            )
            data = SmartSearch(root).layered_search("bundle_marker")
            self.assertEqual(
                [item["file"] for item in data["primary"]],
                ["core/live.py"],
            )

    def test_backup_exclusion_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "Backups/old.py", "backup_marker = True")
            self.assertEqual(
                SmartSearch(root).search(
                    "backup_marker",
                    include_vendor=True,
                    include_history=True,
                ),
                [],
            )

    def test_vendor_fallback_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "ComfyUI/vendor.py", "vendor_marker = True")
            data = SmartSearch(root).layered_search("vendor_marker")
            self.assertEqual(data["scope"], "Vendor fallback")
            self.assertEqual(
                data["vendor"][0]["file"],
                "ComfyUI/vendor.py",
            )

    def test_policy_disclosure_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "core/live.py", "report_marker = True")
            report = SmartSearch(root).format_report("report_marker")
            self.assertIn(
                "Generated apply/preview/checkpoint bundles and backup trees are excluded.",
                report,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
