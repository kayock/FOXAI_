from __future__ import annotations

import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import sys
import tempfile
from pathlib import Path

EXPECTED_BEFORE = "d7bf0a2042d55ef7f0a5869556015e42c7427e7ff88636b28e1795f3adf7b952"
EXPECTED_AFTER = "a1e20209a7f102060108ff7422b6d98c7ea703a2aa085d7740e3d355c7532e81"
BEGIN_MARKER = "# FOXAI_LIVE_CURRENT_STATE_CHAT_V1_BEGIN"
END_MARKER = "# FOXAI_LIVE_CURRENT_STATE_CHAT_V1_END"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str, code: int) -> int:
    print()
    print("NOT INSTALLED")
    print(message)
    print("The original WebUI file remains in place.")
    return code


def focused_test(source_text: str) -> None:
    assert source_text.count(BEGIN_MARKER) == 1
    assert source_text.count(END_MARKER) == 1
    assert "Do not describe owner-visible runtime details as not publicly disclosed" in source_text
    assert "_live_current_state_http_reply(_sk_raw, _sk_route)" in source_text

    start = source_text.index(BEGIN_MARKER)
    finish = source_text.index(END_MARKER, start) + len(END_MARKER)
    block = source_text[start:finish]

    temp_root = Path(tempfile.mkdtemp(prefix="foxai_live_status_test_"))
    try:
        comfy = temp_root / "ComfyUI"
        comfy.mkdir(parents=True)
        comfy_main = comfy / "main.py"
        comfy_main.write_text("", encoding="utf-8")

        model = temp_root / "Models" / "Chat" / "Qwen3-30B-A3B-Q4_K_M.gguf"
        model.parent.mkdir(parents=True)
        model.write_text("", encoding="utf-8")

        namespace = {
            "__name__": "foxai_live_status_test",
            "json": json,
            "re": re,
            "os": os,
            "sys": sys,
            "platform": platform,
            "shutil": shutil,
            "Path": Path,
            "datetime": datetime.datetime,
            "ROOT": temp_root,
            "DRIVE": temp_root,
            "COMFY": comfy,
            "COMFY_MAIN": comfy_main,
            "CHAT_HEALTH": "http://127.0.0.1:8080/health",
            "chat_model": str(model),
            "chat_model_source": {"source": "USB", "source_label": "USB"},
            "chat_profile_id": "balanced_text",
            "active_project": "Focused Test",
            "active_prof": lambda: ("Agent Fox",),
            "check": lambda url: url in {
                "http://127.0.0.1:8080/health",
                "http://127.0.0.1:8188",
            },
        }

        exec(compile(block, "<foxai-live-status-test>", "exec"), namespace)

        namespace["_live_foxai_process_snapshot"] = lambda: {
            "available": True,
            "items": [
                {"pid": 101, "name": "python.exe", "role": "FOXAI WebUI"},
                {"pid": 202, "name": "llama-server.exe", "role": "Shared chat engine"},
            ],
            "model_candidates": ["Qwen3-30B-A3B-Q4_K_M.gguf"],
            "reason": "",
        }

        questions = (
            "What Python is FOXAI using?",
            "How much free space is on Z:?",
            "Is ComfyUI running?",
            "Which FOXAI launchers are active?",
            "What model is loaded?",
            "Show me FOXAI's current status.",
        )

        for question in questions:
            raw = json.dumps({"message": question}).encode("utf-8")
            send = namespace["_live_current_state_http_reply"](
                raw,
                "/api/chat/send",
            )
            assert send.get("intercepted") is True, (question, send)
            payload = json.loads(send["body"].decode("utf-8"))
            assert payload.get("status") == "answered", (question, payload)
            assert payload.get("live_current_state") is True, (question, payload)
            assert "not publicly disclosed" not in payload.get("answer", "").casefold()

            stream = namespace["_live_current_state_http_reply"](
                raw,
                "/api/chat/stream",
            )
            assert stream.get("intercepted") is True, (question, stream)
            events = [
                json.loads(line)
                for line in stream["body"].decode("utf-8").splitlines()
            ]
            assert [event.get("type") for event in events] == [
                "start",
                "chunk",
                "final",
            ]

        for question in (
            r"What does core\director.py do?",
            "Tell me a joke about foxes.",
            r"/engineer explain what core\director.py does",
            "Which Python should I install for data science?",
        ):
            raw = json.dumps({"message": question}).encode("utf-8")
            result = namespace["_live_current_state_http_reply"](
                raw,
                "/api/chat/send",
            )
            assert result.get("intercepted") is False, (question, result)

    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    if len(sys.argv) != 4:
        return fail("The installer did not receive its required paths.", 2)

    root = Path(sys.argv[1]).resolve()
    target = Path(sys.argv[2]).resolve()
    replacement = Path(sys.argv[3]).resolve()

    if not target.is_file():
        return fail(f"Could not find: {target}", 3)
    if not replacement.is_file():
        return fail("The packaged replacement is missing.", 4)

    current = digest(target)

    if current == EXPECTED_AFTER:
        print()
        print("ALREADY INSTALLED")
        print("Agent Fox live current-status answers are already active.")
        return 0

    if current != EXPECTED_BEFORE:
        return fail(
            "Your current core\\foxai_web.py differs from the exact uploaded "
            "file used to build this repair, so it was not overwritten.",
            5,
        )

    if digest(replacement) != EXPECTED_AFTER:
        return fail("The packaged replacement failed its integrity check.", 6)

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = root / "Backups" / "AgentFoxLiveStatus"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"foxai_web_before_live_status_{stamp}.py"
    shutil.copy2(target, backup)

    temporary = target.with_name("foxai_web.py.installing")

    try:
        shutil.copy2(replacement, temporary)
        installed_text = temporary.read_text(encoding="utf-8")
        compile(installed_text, str(temporary), "exec")
        focused_test(installed_text)
        os.replace(temporary, target)

        if digest(target) != EXPECTED_AFTER:
            raise RuntimeError("The installed file failed its final integrity check.")

    except Exception as error:
        try:
            if temporary.exists():
                temporary.unlink()
            shutil.copy2(backup, target)
        except Exception as restore_error:
            print()
            print("AUTOMATIC RESTORE NEEDS ATTENTION")
            print(f"Install error: {error}")
            print(f"Restore error: {restore_error}")
            print(f"Backup: {backup}")
            return 20

        return fail(
            "The automatic tests failed, so the original WebUI file was restored.\n"
            + str(error),
            10,
        )

    print()
    print("SUCCESS")
    print("Normal WebUI chat can now answer live read-only FOXAI status questions.")
    print("Python, Z: free space, ComfyUI, active FOXAI processes, loaded model,")
    print("and overall FOXAI status are covered.")
    print("Historical receipts are not substituted for current readings.")
    print("Slash commands, Engineer, Workshop, Casbin, and file grounding remain active.")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
