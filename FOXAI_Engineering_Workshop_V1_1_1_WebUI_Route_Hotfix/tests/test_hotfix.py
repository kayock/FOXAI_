from pathlib import Path
import importlib.util
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "INSTALL_ENGINEERING_WORKSHOP_V1_1_1.py"
spec = importlib.util.spec_from_file_location("hotfix", MODULE_PATH)
hotfix = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hotfix)


class HotfixTests(unittest.TestCase):
    def test_webui_route_is_inserted_before_analyze(self):
        source = """def web_engineer_analyze(text, caller='operator'):\n    with lock:\n        try:\n            return _web_engineer.analyze(text)\n        finally:\n            pass\n"""
        patched, changes = hotfix.patch_webui(source)
        self.assertIn(hotfix.HOTFIX_MARKER, patched)
        self.assertIn("workshop_bridge.handle", patched)
        self.assertLess(
            patched.index(hotfix.HOTFIX_MARKER),
            patched.index("return _web_engineer.analyze(text)"),
        )
        self.assertEqual(changes, ["routed_workshop_before_read_only_analyze"])

    def test_webui_patch_is_idempotent(self):
        source = """def f(text):\n        try:\n            return _web_engineer.analyze(text)\n        finally:\n            pass\n"""
        first, _ = hotfix.patch_webui(source)
        second, changes = hotfix.patch_webui(first)
        self.assertEqual(first, second)
        self.assertEqual(changes, [])

    def test_engineer_import_error_is_exposed(self):
        source = (
            hotfix.OLD_IMPORT_BLOCK
            + "\nclass EngineerAgent:\n    def __init__(self):\n"
            + hotfix.OLD_INIT_BLOCK
        )
        patched, changes = hotfix.patch_engineer_agent(source)
        self.assertIn("_ENGINEERING_WORKSHOP_IMPORT_ERROR", patched)
        self.assertIn("self._engineering_workshop_import_error", patched)
        self.assertEqual(len(changes), 2)


if __name__ == "__main__":
    unittest.main()
