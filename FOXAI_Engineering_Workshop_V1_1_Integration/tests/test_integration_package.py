from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
INSTALLER = PACKAGE / "INSTALL_ENGINEERING_WORKSHOP_V1_1.py"


ENGINEER_FIXTURE = '''from core.engineer_intent import EngineerIntent

class EngineerAgent:
    """Engineer is FOXAI's read-only code and architecture specialist.

    Current goals:
    - Never modify files.
    """
    def __init__(self, app):
        self.app = app
        self.intent = EngineerIntent()

    def handle(self, text, payload=None, caller="operator", operator_approved=False):
        query = (payload or text or "").strip()
        self.app.add_chat("ERIC", query)
        return "break"
'''

SECURITY_FIXTURE = '''
from dataclasses import dataclass

@dataclass
class Decision:
    allowed: bool
    reason: str = "allowed"

def authorize_department_route(actor, department, action="route", operator_approved=False):
    return Decision(actor in {"operator", "human_operator", "eric", "ui_operator"})

def authorize_repair_action(actor, approval_source, confirmation, action_id):
    expected = f"APPLY {action_id}".upper()
    return Decision(actor in {"operator", "human_operator", "eric", "ui_operator"} and approval_source == "ui_operator" and confirmation.strip().upper() == expected, f"Exact confirmation required: {expected}")
'''


class IntegrationPackageTests(unittest.TestCase):
    def make_root(self, base: Path) -> Path:
        root = base / "FOXAI"
        (root / "core").mkdir(parents=True)
        (root / "Departments" / "Engineering").mkdir(parents=True)
        (root / "core" / "__init__.py").write_text("", encoding="utf-8")
        (root / "Departments" / "__init__.py").write_text("", encoding="utf-8")
        (root / "core" / "engineer_intent.py").write_text("class EngineerIntent: pass\n", encoding="utf-8")
        (root / "core" / "security_containment.py").write_text(SECURITY_FIXTURE, encoding="utf-8")
        (root / "core" / "engineer_agent.py").write_text(ENGINEER_FIXTURE, encoding="utf-8")
        (root / "Departments" / "Engineering" / "placeholder.txt").write_text("old", encoding="utf-8")
        return root

    def run_installer(self, root: Path, approve: bool) -> subprocess.CompletedProcess[str]:
        argv = [sys.executable, str(INSTALLER), "--foxai-root", str(root)]
        if approve:
            argv.append("--approve")
        return subprocess.run(argv, cwd=PACKAGE, capture_output=True, text=True, timeout=240)

    def test_preview_changes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(Path(temp))
            before = (root / "core" / "engineer_agent.py").read_bytes()
            result = self.run_installer(root, False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(before, (root / "core" / "engineer_agent.py").read_bytes())
            self.assertFalse((root / "core" / "engineering_workshop_bridge.py").exists())

    def test_apply_patches_and_compiles(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(Path(temp))
            result = self.run_installer(root, True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            source = (root / "core" / "engineer_agent.py").read_text(encoding="utf-8")
            self.assertIn("FOXAI_ENGINEERING_WORKSHOP_V1_1_INTEGRATION", source)
            self.assertTrue((root / "core" / "engineering_workshop_bridge.py").exists())
            compile(source, "engineer_agent.py", "exec")

    def test_bridge_plan_preview_and_apply(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(Path(temp))
            result = self.run_installer(root, True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            sys.path.insert(0, str(root))
            try:
                module = importlib.import_module("core.engineering_workshop_bridge")
                bridge_path = root / "core" / "engineering_workshop_bridge.py"
                bridge = module.EngineeringWorkshopBridge(object())
                report = bridge.handle(
                    "/engineer workshop begin Demo :: implement a controlled demo file",
                    caller="operator",
                )
                self.assertIn("MISSION STAGED", report)
                state = bridge.workshop.state_store.load_active()
                self.assertIsNotNone(state)
                plan = {
                    "schema": "foxai.engineering.plan.v1",
                    "mission_id": state.mission_id,
                    "project_root": str(root),
                    "changes": [
                        {
                            "action": "write_file",
                            "path": "demo_controlled_builder.txt",
                            "content": "verified\n",
                            "must_not_exist": True,
                        }
                    ],
                    "validations": [
                        {
                            "name": "verify demo content",
                            "argv": [sys.executable, "-c", "from pathlib import Path; assert Path('demo_controlled_builder.txt').read_text() == 'verified\\n'"],
                            "cwd": ".",
                        }
                    ],
                }
                plan_json = json.dumps(plan)
                preview = bridge.handle(
                    f"/engineer workshop save-plan {state.mission_id} :: {plan_json}",
                    caller="operator",
                )
                self.assertIn("EXACT PLAN PREVIEW", preview)
                state = bridge.workshop.state_store.load_active()
                apply_report = bridge.handle(
                    f'/engineer workshop apply "{state.plan_path}" :: APPLY {state.plan_sha256}',
                    caller="operator",
                )
                self.assertIn("applied_verified", apply_report)
                self.assertEqual((root / "demo_controlled_builder.txt").read_text(), "verified\n")
            finally:
                sys.path.remove(str(root))
                for name in list(sys.modules):
                    if name == "Departments" or name.startswith("Departments.") or name == "core" or name.startswith("core."):
                        sys.modules.pop(name, None)


if __name__ == "__main__":
    unittest.main()
