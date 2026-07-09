from pathlib import Path
import json

root = Path(__file__).resolve().parent
dst = root / "Extensions" / "Academy" / "Conversation"
dst.mkdir(parents=True, exist_ok=True)

manifest = {
  "schema": 1,
  "key": "conversation",
  "name": "Conversation / Brain Router",
  "callsign": "USS Conversation Shuttle",
  "department": "Academy",
  "category": "Artificial Minds",
  "priority": 10,
  "portable": True,
  "reserved": False,
  "executables": [],
  "capabilities": [
    "general_reasoning",
    "conversation",
    "brainstorming",
    "teaching",
    "planning",
    "summarization",
    "creative_writing"
  ],
  "version": "3.4",
  "status": "ready",
  "description": "Routes reasoning and conversation missions through FOXAI brain providers."
}
(dst / "extension.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

plugin = """from __future__ import annotations

from core_v10.extension_hooks import hookimpl
from core_v10.conversation_shuttle import ConversationShuttle


@hookimpl
def extension_health(context, manifest):
    if manifest.get("key") != "conversation":
        return None
    shuttle = ConversationShuttle(context.foxai_root)
    h = shuttle.health()
    return {
        "key": "conversation",
        "ok": h.get("ok", False),
        "status": h.get("status", "unknown"),
        "message": h.get("message", ""),
        "path": "internal://conversation_shuttle",
    }


@hookimpl
def extension_launch(context, manifest, key):
    if key != "conversation":
        return None
    return {"key": "conversation", "ok": False, "message": "USS Conversation Shuttle is a service, not a GUI app."}


@hookimpl
def extension_invoke(context, manifest, key, action, payload):
    if key != "conversation":
        return None
    shuttle = ConversationShuttle(context.foxai_root)
    if action == "chat":
        return {"key": "conversation", **shuttle.chat(
            prompt=payload.get("prompt", ""),
            professor=payload.get("professor", "Professor Kayock"),
            mission_id=payload.get("mission_id"),
            metadata=payload.get("metadata", {}),
        )}
    return {"key": "conversation", "ok": False, "message": f"Unsupported action: {action}"}
"""
(dst / "plugin.py").write_text(plugin, encoding="utf-8")
print("USS Conversation Shuttle installed:")
print(dst)
