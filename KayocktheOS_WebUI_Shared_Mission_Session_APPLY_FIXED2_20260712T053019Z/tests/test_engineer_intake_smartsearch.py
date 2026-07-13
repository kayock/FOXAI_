from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "candidate" / "core" / "engineer_agent.py"
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT
# Keep unittest from interpreting the source path as a test selector.
sys.argv[:] = [sys.argv[0]]

TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
ENGINEER = next(
    node for node in TREE.body
    if isinstance(node, ast.ClassDef) and node.name == "EngineerAgent"
)

def method(name):
    node = next(
        node for node in ENGINEER.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {"re": re}
    exec(compile(module, str(SOURCE), "exec"), ns)
    return ns[name]

normalize_operator_query = method("normalize_operator_query")
smart_search_report = method("smart_search_report")
analyze = method("analyze")

class FakeSearch:
    def __init__(self):
        self.targets = []

    def format_report(self, target):
        self.targets.append(target)
        return f"TARGET={target}"

class FakeIntent:
    def classify(self, query):
        return {"intent": "project_search"}

class FakeEngineer:
    normalize_operator_query = staticmethod(normalize_operator_query)
    smart_search_report = smart_search_report
    analyze = analyze

    def __init__(self):
        self.smart_search = FakeSearch()
        self.intent = FakeIntent()

class NormalizationTests(unittest.TestCase):
    def test_slash_prefix_removed(self):
        self.assertEqual(
            normalize_operator_query("/engineer smart search for COMFY_MAIN"),
            "smart search for COMFY_MAIN",
        )

    def test_colon_prefix_removed(self):
        self.assertEqual(
            normalize_operator_query("Engineer: review core/foxai_web.py"),
            "review core/foxai_web.py",
        )

    def test_comma_prefix_removed(self):
        self.assertEqual(
            normalize_operator_query("Engineer, investigate ComfyUI"),
            "investigate ComfyUI",
        )

    def test_ordinary_engineers_word_preserved(self):
        self.assertEqual(
            normalize_operator_query("What do engineers do?"),
            "What do engineers do?",
        )

class SmartSearchTests(unittest.TestCase):
    def test_target_is_extracted(self):
        obj = FakeEngineer()
        result = obj.smart_search_report("/engineer smart search for COMFY_MAIN")
        self.assertEqual(result, "TARGET=COMFY_MAIN")
        self.assertEqual(obj.smart_search.targets, ["COMFY_MAIN"])

    def test_quoted_target_is_dequoted(self):
        obj = FakeEngineer()
        result = obj.smart_search_report('/engineer smart search for "launch(pycmd()"')
        self.assertEqual(result, "TARGET=launch(pycmd()")
        self.assertEqual(obj.smart_search.targets, ["launch(pycmd()"])

    def test_empty_target_is_safe_and_read_only(self):
        obj = FakeEngineer()
        result = obj.smart_search_report("/engineer smart search for ")
        self.assertIn("No search target was provided.", result)
        self.assertIn("Read-only. No files were modified.", result)
        self.assertEqual(obj.smart_search.targets, [])

    def test_analyze_routes_to_parsed_smart_search(self):
        obj = FakeEngineer()
        result = obj.analyze("/engineer smart search for COMFY_MAIN")
        self.assertEqual(result, "TARGET=COMFY_MAIN")
        self.assertEqual(obj.smart_search.targets, ["COMFY_MAIN"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
