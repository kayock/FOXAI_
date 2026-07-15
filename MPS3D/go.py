from __future__ import annotations

import runpy
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    package_dir = Path(__file__).resolve().parent
    target = package_dir / "apply_model_profile_selector_runtime_phase3.py"
    log_path = package_dir / "APPLY_STARTUP_ERROR.txt"

    try:
        if not target.is_file():
            raise FileNotFoundError(
                f"Apply script is missing: {target}"
            )

        package_text = str(package_dir)
        if package_text not in sys.path:
            sys.path.insert(0, package_text)

        runpy.run_path(str(target), run_name="__main__")
        return 0
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        print(code)
        return 1
    except BaseException as exc:
        timestamp = datetime.now(timezone.utc).isoformat()
        details = (
            "FOXAI MODEL PROFILE SELECTOR RUNTIME PHASE 3\n"
            "STARTUP FAILURE — NO APPLY CONFIRMED\n\n"
            f"Time: {timestamp}\n"
            f"Package folder: {package_dir}\n"
            f"Python: {sys.executable}\n"
            f"Python version: {sys.version}\n"
            f"Exception: {type(exc).__name__}: {exc}\n\n"
            "Traceback:\n"
            + traceback.format_exc()
        )
        try:
            log_path.write_text(details, encoding="utf-8")
        except Exception:
            pass

        print()
        print("=" * 72)
        print("STARTUP STOPPED — NOTHING WAS APPLIED")
        print("=" * 72)
        print()
        print(f"{type(exc).__name__}: {exc}")
        print()
        print("Full diagnostic:")
        print(log_path)
        print()
        print("The window will remain open so this message can be read.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
