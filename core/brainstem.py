import time
import requests


class Brainstem:
    """
    Brainstem is FOXAI's central nervous system.

    It monitors the local neural engine and tracks the current Workshop state.
    """

    STATE_OFFLINE = "OFFLINE"
    STATE_STARTING = "STARTING"
    STATE_READY = "READY"
    STATE_BUSY = "BUSY"
    STATE_ERROR = "ERROR"

    def __init__(self, host="127.0.0.1", port="8080"):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

        self.state = self.STATE_OFFLINE
        self.active_mission = None
        self.active_specialist = None
        self.mission_started_at = None
        self.last_error = None

    # -------------------------
    # Neural engine health
    # -------------------------

    def health_url(self):
        return f"{self.base_url}/health"

    def chat_url(self):
        return f"{self.base_url}/v1/chat/completions"

    def is_server_alive(self, timeout=1):
        try:
            response = requests.get(self.health_url(), timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False

    def wait_until_ready(self, seconds=90):
        self.set_state(self.STATE_STARTING)
        start = time.time()

        while time.time() - start < seconds:
            if self.is_server_alive():
                self.set_state(self.STATE_READY)
                return True
            time.sleep(1)

        self.set_error("Neural engine failed to respond before timeout.")
        return False

    def test_chat(self):
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "user", "content": "Reply with exactly: ONLINE"}
            ],
            "temperature": 0,
            "max_tokens": 16,
            "stream": False,
        }

        try:
            start = time.time()
            response = requests.post(self.chat_url(), json=payload, timeout=60)
            elapsed = round(time.time() - start, 2)

            if response.status_code != 200:
                self.set_error(f"HTTP {response.status_code}")
                return False, f"HTTP {response.status_code}", elapsed

            text = response.json()["choices"][0]["message"]["content"].strip()

            if not text:
                self.set_error("Blank response")
                return False, "Blank response", elapsed

            self.set_state(self.STATE_READY)
            return True, text, elapsed

        except Exception as error:
            self.set_error(str(error))
            return False, str(error), 0

    # -------------------------
    # Workshop state
    # -------------------------

    def set_state(self, state):
        self.state = state
        if state != self.STATE_ERROR:
            self.last_error = None

    def set_error(self, message):
        self.state = self.STATE_ERROR
        self.last_error = message

    def is_ready(self):
        return self.state == self.STATE_READY

    def is_busy(self):
        return self.state == self.STATE_BUSY

    def begin_mission(self, mission="Unknown", specialist="Unknown"):
        self.state = self.STATE_BUSY
        self.active_mission = mission
        self.active_specialist = specialist
        self.mission_started_at = time.time()
        self.last_error = None

    def complete_mission(self):
        self.state = self.STATE_READY
        self.active_mission = None
        self.active_specialist = None
        self.mission_started_at = None

    def fail_mission(self, error):
        self.state = self.STATE_ERROR
        self.last_error = str(error)

    def elapsed_seconds(self):
        if not self.mission_started_at:
            return 0
        return int(time.time() - self.mission_started_at)

    def elapsed_label(self):
        seconds = self.elapsed_seconds()
        minutes = seconds // 60
        remaining = seconds % 60
        return f"{minutes:02d}:{remaining:02d}"

    def snapshot(self):
        return {
            "state": self.state,
            "busy": self.is_busy(),
            "active_mission": self.active_mission,
            "active_specialist": self.active_specialist,
            "elapsed_seconds": self.elapsed_seconds(),
            "elapsed_label": self.elapsed_label(),
            "last_error": self.last_error,
            "neural_engine_alive": self.is_server_alive(),
        }
