from __future__ import annotations

from pathlib import Path
import shutil
import datetime
import re

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core" / "foxai_web.py"

IMPORT_MARKER = 'from urllib.parse import urlparse, parse_qs, unquote\n'
MISSION_IMPORT = '\nfrom core_v10.mission_bus import MissionBus\n'
MESSAGES_MARKER = "messages=[{'role':'system','content':PROF[prof][3]}]\n"
BUS_INSTANCE = 'mission_bus=MissionBus(ROOT)\n'
LOG_MARKER = 'def log(s): LOGS.mkdir(exist_ok=True); LOG.open(\'a\',encoding=\'utf-8\').write(f"[{datetime.now():%F %T}] {s}\\n")\n'
HELPER_CODE = 'def archive_chat_legacy(project, professor, model_name, user_text, answer):\n    try:\n        n=datetime.now()\n        folder=ROOT/\'Mission Archive\'/\'Chats\'/str(n.year)/f"{n.month:02d}"/f"{n.day:02d}"\n        folder.mkdir(parents=True,exist_ok=True)\n        safe=\'\'.join(c for c in (project or \'Default_Mission\') if c.isalnum() or c in \' _.-\').strip().replace(\' \',\'_\') or \'Default_Mission\'\n        path=folder/f"{n:%H-%M-%S}_{safe}.md"\n        path.write_text(\n            "# FoxAI Mission Log\\n\\n"\n            f"Saved: {n.isoformat(timespec=\'seconds\')}\\n\\n"\n            f"Project: {project}\\n\\n"\n            f"Professor: {professor}\\n\\n"\n            f"Model: {model_name or \'None\'}\\n\\n"\n            "## ERIC\\n\\n"\n            f"{user_text.strip()}\\n\\n"\n            "## AGENT\\n\\n"\n            f"{answer.strip()}\\n",\n            encoding=\'utf-8\'\n        )\n        return str(path)\n    except Exception as e:\n        try: log(f"Legacy archive failed: {e}")\n        except Exception: pass\n        return None\n\n'
NEW_CHAT_BLOCK = "        if path=='/api/chat/send':\n            text=(d.get('message') or '').strip()\n            if not text:\n                self.js({'ok':False,'message':'Empty message.'}); return\n            if not check(CHAT_HEALTH):\n                self.js({'ok':False,'message':'Chat engine is offline. Start Chat Engine first.'}); return\n\n            # FOXAI actual-core bus wiring:\n            # Route chat through core_v10 MissionBus instead of direct CHAT_API.\n            project=active_project or 'Default_Mission'\n            professor=prof or 'fox'\n            model_name=Path(chat_model).name if chat_model else None\n\n            result=mission_bus.dispatch('mission.ask',{\n                'project':project,\n                'professor':professor,\n                'model_name':model_name,\n                'text':text\n            })\n\n            if result.get('ok'):\n                ans=result.get('answer','')\n                messages.append({'role':'user','content':text})\n                messages.append({'role':'assistant','content':ans})\n                archive_chat_legacy(project, professor, model_name, text, ans)\n                if active_project:\n                    try: save_state('Agent response received through Mission Bus')\n                    except Exception: pass\n                self.js({'ok':True,'answer':ans}); return\n\n            self.js({'ok':False,'message':result.get('message','Mission Bus request failed.')}); return\n        self.send_response(404); self.end_headers()\n"

def fail(msg: str) -> None:
    print("[FOXAI ACTUAL CORE PATCH ERROR]", msg)
    raise SystemExit(1)

def main() -> int:
    if not TARGET.exists():
        fail("Could not find core\\foxai_web.py. Extract this ZIP into the FOXAI root.")
    if not (ROOT / "core_v10" / "mission_bus.py").exists():
        fail("Could not find core_v10\\mission_bus.py. Install/extract FOXAI Core v10 Phase 2 first.")

    text = TARGET.read_text(encoding="utf-8", errors="replace")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"foxai_web_backup_actual_core_before_bus_{stamp}.py")
    shutil.copy2(TARGET, backup)
    print(f"[FOXAI PATCH] Backup created: {backup}")

    changed = False

    if "from core_v10.mission_bus import MissionBus" not in text:
        if IMPORT_MARKER not in text:
            fail("Could not find urllib import marker.")
        text = text.replace(IMPORT_MARKER, IMPORT_MARKER + MISSION_IMPORT)
        changed = True
        print("[FOXAI PATCH] Added MissionBus import.")

    if "mission_bus=MissionBus(ROOT)" not in text and "mission_bus = MissionBus(ROOT)" not in text:
        if MESSAGES_MARKER not in text:
            fail("Could not find messages global marker.")
        text = text.replace(MESSAGES_MARKER, MESSAGES_MARKER + BUS_INSTANCE)
        changed = True
        print("[FOXAI PATCH] Added mission_bus instance.")

    if "def archive_chat_legacy" not in text:
        if LOG_MARKER not in text:
            fail("Could not find log() marker for archive helper.")
        text = text.replace(LOG_MARKER, HELPER_CODE + LOG_MARKER)
        changed = True
        print("[FOXAI PATCH] Added legacy archive helper.")

    pattern = re.compile(
        r"        if path=='/api/chat/send':\n"
        r".*?"
        r"        self\.send_response\(404\); self\.end_headers\(\)\n",
        re.DOTALL
    )

    matches = list(pattern.finditer(text))
    if not matches:
        if "mission_bus.dispatch('mission.ask'" in text:
            print("[FOXAI PATCH] /api/chat/send already appears wired to MissionBus.")
        else:
            fail("Could not locate compact /api/chat/send route.")
    else:
        m = matches[-1]
        text = text[:m.start()] + NEW_CHAT_BLOCK + text[m.end():]
        changed = True
        print("[FOXAI PATCH] Rewired /api/chat/send to MissionBus.")

    if "path=='/api/kernel/ping'" not in text:
        marker = "        if path=='/api/status': self.js(status()); return\n"
        if marker in text:
            text = text.replace(marker, marker + "        if path=='/api/kernel/ping': self.js(mission_bus.dispatch('ping')); return\n")
            changed = True
            print("[FOXAI PATCH] Added /api/kernel/ping.")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("[FOXAI PATCH] Patch applied successfully.")
    else:
        print("[FOXAI PATCH] No changes needed.")

    print()
    print("Test:")
    print("1. Restart FOXAI.")
    print("2. Select FOXAI_Mission_Bus_Test.")
    print("3. Start Chat Engine.")
    print("4. Ask: What do you remember about this mission?")
    print("5. Check:")
    print("   Projects/<project>/Memory/chat_transcript.md")
    print("   Mission Archive/Chats/<year>/<month>/<day>/")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
