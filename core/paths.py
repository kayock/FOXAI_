from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ENGINE = BASE / "Engine" / "llama-server.exe"
MODELS = BASE / "Models"
PROMPTS = BASE / "Prompts"
CONFIG = BASE / "Config"
LOGS = BASE / "Logs"
MEMORY = BASE / "Memory"
ARCHIVE = BASE / "Mission Archive"
LIBRARY = BASE / "Library"
RED_CANVAS = BASE / "Red Canvas"
ASSETS = BASE / "assets"
