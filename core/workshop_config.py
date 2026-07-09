import json
from pathlib import Path


class WorkshopConfig:
    """
    Central Workshop configuration.

    RC1 focuses on chat resilience:
    - configurable timeout
    - heartbeat interval
    - long think mode
    - graceful timeout language
    """

    DEFAULTS = {
        "chat_timeout_seconds": 900,
        "heartbeat_interval_seconds": 30,
        "allow_long_think_mode": True,
        "long_think_timeout_seconds": 1800,
        "enable_streaming": False,
        "graceful_timeout_messages": True,
        "retry_on_timeout": False,
        "adaptive_timeout": True,
    }

    def __init__(self, root=None):
        self.root = Path(root) if root else Path(__file__).resolve().parents[1]
        self.config_dir = self.root / "config"
        self.config_path = self.config_dir / "workshop_config.json"
        self.data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if not self.config_path.exists():
            self.save()
            return self.data

        try:
            loaded = json.loads(self.config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except Exception:
            # Keep defaults if config cannot be read.
            pass

        return self.data

    def save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.data, indent=2),
            encoding="utf-8",
        )

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    @property
    def chat_timeout_seconds(self):
        return int(self.get("chat_timeout_seconds", 900))

    @property
    def heartbeat_interval_seconds(self):
        return int(self.get("heartbeat_interval_seconds", 30))

    @property
    def allow_long_think_mode(self):
        return bool(self.get("allow_long_think_mode", True))

    @property
    def long_think_timeout_seconds(self):
        return int(self.get("long_think_timeout_seconds", 1800))

    @property
    def enable_streaming(self):
        return bool(self.get("enable_streaming", False))

    @property
    def retry_on_timeout(self):
        return bool(self.get("retry_on_timeout", False))

    @property
    def adaptive_timeout(self):
        return bool(self.get("adaptive_timeout", True))

    def timeout_for_mission(self, mission_type="conversation", long_think=False):
        if long_think and self.allow_long_think_mode:
            return self.long_think_timeout_seconds

        if not self.adaptive_timeout:
            return self.chat_timeout_seconds

        mission = (mission_type or "").lower()

        if mission in ["engineering", "architecture", "code review", "research"]:
            return max(self.chat_timeout_seconds, 900)

        if mission in ["creative", "red canvas", "prompt"]:
            return max(self.chat_timeout_seconds, 600)

        return self.chat_timeout_seconds

    def report(self):
        lines = [
            "WORKSHOP CONFIGURATION",
            "",
            "Chat Resilience:",
            f"• Chat Timeout: {self.chat_timeout_seconds} seconds",
            f"• Heartbeat Interval: {self.heartbeat_interval_seconds} seconds",
            f"• Long Think Mode: {self.allow_long_think_mode}",
            f"• Long Think Timeout: {self.long_think_timeout_seconds} seconds",
            f"• Streaming Enabled: {self.enable_streaming}",
            f"• Retry On Timeout: {self.retry_on_timeout}",
            f"• Adaptive Timeout: {self.adaptive_timeout}",
            "",
            f"Config Path: {self.config_path}",
        ]

        return "\n".join(lines)


_config = None


def get_config():
    global _config

    if _config is None:
        _config = WorkshopConfig()

    return _config
