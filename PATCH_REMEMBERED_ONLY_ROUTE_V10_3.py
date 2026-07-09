from __future__ import annotations

from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core_v10" / "mission_engine.py"

def fail(msg: str) -> None:
    print("[FOXAI v10.3 PATCH ERROR]", msg)
    raise SystemExit(1)

def main() -> int:
    if not TARGET.exists():
        fail("Could not find core_v10\\mission_engine.py. Extract this ZIP into the FOXAI root.")

    text = TARGET.read_text(encoding="utf-8", errors="replace")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"mission_engine_backup_before_v10_3_{stamp}.py")
    shutil.copy2(TARGET, backup)
    print(f"[FOXAI v10.3] Backup created: {backup}")

    changed = False

    old = '''        memory_context = self.memory.build_context(
            professor_name=self.professor.name,
            model_name=self.model_name,
        )
'''

    new = '''        recall_phrases = [
            "what do you remember",
            "what confirmed memory",
            "what do we know",
            "what is stored",
            "what do you know about this mission",
        ]
        if any(phrase in user_text.lower() for phrase in recall_phrases) and hasattr(self.memory, "build_remembered_only_context"):
            memory_context = self.memory.build_remembered_only_context(
                professor_name=self.professor.name,
                model_name=self.model_name,
            )
        else:
            memory_context = self.memory.build_context(
                professor_name=self.professor.name,
                model_name=self.model_name,
            )
'''

    if old in text:
        text = text.replace(old, new)
        changed = True
        print("[FOXAI v10.3] Routed memory-recall questions to remembered-only context.")
    elif "build_remembered_only_context" in text:
        print("[FOXAI v10.3] Recall route already appears present.")
    else:
        fail("Could not locate build_context block in mission_engine.py.")

    # Add a stronger system prompt line if possible.
    old_prompt = '''            + "FOXAI is a portable Star Trek Engineering Console for Makers, Builders, and Explorers. "
            + "Always use supplied Mission Intelligence as authoritative project memory."
'''
    new_prompt = '''            + "FOXAI is a portable Star Trek Engineering Console for Makers, Builders, and Explorers. "
            + "Always use supplied Mission Intelligence as authoritative project memory. "
            + "When the user asks what you remember, answer only from the supplied confirmed memory. "
            + "Never infer mission details from the project name alone."
'''
    if old_prompt in text:
        text = text.replace(old_prompt, new_prompt)
        changed = True
        print("[FOXAI v10.3] Strengthened Mission Engine system prompt.")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("[FOXAI v10.3] Patch applied successfully.")
    else:
        print("[FOXAI v10.3] No changes needed.")

    print()
    print("Test:")
    print("1. Restart FOXAI.")
    print("2. Select FOXAI_Memory_Test if possible.")
    print("3. Ask: What confirmed memory do you have for this mission? Do not infer from the project name.")
    print()
    print("Expected:")
    print("- It should list only stored objectives/facts/decisions/tasks.")
    print("- It should NOT mention CAN, Ethernet, sensors, GPS, autonomous buses, or test routes unless stored.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
