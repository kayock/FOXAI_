from __future__ import annotations

import datetime
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

EXPECTED_BEFORE = "1b3aa2e3ab0409112ca602209285e27df1ab6b0216f5d9a9480766e4509078c4"
EXPECTED_AFTER = "aaf6a65bf6195215dd71a6bf1ac39954771195cf7d906d2624fd904f7b068f46"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str, code: int) -> int:
    print()
    print("NOT INSTALLED")
    print(message)
    print("The original Agent Fox integration file remains in place.")
    return code


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
        print("Agent Fox exact-file answers are already active.")
        return 0

    if current != EXPECTED_BEFORE:
        return fail(
            "Your current desktop_self_knowledge_integration_v1.py differs "
            "from the exact uploaded file used to build this repair, so it "
            "was not overwritten.",
            5,
        )

    if digest(replacement) != EXPECTED_AFTER:
        return fail("The packaged replacement failed its integrity check.", 6)

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = root / "Backups" / "AgentFoxExactFile"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (
        f"desktop_self_knowledge_before_exact_file_{stamp}.py"
    )
    shutil.copy2(target, backup)

    temporary = target.with_name(
        "desktop_self_knowledge_integration_v1.py.installing"
    )

    try:
        shutil.copy2(replacement, temporary)
        compile(
            temporary.read_text(encoding="utf-8"),
            str(temporary),
            "exec",
        )
        os.replace(temporary, target)

        check_code = r"""
import importlib.util
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
target = root / "System" / "AgentFoxTechnicalCore" / "desktop_self_knowledge_integration_v1.py"

spec = importlib.util.spec_from_file_location(
    "foxai_agent_exact_file_live_test",
    target,
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

answer = module.route_desktop_message(
    r"What does core\director.py do?"
)
assert answer["intercepted"] is True, answer
assert answer["status"] == "answered", answer
assert answer["model_bypass"] is True, answer
assert "department selector" in answer["answer_text"], answer
assert "opened exactly this one FOXAI file" in answer["answer_text"], answer

slash = module._route_exact_project_file_question(
    r"/engineer explain what core\director.py does"
)
assert slash is None, slash

print("AGENT_FOX_EXACT_FILE_LIVE_TEST_OK")
"""
        test = subprocess.run(
            [sys.executable, "-I", "-B", "-S", "-c", check_code, str(root)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if test.returncode != 0:
            raise RuntimeError(test.stdout + test.stderr)

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
            "The automatic test failed, so the original integration file "
            "was restored.\n" + str(error),
            10,
        )

    print()
    print("SUCCESS")
    print("Ordinary Agent Fox chat can now explain one named FOXAI file.")
    print("The answer is grounded in that exact local file.")
    print("Slash commands, Engineer, Workshop, and Casbin were not changed.")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
