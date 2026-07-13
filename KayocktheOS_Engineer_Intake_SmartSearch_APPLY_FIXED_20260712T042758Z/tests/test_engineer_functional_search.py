from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: test_engineer_functional_search.py PROJECT_ROOT ENGINEER_AGENT_PATH")

ROOT = Path(sys.argv[1]).resolve()
SOURCE = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(ROOT))

from core.smart_search import SmartSearch

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

class FakeIntent:
    def classify(self, query):
        return {"intent": "project_search"}

class FunctionalEngineer:
    normalize_operator_query = staticmethod(normalize_operator_query)
    smart_search_report = smart_search_report
    analyze = analyze

    def __init__(self, root):
        self.smart_search = SmartSearch(root)
        self.intent = FakeIntent()

engineer = FunctionalEngineer(ROOT)

report = engineer.analyze("/engineer smart search for COMFY_MAIN")
assert "Query: COMFY_MAIN" in report, report[:1200]
assert "Scope: Executable/source evidence" in report, report[:1200]
assert "core/foxai_web.py" in report.replace("\\", "/"), report[:2400]

layered = engineer.smart_search.layered_search("COMFY_MAIN", limit=20)
primary_paths = [
    item.get("file", "").replace("\\", "/").lower()
    for item in layered.get("primary", [])
]
assert any(path == "core/foxai_web.py" for path in primary_paths), primary_paths
assert not any(path.startswith(".venv/") for path in primary_paths), primary_paths
assert not any("/site-packages/" in f"/{path}" for path in primary_paths), primary_paths

print("functional_engineer_search=PASS")
print("query=COMFY_MAIN")
print("source_match=core/foxai_web.py")
print("vendor_path_leak=NONE")
