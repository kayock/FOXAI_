import time
import requests

from core.workshop_config import get_config


class ChatTimeoutError(Exception):
    """Raised when the neural engine exceeds the configured timeout."""


class ChatResilience:
    """
    Shared helper for long-running chat requests.

    RC1 provides:
    - centralized timeout lookup
    - graceful timeout messages
    - heartbeat text helpers
    - safe requests.post wrapper

    UI heartbeat wiring comes later.
    """

    def __init__(self, app=None):
        self.app = app
        self.config = get_config()

    def timeout_for(self, mission_type="conversation", long_think=False):
        return self.config.timeout_for_mission(
            mission_type=mission_type,
            long_think=long_think,
        )

    def heartbeat_message(self, started_at, model_name=None, mission_type="conversation"):
        elapsed = int(time.time() - started_at)
        minutes = elapsed // 60
        seconds = elapsed % 60

        lines = [
            "MISSION CONTROL",
            "",
            "Neural engine is still reasoning.",
            "",
            f"Elapsed: {minutes:02d}:{seconds:02d}",
            f"Mission Type: {mission_type}",
        ]

        if model_name:
            lines.append(f"Model: {model_name}")

        lines.extend([
            "",
            "Status:",
            "Still working. No action required unless you want to cancel or retry.",
        ])

        return "\n".join(lines)

    def timeout_message(self, timeout_seconds, mission_type="conversation", model_name=None):
        minutes = timeout_seconds // 60
        seconds = timeout_seconds % 60

        lines = [
            "MISSION CONTROL",
            "",
            "The neural engine exceeded the configured reasoning window.",
            "",
            f"Configured Timeout: {minutes:02d}:{seconds:02d}",
            f"Mission Type: {mission_type}",
        ]

        if model_name:
            lines.append(f"Model: {model_name}")

        lines.extend([
            "",
            "What this usually means:",
            "• The model was working on a difficult request.",
            "• The response was too long for the current timeout.",
            "• The server stalled or stopped responding.",
            "",
            "Recommended actions:",
            "• Retry with a shorter request.",
            "• Use Long Think Mode.",
            "• Reduce max reply tokens.",
            "• Try a smaller or more specialized model.",
            "• Restart the neural engine if repeated timeouts occur.",
        ])

        return "\n".join(lines)

    def post_json(self, url, payload, mission_type="conversation", long_think=False, model_name=None):
        timeout = self.timeout_for(mission_type=mission_type, long_think=long_think)
        started_at = time.time()

        try:
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            return response

        except requests.exceptions.ReadTimeout as error:
            message = self.timeout_message(
                timeout_seconds=timeout,
                mission_type=mission_type,
                model_name=model_name,
            )
            raise ChatTimeoutError(message) from error

        except requests.exceptions.ConnectionError as error:
            message = (
                "MISSION CONTROL\n\n"
                "The neural engine connection was interrupted.\n\n"
                "Recommended actions:\n"
                "• Check whether llama-server is still running.\n"
                "• Restart the neural engine.\n"
                "• Retry the mission after the server reports READY."
            )
            raise ChatTimeoutError(message) from error

    def should_heartbeat(self, started_at, last_heartbeat_at):
        now = time.time()
        interval = self.config.heartbeat_interval_seconds

        return (now - last_heartbeat_at) >= interval
