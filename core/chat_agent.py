import threading


class ChatAgent:
    name = "chat"

    def __init__(self, app):
        self.app = app

    def handle(self, text):
        if not self.app.server.is_running():
            self.app.add_chat("SYSTEM", "Start mission first.")
            return "break"

        self.app.input_box.delete("1.0", "end")
        self.app.add_chat("ERIC", text)
        self.app.messages.append({"role": "user", "content": text})
        self.app.mission_memory.save()

        threading.Thread(target=self.app.get_ai_response, daemon=True).start()
        return "break"
