import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "INSTALL_ENGINEERING_WORKSHOP_V1_2.py"
spec = importlib.util.spec_from_file_location("installer", SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

BASE = '''import re\n\nclass EngineerAgent:\n    def normalize_operator_query(self, query):\n        return query\n\n    def analyze(self, query):\n        query = self.normalize_operator_query(query)\n        lowered = query.lower()\n        return lowered\n'''

class PackageTests(unittest.TestCase):
    def test_patches_analyze_only(self):
        patched, changes = installer.patch_engineer_source(BASE)
        self.assertIn(installer.MARKER, patched)
        self.assertEqual(len(changes), 1)
        self.assertIn("from core.engineering_workshop_bridge import EngineeringWorkshopBridge", patched)
        compile(patched, "fixture.py", "exec")

    def test_idempotent(self):
        patched, _ = installer.patch_engineer_source(BASE)
        second, changes = installer.patch_engineer_source(patched)
        self.assertEqual(patched, second)
        self.assertEqual(changes, [])

    def test_rejects_unknown_anchor(self):
        with self.assertRaises(RuntimeError):
            installer.patch_engineer_source("class EngineerAgent:\n    pass\n")

    def test_preserves_crlf(self):
        source = BASE.replace("\n", "\r\n")
        patched, _ = installer.patch_engineer_source(source, "\r\n")
        self.assertIn("\r\n", patched)
        self.assertNotIn("\n", patched.replace("\r\n", ""))

    def test_package_never_targets_webui(self):
        script_text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"file_targeted": "core/engineer_agent.py"', script_text)
        self.assertNotIn("atomic_write(webui", script_text)

if __name__ == "__main__":
    unittest.main()
