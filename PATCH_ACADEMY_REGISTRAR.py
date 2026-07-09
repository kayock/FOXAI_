from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TARGET_DIR = ROOT / "core_v10" / "academy"
TARGET = TARGET_DIR / "__init__.py"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"academy_registrar_{STAMP}"
BACKUP_FILE = BACKUP_DIR / "core_v10" / "academy" / "__init__.py"

PATCH = 