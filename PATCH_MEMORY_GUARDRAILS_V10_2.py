from __future__ import annotations

from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core_v10" / "memory_engine.py"

def fail(msg: str) -> None:
    print("[FOXAI v10.2 PATCH ERROR]", msg)
    raise SystemExit(1)

def main() -> int:
    if not TARGET.exists():
        fail("Could not find core_v10\\memory_engine.py. Extract this ZIP into the FOXAI root.")

    text = TARGET.read_text(encoding="utf-8", errors="replace")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"memory_engine_backup_before_v10_2_{stamp}.py")
    shutil.copy2(TARGET, backup)
    print(f"[FOXAI v10.2] Backup created: {backup}")

    changed = False

    if "def build_remembered_only_context" not in text:
        marker = "    def build_context(self, professor_name: str, model_name: str | None) -> str:\n"
        helper = r"""
    def build_remembered_only_context(self, professor_name: str, model_name: str | None) -> str:
        self.ensure()

        facts = read_json(self.memory_root / "facts.json", [])
        decisions = read_json(self.memory_root / "decisions.json", [])
        questions = read_json(self.memory_root / "questions.json", [])
        discoveries = read_json(self.memory_root / "discoveries.json", [])
        objectives = read_json(self.memory_root / "objectives.json", [])
        tasks = read_json(self.memory_root / "tasks.json", [])

        notes_path = self.project_path / "FOXAI_PROJECT_NOTES.md"
        notes = notes_path.read_text(encoding="utf-8", errors="replace").strip() if notes_path.exists() else ""

        def lines(title: str, items: list) -> list[str]:
            out = [f"\n{title}:"]
            if not items:
                out.append("- None stored.")
                return out
            for item in items[-12:]:
                if isinstance(item, dict):
                    out.append(f"- {item.get('text', '')}")
                else:
                    out.append(f"- {item}")
            return out

        parts = []
        parts.append("STRICT MISSION MEMORY REPORT")
        parts.append(f"Project: {self.project_path.name}")
        parts.append(f"Professor: {professor_name}")
        parts.append(f"Model: {model_name or 'None'}")
        parts.append("\nPurpose: Answer only from stored mission memory.")

        parts.extend(lines("CONFIRMED OBJECTIVES", objectives))
        parts.extend(lines("CONFIRMED FACTS", facts))
        parts.extend(lines("CONFIRMED DECISIONS", decisions))
        parts.extend(lines("CONFIRMED DISCOVERIES", discoveries))
        parts.extend(lines("CONFIRMED OPEN QUESTIONS", questions))
        parts.extend(lines("CONFIRMED TASKS", tasks))

        if notes:
            parts.append("\nPROJECT NOTES:")
            parts.append(notes[-2000:])
        else:
            parts.append("\nPROJECT NOTES:")
            parts.append("- None stored.")

        parts.append("\nUNKNOWN BY DEFAULT:")
        parts.append("- Any schedule not listed above is unknown.")
        parts.append("- Any hardware, sensors, GPS, routes, diagnostics, payloads, tests, or results not listed above are unknown.")
        parts.append("- Any installation status not listed above is unknown.")
        parts.append("- Do not infer meaning from the project name alone.")

        parts.append("\nRESPONSE RULES:")
        parts.append("- If asked what you remember, list only the CONFIRMED sections and project notes.")
        parts.append("- Do not add fictional objectives, hardware, routes, schedules, diagnostics, or test results.")
        parts.append("- If there is little memory, say the stored memory is sparse.")
        parts.append("- Put recommendations under a separate heading: Suggested Next Steps.")
        return "\n".join(parts)

"""
        if marker not in text:
            fail("Could not find build_context marker.")
        text = text.replace(marker, helper + marker)
        changed = True
        print("[FOXAI v10.2] Added strict remembered-only context builder.")

    if "Do not infer meaning from the project name alone." not in text:
        marker = '        parts.append("- Novel Forge is reserved but not installed unless Mission Intelligence explicitly says it is installed.")\n'
        add = (
            marker +
            '        parts.append("- Do not infer meaning from the project name alone.")\n'
            '        parts.append("- Do not turn software terms like bus, kernel, route, engine, or payload into physical vehicle/hardware claims unless stored memory explicitly says so.")\n'
            '        parts.append("- Unknown by default: schedules, locations, sensors, GPS, test routes, diagnostics, failures, and success criteria.")\n'
        )
        if marker in text:
            text = text.replace(marker, add)
            changed = True
            print("[FOXAI v10.2] Added unknown-by-default guardrails to normal context.")
        else:
            print("[FOXAI v10.2] Normal grounding marker not found; skipped.")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("[FOXAI v10.2] Patch applied successfully.")
    else:
        print("[FOXAI v10.2] No changes needed.")

    print()
    print("Next:")
    print("Run TEST_MEMORY_GUARDRAILS.bat")
    print("Then restart FOXAI and create/use project FOXAI_Memory_Test.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
