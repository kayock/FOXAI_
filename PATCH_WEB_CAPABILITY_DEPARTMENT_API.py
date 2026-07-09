from __future__ import annotations

from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core" / "foxai_web.py"

def fail(msg: str) -> None:
    print("[FOXAI WEB CAPABILITY API PATCH ERROR]", msg)
    raise SystemExit(1)

def main() -> int:
    if not TARGET.exists():
        fail("Could not find core\\foxai_web.py. Extract this ZIP into the FOXAI root.")

    if not (ROOT / "core_v10" / "mission_bus.py").exists():
        fail("Missing core_v10\\mission_bus.py. Install Mission Bus / Capability Manager first.")

    text = TARGET.read_text(encoding="utf-8", errors="replace")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"foxai_web_backup_before_capability_api_{stamp}.py")
    shutil.copy2(TARGET, backup)
    print(f"[FOXAI PATCH] Backup created: {backup}")

    changed = False

    if "from core_v10.mission_bus import MissionBus" not in text:
        marker = "from urllib.parse import urlparse, parse_qs, unquote\n"
        if marker not in text:
            fail("Could not find import marker.")
        text = text.replace(marker, marker + "\nfrom core_v10.mission_bus import MissionBus\n")
        changed = True
        print("[FOXAI PATCH] Added MissionBus import.")

    if "mission_bus=MissionBus(ROOT)" not in text and "mission_bus = MissionBus(ROOT)" not in text:
        marker = "messages=[{'role':'system','content':PROF[prof][3]}]\n"
        if marker not in text:
            fail("Could not find messages global marker.")
        text = text.replace(marker, marker + "mission_bus=MissionBus(ROOT)\n")
        changed = True
        print("[FOXAI PATCH] Added mission_bus global instance.")

    if "def department_registry()" not in text:
        marker = "def status():\n"
        helper = '''def department_registry():
    return {
        'ok': True,
        'departments': [
            {'key':'dashboard','name':'Dashboard','icon':'🏠','description':'Mission overview and system status.'},
            {'key':'projects','name':'Projects','icon':'🗂','description':'Local project workspaces.'},
            {'key':'memory','name':'Mission Memory','icon':'🧭','description':'Structured project memory and timeline.'},
            {'key':'mission','name':'Mission Console','icon':'💬','description':'Talk to active professors through local models.'},
            {'key':'academy','name':'Academy','icon':'🧠','description':'Professor profiles and expertise routing.'},
            {'key':'creative','name':'Creative Studio','icon':'🎨','description':'Image, story, media, and creative tools.'},
            {'key':'library','name':'Iron Library','icon':'📚','description':'Local documents, manuals, prompts, and research.'},
            {'key':'hangar','name':'Hangar Bay','icon':'🛫','description':'Portable apps and specialist capabilities.'},
            {'key':'repair','name':'Repair Bay','icon':'🛠','description':'Diagnostics, repair tools, and reports.'},
            {'key':'logs','name':'Logs','icon':'📜','description':'System logs and mission archive.'},
            {'key':'settings','name':'Settings','icon':'⚙','description':'Paths, configuration, and integration settings.'},
        ]
    }

'''
        if marker not in text:
            fail("Could not find status() marker.")
        text = text.replace(marker, helper + marker)
        changed = True
        print("[FOXAI PATCH] Added department_registry().")

    if "path=='/api/capabilities/list'" not in text:
        marker = "        if path=='/api/status': self.js(status()); return\n"
        if marker not in text:
            fail("Could not find /api/status GET marker.")
        routes = (
            "        if path=='/api/capabilities/list': self.js(mission_bus.dispatch('capabilities.list')); return\n"
            "        if path=='/api/capabilities/health': self.js(mission_bus.dispatch('capabilities.health', {'key': qs.get('key',[''])[0] or None})); return\n"
            "        if path=='/api/capabilities/find': self.js(mission_bus.dispatch('capabilities.find', {'capability': qs.get('capability',[''])[0]})); return\n"
            "        if path=='/api/departments/list': self.js(department_registry()); return\n"
        )
        text = text.replace(marker, routes + marker)
        changed = True
        print("[FOXAI PATCH] Added capability/department GET API routes.")

    if "path=='/api/capabilities/launch'" not in text:
        marker = "        if path=='/api/memory/save': self.js(save_state('Mission state manually saved')); return\n"
        if marker not in text:
            fail("Could not find /api/memory/save POST marker.")
        route = "        if path=='/api/capabilities/launch': self.js(mission_bus.dispatch('capabilities.launch', {'key': d.get('key','')})); return\n"
        text = text.replace(marker, route + marker)
        changed = True
        print("[FOXAI PATCH] Added capability launch POST API route.")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("[FOXAI PATCH] Patch applied successfully.")
    else:
        print("[FOXAI PATCH] No changes needed.")

    print()
    print("Test after restarting FOXAI:")
    print("http://127.0.0.1:8765/api/capabilities/list")
    print("http://127.0.0.1:8765/api/departments/list")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
