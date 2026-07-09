from __future__ import annotations

from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core" / "foxai_web.py"

def fail(msg: str) -> None:
    print("[FOXAI v10 PATCH ERROR]", msg)
    raise SystemExit(1)

def main() -> int:
    if not TARGET.exists():
        fail(f"Could not find {TARGET}. Put this patch in the FOXAI root beside START_FOXAI_WEB.bat.")

    text = TARGET.read_text(encoding="utf-8", errors="replace")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"foxai_web_backup_before_v10_{stamp}.py")
    shutil.copy2(TARGET, backup)
    print(f"[FOXAI v10] Backup created: {backup}")

    changed = False

    if '"novelforge"' not in text:
        marker = '''    "deadpool": {"name":"Professor Deadpool","college":"Meta Creativity","motto":"The best stories know they're being told.","prompt":"You are Professor Deadpool inside FOXAI. Specialize in creative brainstorming, comedy, meta commentary, comics, characters, and bold ideas while still being useful."},
}'''
        replacement = '''    "deadpool": {"name":"Professor Deadpool","college":"Meta Creativity","motto":"The best stories know they're being told.","prompt":"You are Professor Deadpool inside FOXAI. Specialize in creative brainstorming, comedy, meta commentary, comics, characters, and bold ideas while still being useful."},
    "novelforge": {"name":"Professor Novel Forge","college":"Creative Writing","motto":"Every world deserves to remember its own history.","prompt":"You are Professor Novel Forge inside FOXAI. Specialize in Dungeons & Dragons, choose-your-own-adventure stories, long-form fiction, comics, worldbuilding, character continuity, campaign memory, lore, plot structure, and creative writing. Preserve continuity using Mission Intelligence when provided."},
}'''
        if marker in text:
            text = text.replace(marker, replacement)
            changed = True
            print("[FOXAI v10] Added Professor Novel Forge.")
        else:
            print("[FOXAI v10] Novel Forge marker not found; skipping professor insertion.")
    else:
        print("[FOXAI v10] Professor Novel Forge already present.")

    if "def memory_root_for_project" not in text:
        insert_after = '''def mission_current() -> dict:
    if not active_project:
        return {"ok": False, "message": "No active project selected."}
    mission = ensure_mission(active_project)
    timeline = read_json(project_file(active_project, "timeline.json"), [])
    tasks = tasks_for(active_project)
    return {"ok": True, "mission": mission, "timeline": timeline, "tasks": tasks}
'''
        memory_engine = insert_after + r'''
def memory_root_for_project(project: str) -> Path | None:
    p = safe_project_path(project)
    if not p:
        return None
    memory = p / "Memory"
    memory.mkdir(parents=True, exist_ok=True)
    return memory

def memory_json(project: str, name: str, default):
    memory = memory_root_for_project(project)
    if not memory:
        return default
    return read_json(memory / name, default)

def memory_write_json(project: str, name: str, data) -> None:
    memory = memory_root_for_project(project)
    if not memory:
        return
    write_json(memory / name, data)

def memory_append_md(project: str, name: str, text: str) -> None:
    memory = memory_root_for_project(project)
    if not memory:
        return
    path = memory / name
    with path.open("a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\\n\\n")

def ensure_memory_files(project: str) -> None:
    memory = memory_root_for_project(project)
    if not memory:
        return

    defaults = {
        "facts.json": [],
        "decisions.json": [],
        "questions.json": [],
        "discoveries.json": [],
        "objectives.json": [],
    }
    for filename, default in defaults.items():
        path = memory / filename
        if not path.exists():
            write_json(path, default)

    mission_md = memory / "mission.md"
    if not mission_md.exists():
        mission_md.write_text(
            f"# Mission Intelligence: {project}\\n\\n"
            f"Created: {now()}\\n\\n"
            "## Mission Purpose\\n\\n"
            "Describe what this project is trying to accomplish.\\n\\n",
            encoding="utf-8"
        )

    session_log = memory / "session_log.md"
    if not session_log.exists():
        session_log.write_text(f"# Session Log: {project}\\n\\n", encoding="utf-8")

def memory_add_event(project: str, event: str) -> None:
    ensure_memory_files(project)
    memory_append_md(project, "session_log.md", f"## {now()}\\n\\n{event}")

def memory_record_chat(project: str, speaker: str, content: str) -> None:
    ensure_memory_files(project)
    safe = content.strip()
    if len(safe) > 4000:
        safe = safe[:4000] + "\\n...[trimmed]"
    memory_append_md(project, "chat_transcript.md", f"### {now()} — {speaker}\\n\\n{safe}")

def build_mission_intelligence_context() -> str:
    if not active_project:
        return ""

    try:
        ensure_memory_files(active_project)
        mission = ensure_mission(active_project)
        timeline = read_json(project_file(active_project, "timeline.json"), [])
        tasks = tasks_for(active_project)

        memory = memory_root_for_project(active_project)
        mission_md = ""
        session_log = ""
        notes = ""

        if memory:
            p = memory / "mission.md"
            if p.exists():
                mission_md = p.read_text(encoding="utf-8", errors="replace")[-3000:]
            p = memory / "session_log.md"
            if p.exists():
                session_log = p.read_text(encoding="utf-8", errors="replace")[-3000:]

        note_path = project_file(active_project, mission.get("notes_file", "FOXAI_PROJECT_NOTES.md"))
        if note_path and note_path.exists():
            notes = note_path.read_text(encoding="utf-8", errors="replace")[-3000:]

        facts = memory_json(active_project, "facts.json", [])
        decisions = memory_json(active_project, "decisions.json", [])
        discoveries = memory_json(active_project, "discoveries.json", [])
        questions = memory_json(active_project, "questions.json", [])
        objectives = memory_json(active_project, "objectives.json", [])

        open_tasks = [t.get("text", "") for t in tasks if not t.get("done")]
        done_tasks = [t.get("text", "") for t in tasks if t.get("done")]
        recent_events = timeline[-10:]

        parts = []
        parts.append("MISSION INTELLIGENCE v10")
        parts.append(f"Current Project: {mission.get('project', active_project)}")
        parts.append(f"Current Task: {mission.get('current_task', 'None')}")
        parts.append(f"Active Professor: {mission.get('active_professor_name', active_professor()['name'])}")
        parts.append(f"Active Model: {mission.get('active_model_name', 'None')}")
        parts.append(f"Last Opened: {mission.get('last_opened', 'Unknown')}")

        if objectives:
            parts.append("\\nObjectives:")
            for item in objectives[-8:]:
                parts.append(f"- {item.get('text', item) if isinstance(item, dict) else item}")

        if open_tasks:
            parts.append("\\nOpen Tasks:")
            for task in open_tasks[:12]:
                parts.append(f"- {task}")

        if done_tasks:
            parts.append("\\nRecently Completed Tasks:")
            for task in done_tasks[-8:]:
                parts.append(f"- {task}")

        if facts:
            parts.append("\\nKnown Facts:")
            for item in facts[-10:]:
                parts.append(f"- {item.get('text', item) if isinstance(item, dict) else item}")

        if decisions:
            parts.append("\\nDecisions:")
            for item in decisions[-10:]:
                parts.append(f"- {item.get('text', item) if isinstance(item, dict) else item}")

        if discoveries:
            parts.append("\\nDiscoveries:")
            for item in discoveries[-8:]:
                parts.append(f"- {item.get('text', item) if isinstance(item, dict) else item}")

        if questions:
            parts.append("\\nOpen Questions:")
            for item in questions[-8:]:
                parts.append(f"- {item.get('text', item) if isinstance(item, dict) else item}")

        if recent_events:
            parts.append("\\nRecent Timeline:")
            for event in recent_events:
                parts.append(f"- {event.get('time', '')}: {event.get('event', '')}")

        if mission_md:
            parts.append("\\nMission Brief:")
            parts.append(mission_md)

        if notes:
            parts.append("\\nProject Notes:")
            parts.append(notes)

        if session_log:
            parts.append("\\nRecent Session Log:")
            parts.append(session_log)

        parts.append("\\nInstruction: Treat Mission Intelligence as real disk-backed project memory. Use it directly. Do not say you lack memory if the answer is in this context. If something is missing, state exactly what is missing.")
        return "\\n".join(parts).strip()

    except Exception as exc:
        return f"MISSION INTELLIGENCE ERROR: {exc}"

def memory_add_item(kind: str, text: str) -> dict:
    if not active_project:
        return {"ok": False, "message": "Select a project first."}
    allowed = {
        "fact": "facts.json",
        "decision": "decisions.json",
        "question": "questions.json",
        "discovery": "discoveries.json",
        "objective": "objectives.json",
    }
    filename = allowed.get(kind)
    if not filename:
        return {"ok": False, "message": "Unknown memory type."}
    value = text.strip()
    if not value:
        return {"ok": False, "message": "Memory item is empty."}
    items = memory_json(active_project, filename, [])
    items.append({"time": now(), "text": value})
    memory_write_json(active_project, filename, items[-500:])
    memory_add_event(active_project, f"Memory added ({kind}): {value}")
    return {"ok": True, "message": f"Saved {kind} to Mission Intelligence."}
'''
        if insert_after in text:
            text = text.replace(insert_after, memory_engine)
            changed = True
            print("[FOXAI v10] Added Mission Intelligence Engine.")
        else:
            print("[FOXAI v10] Could not find mission_current block; memory engine may already exist or file differs.")
    else:
        print("[FOXAI v10] Mission Intelligence Engine already present.")

    if "ensure_memory_files(active_project)" not in text:
        before = text
        text = text.replace(
            '''    ensure_mission(active_project)
    add_timeline(active_project, "Project created")
    save_mission_state("Project selected")
''',
            '''    ensure_mission(active_project)
    ensure_memory_files(active_project)
    memory_add_event(active_project, "Project created and Mission Intelligence initialized")
    add_timeline(active_project, "Project created")
    save_mission_state("Project selected")
'''
        )
        text = text.replace(
            '''    add_timeline(active_project, "Project opened")
''',
            '''    ensure_memory_files(active_project)
    memory_add_event(active_project, "Project opened")
    add_timeline(active_project, "Project opened")
'''
        )
        if text != before:
            changed = True
            print("[FOXAI v10] Wired project open/create to memory files.")
        else:
            print("[FOXAI v10] Project wiring markers not found.")
    else:
        print("[FOXAI v10] Project memory wiring already present.")

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
            if active_project:
                add_timeline(active_project, "Message sent to Mission Console with Mission Intelligence")
                memory_record_chat(active_project, "ERIC", text)
            try:
                result = post_json(CHAT_API, {"model":"local-model","messages":messages,"temperature":0.7,"max_tokens":768,"stream":False}, 300)
'''
    if old in text:
        text = text.replace(old, new)
        changed = True
        print("[FOXAI v10] Injected Mission Intelligence into chat prompts.")
    else:
        print("[FOXAI v10] Chat prompt block may already be patched or differs.")

    if 'memory_record_chat(active_project, "AGENT"' not in text:
        before = text
        text = text.replace(
            '''                answer = result["choices"][0]["message"]["content"].strip(); messages.append({"role":"assistant","content":answer})
                if active_project: save_mission_state("Agent response received")
''',
            '''                answer = result["choices"][0]["message"]["content"].strip(); messages.append({"role":"assistant","content":answer})
                if active_project:
                    memory_record_chat(active_project, "AGENT", answer)
                    memory_add_event(active_project, "Agent response received")
                    save_mission_state("Agent response received")
'''
        )
        if text != before:
            changed = True
            print("[FOXAI v10] Added assistant transcript capture.")

    if "/api/memory/add" not in text:
        route_marker = '''        if path == "/api/memory/save": self._json(save_mission_state("Mission state manually saved")); return
'''
        route = route_marker + '''        if path == "/api/memory/add": self._json(memory_add_item(data.get("kind",""), data.get("text",""))); return
'''
        if route_marker in text:
            text = text.replace(route_marker, route)
            changed = True
            print("[FOXAI v10] Added /api/memory/add route.")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("[FOXAI v10] Patch applied successfully.")
    else:
        print("[FOXAI v10] No changes needed.")

    print()
    print("Next:")
    print("1. Restart FOXAI.")
    print("2. Select a project.")
    print("3. Add notes in the Project Workspace.")
    print("4. Ask: What do you remember about this mission?")
    print("5. Check: Projects/<project>/Memory/")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
