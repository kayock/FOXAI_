import subprocess
from core.paths import ENGINE

class LlamaServer:
    def __init__(self):
        self.process = None

    def start(self, model, host="127.0.0.1", port="8080", context="8192", threads="12"):
        if self.is_running():
            return False
        if not ENGINE.exists():
            raise FileNotFoundError(f"Missing llama-server.exe at: {ENGINE}")
        cmd = [
            str(ENGINE), "--model", str(model),
            "--host", str(host), "--port", str(port),
            "--ctx-size", str(context), "--threads", str(threads),
        ]
        self.process = subprocess.Popen(cmd)
        return True

    def stop(self):
        if self.is_running():
            self.process.terminate()

    def is_running(self):
        return self.process is not None and self.process.poll() is None
