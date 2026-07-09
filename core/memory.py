import json
from datetime import datetime
from core.paths import MEMORY, ARCHIVE

OPERATOR_FILE = MEMORY / "Operator.json"
CHAT_ARCHIVE = ARCHIVE / "Chats"

DEFAULT_OPERATOR = {
    "operator_name": "Eric Fox",
    "platform_name": "FoxAI",
    "assistant_name": "Agent Fox",
    "style": "adaptive",
    "theme": "cyberpunk hacker console inspired by Kali Linux",
    "current_mission": "Operation Cyber Console",
    "project_goal": "Build a portable offline AI workstation on a Samsung T7 USB drive"
}

class OperatorMemory:
    def __init__(self):
        self.data = {}

    def load(self):
        MEMORY.mkdir(exist_ok=True)
        if not OPERATOR_FILE.exists():
            self.data = DEFAULT_OPERATOR.copy()
            self.save()
        else:
            with open(OPERATOR_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        return self.data

    def save(self):
        MEMORY.mkdir(exist_ok=True)
        with open(OPERATOR_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def get(self, key, default=None):
        return self.data.get(key, default)

class MissionMemory:
    def __init__(self):
        self.start_time = datetime.now()
        self.lines = []

    def add(self, speaker, text):
        self.lines.append((speaker, text))

    def save(self):
        if not self.lines:
            return None
        now = datetime.now()
        folder = CHAT_ARCHIVE / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / now.strftime("%H-%M-%S Mission.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# FoxAI Mission Log\n\n")
            f.write(f"Started: {self.start_time}\nSaved:   {now}\n\n")
            for speaker, text in self.lines:
                f.write(f"## {speaker}\n\n{text.strip()}\n\n")
        return path
