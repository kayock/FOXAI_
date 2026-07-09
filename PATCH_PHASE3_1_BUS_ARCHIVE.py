
from __future__ import annotations

from pathlib import Path
import shutil
import datetime
import re

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core" / "foxai_web.py"

def fail(msg: str) -> None:
    print("[FOXAI PHASE 3.1 ERROR]", msg)
    raise SystemExit(1)

def main() -> int:
    if not TARGET.exists():
        fail("Could not find core\\foxai_web.py. Extract this ZIP into the FOXAI root folder.")
    if not (ROOT / "core_v10" / "mission_bus.py").exists():
        fail("Could not find core_v10\\mission_bus.py. Install Core v10 Phase 2 Mission Bus first.")

    text = TARGET.read_text(encoding="utf-8", errors="replace")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"foxai_web_backup_before_phase3_1_{stamp}.py")
    shutil.copy2(TARGET, backup)
    print(f"[FOXAI 3.1] Backup created: {backup}")

    changed = False

    if "from core_v10.mission_bus import MissionBus" not in text:
        marker = "from urllib.parse import urlparse, parse_qs, unquote\n"
        if marker not in text:
            fail("Import marker not found.")
        text = text.replace(marker, marker + "\nfrom core_v10.mission_bus import MissionBus\n")
        changed = True
        print("[FOXAI 3.1] Imported MissionBus.")

    if "mission_bus = MissionBus(ROOT)" not in text:
        marker = 'messages = [{"role":"system","content":PROFESSORS[active_professor_key]["prompt"]}]\n'
        if marker not in text:
            fail("messages global marker not found.")
        text = text.replace(marker, marker + "mission_bus = MissionBus(ROOT)\n")
        changed = True
        print("[FOXAI 3.1] Created MissionBus instance.")

    if "def archive_chat_legacy" not in text:
        helper_marker = "def log(message: str) -> None:\n"
        helper = """
def archive_chat_legacy(project: str, professor: str, model_name: str | None, user_text: str, answer: str) -> None:
    try:
        year = datetime.now().strftime("%Y")
        archive_dir = ROOT / "Mission Archive" / "Chats" / year
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_project = "".join(c for c in (project or "Default_Mission") if c.isalnum() or c in " _.-").strip().replace(" ", "_")
        path = archive_dir / f"{stamp}_{safe_project}.md"
        path.write_text(
            "# FOXAI Mission Chat Archive\\\\n\\\\n"
            f"Time: {datetime.now().isoformat(timespec='seconds')}\\\\n\\\\n"
            f"Project: {project}\\\\n\\\\n"
            f"Professor: {professor}\\\\n\\\\n"
            f"Model: {model_name or 'None'}\\\\n\\\\n"
            "## Eric\\\\n\\\\n"
            f"{user_text}\\\\n\\\\n"
            "## Response\\\\n\\\\n"
            f"{answer}\\\\n",
            encoding="utf-8"
        )
    except Exception as exc:
        try:
            log(f"Legacy archive failed: {exc}")
        except Exception:
            pass

"""
        if helper_marker not in text:
            fail("Could not find helper insertion marker.")
        text = text.replace(helper_marker, helper + helper_marker)
        changed = True
        print("[FOXAI 3.1] Added legacy chat archive helper.")

    pattern = re.compile(
        r'        if path == "/api/chat/send":\n'
        r'.*?'
        r'        self\.send_response\(404\); self\.end_headers\(\)\n',
        re.DOTALL
    )

    new_block = """        if path == "/api/chat/send":
            text = (data.get("message") or "").strip()
            if not text:
                self._json({"ok": False, "message": "Empty message."})
                return
            if not check_url(CHAT_HEALTH):
                self._json({"ok": False, "message": "Chat engine is offline. Start Chat Engine first."})
                return

            project = active_project or "Default_Mission"
            professor = active_professor_key or "fox"
            model_name = Path(chat_model).name if chat_model else None

            result = mission_bus.dispatch("mission.ask", {
                "project": project,
                "professor": professor,
                "model_name": model_name,
                "text": text
            })

            if result.get("ok"):
                answer = result.get("answer", "")
                messages.append({"role": "user", "content": text})
                messages.append({"role": "assistant", "content": answer})
                archive_chat_legacy(project, professor, model_name, text, answer)

                if active_project:
                    try:
                        save_mission_state("Agent response received through Mission Bus")
                    except Exception:
                        pass

                self._json({"ok": True, "answer": answer})
                return

            self._json({"ok": False, "message": result.get("message", "Mission Bus request failed.")})
            return

        self.send_response(404); self.end_headers()
"""

    matches = list(pattern.finditer(text))
    if not matches:
        if 'mission_bus.dispatch("mission.ask"' in text and "archive_chat_legacy(project" in text:
            print("[FOXAI 3.1] Chat route already appears hardened.")
        else:
            fail("Could not locate /api/chat/send route for replacement.")
    else:
        match = matches[-1]
        text = text[:match.start()] + new_block + text[match.end():]
        changed = True
        print("[FOXAI 3.1] Replaced /api/chat/send with hardened Mission Bus route.")

    if 'if path == "/api/kernel/ping"' not in text:
        marker = '        if path == "/api/status": self._json(status()); return\n'
        if marker in text:
            text = text.replace(marker, marker + '        if path == "/api/kernel/ping": self._json(mission_bus.dispatch("ping")); return\n')
            changed = True
            print("[FOXAI 3.1] Added kernel ping endpoint.")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("[FOXAI 3.1] Patch applied successfully.")
    else:
        print("[FOXAI 3.1] No changes needed.")

    print()
    print("Next:")
    print("1. Restart FOXAI.")
    print("2. Select project FOXAI_Mission_Bus_Test.")
    print("3. Start Chat Engine.")
    print("4. Ask: What do you remember about this mission?")
    print("5. Check Projects/<project>/Memory/chat_transcript.md")
    print("6. Check Mission Archive/Chats/<year>/")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
