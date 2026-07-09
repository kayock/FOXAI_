class RedCanvasAgent:
    name = "red_canvas"

    def __init__(self, app):
        self.app = app

    def handle(self, original_text, image_prompt):
        self.app.input_box.delete("1.0", "end")
        self.app.route_image_request(original_text, image_prompt)
        return "break"
