from __future__ import annotations

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
