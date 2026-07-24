from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code_slicer_v1 import CodeSlicer
from project_forge_preview8 import ForgeConfig, SurgicalForge, sha256_file

EXPECTED_SLICER_SHA256 = "d2385086ba36a66692f9c596ff58cb4e41143e23bc83d8a12ba58022df4ec98d"


class Preview8Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="forge_preview8_test_")
        self.base = Path(self.temp.name)
        self.source = self.base / "DirtyPythonLab"
        self.workspaces = self.base / "Workspaces"
        self.source.mkdir()
        (self.source / "tests").mkdir()
        self._write_1044_line_lab()
        (self.source / "tests" / "test_dirty_python_lab.py").write_text(
            textwrap.dedent(
                """
                import unittest
                from dirty_python_lab import target_value

                class DirtyLabTests(unittest.TestCase):
                    def test_target_value(self):
                        self.assertEqual(target_value(), 2)

                if __name__ == "__main__":
                    unittest.main()
                """
            ).lstrip(),
            encoding="utf-8",
        )
        (self.source / "config.json").write_text("{}\n", encoding="utf-8")
        self.fake_opencode = self.base / "fake_opencode.py"
        patch_text = (
            "--- a/dirty_python_lab.py\n"
            "+++ b/dirty_python_lab.py\n"
            "@@ -1,3 +1,3 @@\n"
            " def target_value():\n"
            "-    return 1\n"
            "+    return 2\n"
            " \n"
        )
        fake_source = (
            "from pathlib import Path\n\n"
            f"patch = {patch_text!r}\n"
            'Path("PROPOSED.patch").write_text(patch, encoding="utf-8")\n'
            "print('{\"type\":\"text\",\"text\":\"wrote surgical patch\"}')\n"
        )
        self.fake_opencode.write_text(fake_source, encoding="utf-8")
        self.config = ForgeConfig(
            source_root=str(self.source),
            workspace_root=str(self.workspaces),
            endpoint="http://127.0.0.1:9/v1",
            model_id="synthetic-model",
            context_limit=16384,
            output_limit=1024,
            max_rounds=1,
            initial_symbol_limit=6,
            repair_symbol_limit=6,
            seed_symbols=["target_value"],
            opencode_command=[sys.executable, str(self.fake_opencode)],
            test_commands=[["{python}", "-m", "unittest", "discover", "-s", "tests", "-v"]],
            opencode_timeout_seconds=30,
            test_timeout_seconds=30,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_1044_line_lab(self) -> None:
        lines = [
            "def target_value():",
            "    return 1",
            "",
            "class Outer:",
            "    def method(self):",
            "        def inner():",
            "            return 'inner'",
            "        return inner()",
        ]
        while len(lines) < 1044:
            lines.append(f"# filler line {len(lines) + 1}")
        self.assertEqual(len(lines), 1044)
        (self.source / "dirty_python_lab.py").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_exact_uploaded_slicer_hash(self) -> None:
        self.assertEqual(sha256_file(ROOT / "code_slicer_v1.py"), EXPECTED_SLICER_SHA256)

    def test_slicer_maps_and_extracts_qualified_symbols(self) -> None:
        slicer = CodeSlicer(str(self.source / "dirty_python_lab.py"))
        symbols = slicer.get_symbol_map()
        names = {item["qualified_name"] for item in symbols}
        self.assertIn("target_value", names)
        self.assertIn("Outer.method", names)
        self.assertIn("Outer.method.inner", names)
        sliced = slicer.extract_slice(["target_value"])
        self.assertIn("Symbol: target_value", sliced)
        self.assertIn("   1 | def target_value():", sliced)
        self.assertNotIn("filler line 1044", sliced)

    def test_review_detects_1044_lines_without_modifying_source(self) -> None:
        forge = SurgicalForge(self.config)
        before = sha256_file(self.source / "dirty_python_lab.py")
        review = forge.review(task="Change target_value to return 2")
        after = sha256_file(self.source / "dirty_python_lab.py")
        self.assertEqual(review["target_lines"], 1044)
        self.assertIn("target_value", review["selected_symbols"])
        self.assertEqual(before, after)
        self.assertTrue(review["whole_file_read_blocked_for_opencode"])

    def test_agent_view_physically_excludes_target(self) -> None:
        forge = SurgicalForge(self.config)
        snapshot = forge.create_snapshot(task="Change target_value to return 2")
        project = Path(snapshot["project"])
        view = forge.build_agent_view(project, "Change target_value to return 2", 1)
        agent_view = Path(view["agent_view"])
        self.assertFalse((agent_view / "dirty_python_lab.py").exists())
        self.assertEqual(list(agent_view.rglob("dirty_python_lab.py")), [])
        selected = json.loads((agent_view / "slices" / "SELECTED_SYMBOLS.json").read_text(encoding="utf-8"))
        self.assertTrue(any(item["qualified_name"] == "target_value" for item in selected))
        config = json.loads((agent_view / "opencode.json").read_text(encoding="utf-8"))
        self.assertEqual(config["permission"]["external_directory"], "deny")
        self.assertEqual(config["permission"]["bash"], "deny")

    def test_patch_validator_rejects_protected_test_edit(self) -> None:
        forge = SurgicalForge(self.config)
        snapshot = forge.create_snapshot(task="Change target_value to return 2")
        project = Path(snapshot["project"])
        patch = project.parent / "bad.patch"
        patch.write_text(
            "--- a/tests/test_dirty_python_lab.py\n+++ b/tests/test_dirty_python_lab.py\n@@ -1,1 +1,1 @@\n-import unittest\n+import unittest # changed\n",
            encoding="utf-8",
        )
        result = forge.validate_patch(project, patch)
        self.assertFalse(result["valid"])
        self.assertTrue(any("not allowed" in item for item in result["errors"]))

    def test_end_to_end_disposable_build_and_rollback(self) -> None:
        forge = SurgicalForge(self.config)
        original_before = sha256_file(self.source / "dirty_python_lab.py")
        receipt = forge.run_surgical_build(
            task="Change target_value so the protected test passes.",
            require_live_model_probe=False,
        )
        self.assertEqual(receipt["status"], "passed_disposable_only")
        self.assertFalse(receipt["whole_target_available_to_opencode"])
        self.assertEqual(receipt["host_profile_write_count"], 0)
        self.assertEqual(receipt["original_source_changes"], [])
        self.assertTrue(receipt["stopped_before_original_apply"])
        self.assertEqual(original_before, sha256_file(self.source / "dirty_python_lab.py"))
        disposable = Path(receipt["project"]) / "dirty_python_lab.py"
        self.assertIn("return 2", disposable.read_text(encoding="utf-8"))
        self.assertTrue(receipt["final_tests"]["passed"])
        rolled = forge.rollback()
        self.assertTrue(rolled["rolled_back"])
        self.assertIn("return 1", disposable.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
