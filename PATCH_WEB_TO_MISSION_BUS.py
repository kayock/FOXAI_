from __future__ import annotations

from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core" / "foxai_web.py"

def fail(msg: str) -> None:
    print("[FOXAI PHASE 3 PATCH ERROR]", msg)
    raise SystemExit(1)

def main() -> int:
    if not TARGET.exists():
        fail("Could not find core\\foxai_web.py. Extract this ZIP into the FOXAI root folder.")
    if not (ROOT / "core_v10" / "mission_bus.py").exists():
        fail("Could not find core_v10\\mission_bus.py. Install Phase 2 Mission Bus first.")

    text = TARGET.read_text(encoding="utf-8", errors="replace")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"foxai_web_backup_before_phase3_bus_{stamp}.py")
    shutil.copy2(TARGET, backup)
    print(f"[FOXAI PHASE 3] Backup created: {backup}")

    changed = False

    if "from core_v10.mission_bus import MissionBus" not in text:
        marker = "from urllib.parse import urlparse, parse_qs, unquote\n"
        if marker not in text:
            fail("Could not find import marker.")
        text = text.replace(marker, marker + "\nfrom core_v10.mission_bus import MissionBus\n")
        changed = True
        print("[FOXAI PHASE 3] Imported MissionBus.")

    if "mission_bus = MissionBus(ROOT)" not in text:
        marker = 'messages = [{"role":"system","content":PROFESSORS[active_professor_key]["prompt"]}]\n'
        if marker not in text:
            fail("Could not find messages global marker.")
        text = text.replace(marker, marker + "mission_bus = MissionBus(ROOT)\n")
        changed = True
        print("[FOXAI PHASE 3] Created MissionBus instance.")

    start = '''        if path == "/api/chat/send":
            text = (data.get("message") or "").strip()
            if not text: self._json({"ok":False,"message":"Empty message."}); return
            if not check_url(CHAT_HEALTH): self._json({"ok":False,"message":"Chat engine is offline. Start Chat Engine first."}); return
'''
    idx = text.find(start)
    if idx == -1:
        if "MissionBus.dispatch mission.ask" in text or 'mission_bus.dispatch("mission.ask"' in text:
            print("[FOXAI PHASE 3] Chat send route already appears patched.")
        else:
            fail("Could not locate /api/chat/send block start.")
    else:
        end_marker = '        self.send_response(404); self.end_headers()\n'
        end_idx = text.find(end_marker, idx)
        if end_idx == -1:
            fail("Could not locate /api/chat/send block end.")
        new_block = '''        if path == "/api/chat/send":
            text = (data.get("message") or "").strip()
            if not text:
                self._json({"ok": False, "message": "Empty message."})
                return
            if not check_url(CHAT_HEALTH):
                self._json({"ok": False, "message": "Chat engine is offline. Start Chat Engine first."})
                return

            # FOXAI Core v10 Phase 3:
            # All chat now routes through the Mission Bus / Kernel path.
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
                if active_project:
                    try:
                        save_mission_state("Agent response received through Mission Bus")
                    except Exception:
                        pass
                self._json({"ok": True, "answer": answer})
                return

            self._json({"ok": False, "message": result.get("message", "Mission Bus request failed.")})
            return

'''
        text = text[:idx] + new_block + text[end_idx:]
        changed = True
        print("[FOXAI PHASE 3] Rewired /api/chat/send to MissionBus.dispatch('mission.ask').")

    if 'if path == "/api/kernel/ping"' not in text:
        marker = '        if path == "/api/status": self._json(status()); return\n'
        if marker in text:
            text = text.replace(
                marker,
                marker + '        if path == "/api/kernel/ping": self._json(mission_bus.dispatch("ping")); return\n'
            )
            changed = True
            print("[FOXAI PHASE 3] Added /api/kernel/ping endpoint.")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("[FOXAI PHASE 3] Patch applied successfully.")
    else:
        print("[FOXAI PHASE 3] No changes needed.")

    print()
    print("Next:")
    print("1. Restart FOXAI.")
    print("2. Select a project.")
    print("3. Start Chat Engine.")
    print("4. Ask: What do you remember about this mission?")
    print("5. Check Projects/<project>/Memory/chat_transcript.md")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
