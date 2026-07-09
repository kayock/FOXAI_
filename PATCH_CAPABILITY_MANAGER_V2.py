from __future__ import annotations

from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parent
BUS = ROOT / "core_v10" / "mission_bus.py"
ADAPTER = ROOT / "core_v10" / "capability_adapter.py"

def fail(msg: str) -> None:
    print("[FOXAI CM v2 ERROR]", msg)
    raise SystemExit(1)

def backup(path: Path) -> None:
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    b = path.with_name(f"{path.stem}_backup_before_cm_v2_{stamp}{path.suffix}")
    shutil.copy2(path, b)
    print(f"[FOXAI CM v2] Backup created: {b}")

def patch_adapter() -> bool:
    if not ADAPTER.exists():
        fail("Missing core_v10\\capability_adapter.py. Install Capability Manager v1 first.")

    text = ADAPTER.read_text(encoding="utf-8", errors="replace")
    backup(ADAPTER)
    changed = False

    if "def python_adapter_path" not in text:
        marker = "    def health(self) -> dict[str, Any]:\n"
        helper = '''    def python_adapter_path(self) -> Path | None:
        candidate = self.adapter_path.parent / "adapter.py"
        return candidate if candidate.exists() else None

    def has_python_adapter(self) -> bool:
        return self.python_adapter_path() is not None

'''
        if marker not in text:
            fail("Could not find health() marker in capability_adapter.py")
        text = text.replace(marker, helper + marker)
        changed = True
        print("[FOXAI CM v2] Added adapter.py detection.")

    if "has_python_adapter" not in text.split("def summary", 1)[-1]:
        old = '            "path": str(self.executable_path()) if self.executable_path() else None,\n        }\n'
        new = '            "path": str(self.executable_path()) if self.executable_path() else None,\n            "has_python_adapter": self.has_python_adapter(),\n            "adapter_file": str(self.python_adapter_path()) if self.python_adapter_path() else None,\n        }\n'
        if old in text:
            text = text.replace(old, new)
            changed = True
            print("[FOXAI CM v2] Added adapter.py fields to summary.")
        else:
            print("[FOXAI CM v2] Summary marker not found; skipping summary enhancement.")

    if changed:
        ADAPTER.write_text(text, encoding="utf-8")
        print("[FOXAI CM v2] capability_adapter.py patched.")
    return changed

def patch_bus() -> bool:
    if not BUS.exists():
        fail("Missing core_v10\\mission_bus.py. Install Mission Bus first.")

    text = BUS.read_text(encoding="utf-8", errors="replace")
    backup(BUS)
    changed = False

    if "from .capability_manager import CapabilityManager" not in text:
        marker = "from .foxai_core import FoxAICore\n"
        if marker not in text:
            fail("Could not find FoxAICore import marker in mission_bus.py")
        text = text.replace(marker, marker + "from .capability_manager import CapabilityManager\n")
        changed = True
        print("[FOXAI CM v2] Imported CapabilityManager into MissionBus.")

    if "self.capabilities = CapabilityManager(self.foxai_root)" not in text:
        marker = "        self.core = FoxAICore(self.foxai_root)\n"
        if marker not in text:
            fail("Could not find __post_init__ marker in mission_bus.py")
        text = text.replace(marker, marker + "        self.capabilities = CapabilityManager(self.foxai_root)\n")
        changed = True
        print("[FOXAI CM v2] Added CapabilityManager instance to MissionBus.")

    if 'command == "capabilities.list"' not in text:
        marker = '''            if command == "projects.create":
                name = payload.get("name", "")
                if not name:
                    return {"ok": False, "message": "Missing project name."}
                return self.core.create_project(name)

'''
        add = '''            if command == "capabilities.list":
                return {"ok": True, "capabilities": self.capabilities.list()}

            if command == "capabilities.health":
                return self.capabilities.health(payload.get("key"))

            if command == "capabilities.find":
                capability = payload.get("capability", "")
                if not capability:
                    return {"ok": False, "message": "Missing capability name."}
                return {"ok": True, "matches": self.capabilities.by_capability(capability)}

            if command == "capabilities.launch":
                key = payload.get("key", "")
                if not key:
                    return {"ok": False, "message": "Missing capability key."}
                return self.capabilities.launch(key)

'''
        if marker not in text:
            fail("Could not find projects.create command marker in mission_bus.py")
        text = text.replace(marker, marker + add)
        changed = True
        print("[FOXAI CM v2] Added capability commands to MissionBus.")

    if changed:
        BUS.write_text(text, encoding="utf-8")
        print("[FOXAI CM v2] mission_bus.py patched.")
    return changed

def main() -> int:
    patch_adapter()
    patch_bus()
    print()
    print("Next:")
    print("1. Run TEST_CAPABILITY_BUS.bat")
    print("2. If it passes, Hangar Bay can be wired to capabilities.list.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
