from __future__ import annotations

import datetime
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

EXPECTED_BEFORE = "1397b0ce5d1e21b9fc49eabef76ffa64467d716061b12d1a2c670167597d7d55"
EXPECTED_AFTER = "b28c6cd586f448904b72e80988c081242ca8a249f3aedd9496fba65ad0e814d4"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str, code: int = 1) -> int:
    print()
    print("NOT INSTALLED")
    print(message)
    print("No FOXAI source file was left changed.")
    return code


def main() -> int:
    if len(sys.argv) != 4:
        return fail("The installer did not receive its required paths.", 2)

    root = Path(sys.argv[1]).resolve()
    target = Path(sys.argv[2]).resolve()
    patch = Path(sys.argv[3]).resolve()

    if not target.is_file():
        return fail(f"Could not find: {target}", 3)
    if not patch.is_file():
        return fail(f"Could not find packaged replacement: {patch}", 4)

    current = sha256(target)
    replacement = sha256(patch)

    if replacement != EXPECTED_AFTER:
        return fail("The packaged replacement failed its integrity check.", 5)

    if current == EXPECTED_AFTER:
        print()
        print("ALREADY INSTALLED")
        print("Unified Agent Fox chat is already active.")
        return 0

    if current != EXPECTED_BEFORE:
        return fail(
            "Your current core\\director.py is different from the exact file used "
            "to build this repair. It was not overwritten.",
            6,
        )

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = root / "Backups" / "UnifiedAgentFoxChat"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"director_before_unified_chat_{stamp}.py"
    shutil.copy2(target, backup)

    temporary = target.with_name("director.py.unified_chat_installing")
    try:
        shutil.copy2(patch, temporary)
        compile(temporary.read_text(encoding="utf-8"), str(temporary), "exec")
        os.replace(temporary, target)

        test_code = r"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))

from core.director import direct

normal_messages = (
    "What safeguards limit the resource evidence provider?",
    "Can you explain the kernel?",
    "Search my library for astronomy.",
    "Draw a purple fox.",
    "Please review this traceback and explain it.",
    "Write a poem about foxes.",
)

for message in normal_messages:
    result = direct(
        message,
        actor="operator",
        operator_approved=True,
        audit=False,
    )
    assert result["agent"] == "chat", (message, result)

image = direct(
    "/image a purple fox",
    actor="operator",
    operator_approved=True,
    audit=False,
)
assert image["agent"] == "red_canvas", image
print("UNIFIED_AGENT_FOX_CHAT_OK")
"""
        completed = subprocess.run(
            [sys.executable, "-I", "-B", "-S", "-c", test_code, str(root)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Live routing check failed.\n"
                + completed.stdout
                + completed.stderr
            )

        if sha256(target) != EXPECTED_AFTER:
            raise RuntimeError("Installed file failed its final integrity check.")

    except Exception as exc:
        try:
            if temporary.exists():
                temporary.unlink()
            shutil.copy2(backup, target)
        except Exception as restore_exc:
            print()
            print("AUTOMATIC RESTORE NEEDS ATTENTION")
            print(f"Repair error: {exc}")
            print(f"Restore error: {restore_exc}")
            print(f"Backup remains at: {backup}")
            return 20
        return fail(f"Automatic test failed and the original file was restored.\n{exc}", 10)

    print()
    print("SUCCESS")
    print("Unified Agent Fox chat is installed.")
    print("Normal sentences now stay with Agent Fox.")
    print("Explicit /image and /engineer commands remain available.")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
