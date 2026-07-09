from __future__ import annotations

from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core" / "foxai_web.py"

def fail(msg: str) -> None:
    print("[FOXAI PATCH ERROR]", msg)
    raise SystemExit(1)

def main() -> int:
    if not TARGET.exists():
        fail(f"Could not find {TARGET}. Put this patch in the FOXAI root beside START_FOXAI_WEB.bat.")

    text = TARGET.read_text(encoding="utf-8", errors="replace")

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"foxai_web_backup_before_v9_2_{stamp}.py")
    shutil.copy2(TARGET, backup)
    print(f"[FOXAI PATCH] Backup created: {backup}")

    changed = False

    if '"novelforge"' not in text:
        marker = '''    "deadpool": {"name":"Professor Deadpool","college":"Meta Creativity","motto":"The best stories know they're being told.","prompt":"You are Professor Deadpool inside FOXAI. Specialize in creative brainstorming, comedy, meta commentary, comics, characters, and bold ideas while still being useful."},
}'''
        replacement = '''    "deadpool": {"name":"Professor Deadpool","college":"Meta Creativity","motto":"The best stories know they're being told.","prompt":"You are Professor Deadpool inside FOXAI. Specialize in creative brainstorming, comedy, meta commentary, comics, characters, and bold ideas while still being useful."},
    "novelforge": {"name":"Professor Novel Forge","college":"Creative Writing","motto":"Every world deserves to remember its own history.","prompt":"You are Professor Novel Forge inside FOXAI. Specialize in long-form storytelling, D&D dungeon mastering, choose-your-own-adventure sessions, worldbuilding, character continuity, campaign memory, comics, dialogue, lore, plot structure, and creative writing. Maintain continuity carefully and ask vivid but useful follow-up questions when needed."},
}'''
        if marker not in text:
            fail("Could not locate PROFESSORS deadpool block. Patch cannot safely add Novel Forge.")
        text = text.replace(marker, replacement)
        changed = True
        print("[FOXAI PATCH] Added Professor Novel Forge.")
    else:
        print("[FOXAI PATCH] Professor Novel Forge already present.")

    if "def build_mission_intelligence_context" not in text:
        marker = '''def mission_current() -> dict:
    if not active_project:
        return {"ok": False, "message": "No active project selected."}
    mission = ensure_mission(active_project)
    timeline = read_json(project_file(active_project, "timeline.json"), [])
    tasks = tasks_for(active_project)
    return {"ok": True, "mission": mission, "timeline": timeline, "tasks": tasks}
'''
        addition = marker + r'''
def build_mission_intelligence_context() -> str:
    if not active_project:
        return ""

    try:
        mission = ensure_mission(active_project)
        tasks = tasks_for(active_project)
        timeline = read_json(project_file(active_project, "timeline.json"), [])
        note_path = project_file(active_project, mission.get("notes_file", "FOXAI_PROJECT_NOTES.md"))
        notes = ""
        if note_path and note_path.exists():
            notes = note_path.read_text(encoding="utf-8", errors="replace").strip()

        open_tasks = [t.get("text", "") for t in tasks if not t.get("done")]
        done_tasks = [t.get("text", "") for t in tasks if t.get("done")]
        recent_events = timeline[-12:]

        parts = []
        parts.append("MISSION INTELLIGENCE")
        parts.append(f"Current Project: {mission.get('project', active_project)}")
        parts.append(f"Current Task: {mission.get('current_task', 'None')}")
        parts.append(f"Active Professor: {mission.get('active_professor_name', active_professor()['name'])}")
        parts.append(f"Active Model: {mission.get('active_model_name', 'None')}")
        parts.append(f"Last Opened: {mission.get('last_opened', 'Unknown')}")

        if open_tasks:
            parts.append("\\nOpen Tasks:")
            for task in open_tasks[:12]:
                parts.append(f"- {task}")

        if done_tasks:
            parts.append("\\nCompleted Tasks:")
            for task in done_tasks[-8:]:
                parts.append(f"- {task}")

        if recent_events:
            parts.append("\\nRecent Timeline:")
            for event in recent_events:
                parts.append(f"- {event.get('time', '')}: {event.get('event', '')}")

        if notes:
            trimmed = notes[-3000:]
            parts.append("\\nProject Notes:")
            parts.append(trimmed)

        parts.append("\\nInstruction: Use this Mission Intelligence as real project memory. Do not claim you cannot remember this project if the answer is present here. If information is missing, say what is missing.")
        return "\\n".join(parts).strip()
    except Exception as exc:
        return f"MISSION INTELLIGENCE ERROR: {exc}"
'''
        if marker not in text:
            fail("Could not locate mission_current() block. Patch cannot safely add Mission Intelligence.")
        text = text.replace(marker, addition)
        changed = True
        print("[FOXAI PATCH] Added Mission Intelligence context builder.")
    else:
        print("[FOXAI PATCH] Mission Intelligence builder already present.")

    old = '''            messages.append({"role":"user","content":text})
            if active_project: add_timeline(active_project, "Message sent to Mission Console")
            try:
                result = post_json(CHAT_API, {"model":"local-model","messages":messages,"temperature":0.7,"max_tokens":768,"stream":False}, 300)
'''
    new = '''            memory_context = build_mission_intelligence_context()
            if memory_context:
                augmented_text = memory_context + "\\n\\nUSER REQUEST:\\n" + text
            else:
                augmented_text = text
            messages.append({"role":"user","content":augmented_text})
            if active_project: add_timeline(active_project, "Message sent to Mission Console with Mission Intelligence")
            try:
                result = post_json(CHAT_API, {"model":"local-model","messages":messages,"temperature":0.7,"max_tokens":768,"stream":False}, 300)
'''
    if old in text and "Message sent to Mission Console with Mission Intelligence" not in text:
        text = text.replace(old, new)
        changed = True
        print("[FOXAI PATCH] Wired Mission Intelligence into chat prompts.")
    elif "Message sent to Mission Console with Mission Intelligence" in text:
        print("[FOXAI PATCH] Chat prompt injection already present.")
    else:
        fail("Could not locate chat/send injection point. Patch cannot safely wire memory into prompts.")

    old = '''    ensure_mission(active_project)
    add_timeline(active_project, "Project created")
    save_mission_state("Project selected")
'''
    new = '''    ensure_mission(active_project)
    if not tasks_for(active_project):
        save_tasks(active_project, [
            {"text":"Define project goal", "done":False, "created":now()},
            {"text":"Capture current notes", "done":False, "created":now()},
            {"text":"Decide next action", "done":False, "created":now()}
        ])
    add_timeline(active_project, "Project created")
    save_mission_state("Project selected")
'''
    if old in text and "Define project goal" not in text:
        text = text.replace(old, new)
        changed = True
        print("[FOXAI PATCH] Added starter tasks for new projects.")
    else:
        print("[FOXAI PATCH] Starter task patch skipped/already present.")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("[FOXAI PATCH] Patch applied successfully.")
    else:
        print("[FOXAI PATCH] No changes needed.")

    print()
    print("Next:")
    print("1. Restart FOXAI.")
    print("2. Select a project.")
    print("3. Open Academy and activate Professor Novel Forge.")
    print("4. Ask: What do you remember about this mission?")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
