from __future__ import annotations

import datetime
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

EXPECTED_BEFORE = "d01bd8e6e6ec1b8be896c828177caf3d5eea4bd58a6ea54e95b5976779683b28"
EXPECTED_AFTER = "0fb24b2230423acb2b3e7a68cb47540c904db029b9ceceb5eb85634cd6c47fbb"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str, code: int) -> int:
    print()
    print("NOT INSTALLED")
    print(message)
    print("The original Engineer file remains in place.")
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

    current = sha256(target)
    if current == EXPECTED_AFTER:
        print()
        print("ALREADY INSTALLED")
        print("Engineer exact-file explanations are already active.")
        return 0

    if current != EXPECTED_BEFORE:
        return fail(
            "Your current core\\engineer_agent.py differs from the exact file "
            "used to build this repair, so it was not overwritten.",
            5,
        )

    if sha256(replacement) != EXPECTED_AFTER:
        return fail("The packaged replacement failed its integrity check.", 6)

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = root / "Backups" / "EngineerExactFile"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"engineer_agent_before_exact_file_{stamp}.py"
    shutil.copy2(target, backup)

    temporary = target.with_name("engineer_agent.py.installing")

    try:
        shutil.copy2(replacement, temporary)
        compile(temporary.read_text(encoding="utf-8"), str(temporary), "exec")
        os.replace(temporary, target)

        test_code = r"""
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))

from core.engineer_agent import EngineerAgent

agent = EngineerAgent.__new__(EngineerAgent)
agent.project_root = root

query = r"explain what core\director.py does"
parsed = agent.parse_exact_path_inspection(query)
assert parsed == r"core\director.py", parsed

resolved, error = agent.resolve_exact_inspection_path(parsed)
assert not error, error
assert resolved == (root / "core" / "director.py").resolve(), resolved

text = resolved.read_text(encoding="utf-8", errors="replace")
summary = agent._brief_exact_file_summary(resolved, text)
assert "department selector" in summary, summary
assert "Normal messages remain in Agent Fox chat" in summary, summary

print("ENGINEER_EXACT_FILE_OK")
"""
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-S", "-c", test_code, str(root)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stdout + result.stderr)

        if sha256(target) != EXPECTED_AFTER:
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
            "The automatic test failed, so the original Engineer file was restored.\n"
            + str(error),
            10,
        )

    print()
    print("SUCCESS")
    print("Engineer now opens and explains one named file directly.")
    print("Relative FOXAI paths such as core\\director.py are supported.")
    print("Casbin remains installed; it was not blocking this read-only request.")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
