from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "payload"
sys.path.insert(0, str(ROOT))

from core.smart_search import SmartSearch


class SmartSearchEvidenceCleanupTests(unittest.TestCase):
    def write(self, root: Path, relative: str, text: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_live_source_wins_and_generated_copies_are_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "core/live.py", "needle = 'live'")
            self.write(
                root,
                "KayocktheOS_Test_APPLY_20260712/candidate/core/live.py",
                "needle = 'candidate'",
            )
            self.write(
                root,
                "KayocktheOS_Test_PREVIEW_20260712/payload/core/live.py",
                "needle = 'preview'",
            )
            self.write(
                root,
                "KayocktheOS_Test_Patch_Bundle_20260712/payload/core/live.py",
                "needle = 'patch'",
            )
            self.write(
                root,
                "KayocktheOS_Test_Checkpoint_20260712/payload/core/live.py",
                "needle = 'checkpoint'",
            )
            self.write(root, "Backups/old/core/live.py", "needle = 'backup'")

            data = SmartSearch(root).layered_search("needle")
            self.assertEqual(data["scope"], "Executable/source evidence")
            self.assertEqual([item["file"] for item in data["primary"]], ["core/live.py"])

    def test_backup_tree_is_never_returned_even_in_broad_search(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "Backups/old.py", "backup_only_marker = True")
            results = SmartSearch(root).search(
                "backup_only_marker",
                include_vendor=True,
                include_history=True,
            )
            self.assertEqual(results, [])

    def test_memory_python_is_project_memory_not_primary_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "Memory/ui/main_window.py", "memory_only_marker = True")
            data = SmartSearch(root).layered_search("memory_only_marker")
            self.assertEqual(data["scope"], "Project knowledge / history fallback")
            self.assertEqual(data["primary"], [])
            self.assertEqual(data["history"][0]["evidence_class"], "project_memory")
            self.assertEqual(data["history"][0]["file"], "Memory/ui/main_window.py")

    def test_legitimate_kayocktheos_folder_without_artifact_marker_is_searchable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "KayocktheOS_Runtime/tool.py", "runtime_marker = True")
            results = SmartSearch(root).search("runtime_marker")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["file"], "KayocktheOS_Runtime/tool.py")

    def test_vendor_fallback_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "ComfyUI/vendor.py", "vendor_only_marker = True")
            data = SmartSearch(root).layered_search("vendor_only_marker")
            self.assertEqual(data["scope"], "Vendor fallback")
            self.assertEqual(data["vendor"][0]["file"], "ComfyUI/vendor.py")

    def test_protected_paths_and_secret_redaction_are_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(
                root,
                "core/live.py",
                'needle = True\napi_key = "sk-proj-abcdefghijklmnopqrstuvwxyz123456"',
            )
            self.write(root, "Secrets/hidden.txt", "needle = secret")
            results = SmartSearch(root).search("needle", include_history=True)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["file"], "core/live.py")
            self.assertNotIn(
                "sk-proj-abcdefghijklmnopqrstuvwxyz123456",
                results[0]["snippet"],
            )

    def test_report_discloses_generated_artifact_exclusion(self):
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
