from __future__ import annotations

from pathlib import Path
import shutil
import datetime
import re

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core_v10" / "memory_engine.py"

def fail(msg: str) -> None:
    print("[FOXAI v10.1 PATCH ERROR]", msg)
    raise SystemExit(1)

def main() -> int:
    if not TARGET.exists():
        fail("Could not find core_v10\\memory_engine.py. Extract this ZIP into the FOXAI root.")

    text = TARGET.read_text(encoding="utf-8", errors="replace")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"memory_engine_backup_before_v10_1_{stamp}.py")
    shutil.copy2(TARGET, backup)
    print(f"[FOXAI v10.1] Backup created: {backup}")

    changed = False

    # Add confidence fields to new memory items.
    old = 'items.append({"time": now(), "text": value, "done": False if kind == "task" else None})'
    new = 'items.append({"time": now(), "text": value, "done": False if kind == "task" else None, "confidence": "confirmed", "source": "operator"})'
    if old in text:
        text = text.replace(old, new)
        changed = True
        print("[FOXAI v10.1] Added confidence/source to new memory items.")
    else:
        print("[FOXAI v10.1] Confidence/source memory item patch skipped or already applied.")

    # Replace build_context instruction with grounded rules.
    old_instruction = (
        '        parts.append(\n'
        '            "\\nInstruction: This is real disk-backed memory supplied by FOXAI. Use it directly. "\n'
        '            "Do not claim you lack memory if the answer is present here."\n'
        '        )\n'
    )

    grounded_instruction = (
        '        parts.append("\\nGROUNDING RULES:")\n'
        '        parts.append("- Treat Mission Intelligence as the only authoritative project memory.")\n'
        '        parts.append("- Answer from stored memory only when asked what you remember about the mission.")\n'
        '        parts.append("- Do not invent schedules, diagnostics, hardware, tests, results, objectives, or decisions.")\n'
        '        parts.append("- If a detail is not present in Mission Intelligence, say: I do not know that yet from stored mission memory.")\n'
        '        parts.append("- Clearly separate CONFIRMED memory from suggestions or next-step recommendations.")\n'
        '        parts.append("- Novel Forge is reserved but not installed unless Mission Intelligence explicitly says it is installed.")\n'
        '        parts.append("- When suggesting next steps, label them as Suggested Next Steps, not remembered facts.")\n'
    )

    if old_instruction in text:
        text = text.replace(old_instruction, grounded_instruction)
        changed = True
        print("[FOXAI v10.1] Replaced general instruction with grounded memory rules.")
    elif "GROUNDING RULES:" in text:
        print("[FOXAI v10.1] Grounding rules already present.")
    else:
        print("[FOXAI v10.1] Could not find exact old instruction; appending grounding rules before return.")
        marker = '        return "\\n".join(parts)\n'
        if marker in text and "GROUNDING RULES:" not in text:
            text = text.replace(marker, grounded_instruction + marker)
            changed = True
            print("[FOXAI v10.1] Appended grounding rules.")

    # Add a summary helper method if missing.
    if "def memory_snapshot" not in text:
        insert_marker = "    def build_context(self, professor_name: str, model_name: str | None) -> str:\n"
        helper = r'''
    def memory_snapshot(self) -> dict:
        self.ensure()
        return {
            "project": self.project_path.name,
            "facts": read_json(self.memory_root / "facts.json", []),
            "decisions": read_json(self.memory_root / "decisions.json", []),
            "questions": read_json(self.memory_root / "questions.json", []),
            "discoveries": read_json(self.memory_root / "discoveries.json", []),
            "objectives": read_json(self.memory_root / "objectives.json", []),
            "tasks": read_json(self.memory_root / "tasks.json", []),
            "memory_root": str(self.memory_root),
        }

'''
        if insert_marker in text:
            text = text.replace(insert_marker, helper + insert_marker)
            changed = True
            print("[FOXAI v10.1] Added memory_snapshot helper.")
        else:
            print("[FOXAI v10.1] Could not add memory_snapshot helper.")

    # Ensure output labels emphasize authoritative sections.
    replacements = {
        'parts.append("\\nObjectives:")': 'parts.append("\\nCONFIRMED OBJECTIVES:")',
        'parts.append("\\nOpen Tasks:")': 'parts.append("\\nCONFIRMED OPEN TASKS:")',
        'parts.append("\\nKnown Facts:")': 'parts.append("\\nCONFIRMED FACTS:")',
        'parts.append("\\nDecisions:")': 'parts.append("\\nCONFIRMED DECISIONS:")',
        'parts.append("\\nDiscoveries:")': 'parts.append("\\nCONFIRMED DISCOVERIES:")',
        'parts.append("\\nOpen Questions:")': 'parts.append("\\nCONFIRMED OPEN QUESTIONS:")',
    }
    for a, b in replacements.items():
        if a in text:
            text = text.replace(a, b)
            changed = True
    print("[FOXAI v10.1] Section labels grounded.")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("[FOXAI v10.1] Patch applied successfully.")
    else:
        print("[FOXAI v10.1] No changes needed.")

    print()
    print("Test:")
    print("1. Restart FOXAI.")
    print("2. Select FOXAI_Mission_Bus_Test.")
    print("3. Ask: What do you remember about this mission?")
    print("Expected:")
    print("- It should only mention stored memory.")
    print("- It should not invent 10:00 UTC, sensors, diagnostics, or payload tests.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
