from __future__ import annotations

import json
import runpy
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    package = Path(__file__).resolve().parent
    target = package / "apply.py"
    diagnostic = package / "STARTUP_ERROR.txt"

    try:
        if not target.is_file():
            raise FileNotFoundError(
                f"Apply script is missing: {target}"
            )

        package_text = str(package)
        if package_text not in sys.path:
            sys.path.insert(0, package_text)

        runpy.run_path(str(target), run_name="__main__")
        return 0

    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1

    except Exception as exc:
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "package_folder": str(package),
            "python": sys.executable,
            "python_version": sys.version,
            "exception": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }
        diagnostic.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        print()
        print("FOXAI MISSION IMAGE CONTINUITY + LEAKAGE REPAIR")
        print("STARTUP FAILURE — NO APPLY CONFIRMED")
        print()
        print(payload["exception"])
        print()
        print(payload["traceback"])
        print("Diagnostic:", diagnostic)
        input("Press Enter to close...")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
