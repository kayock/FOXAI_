from datetime import datetime
from core.paths import RED_CANVAS

def ensure_red_canvas():
    (RED_CANVAS / "Outputs").mkdir(parents=True, exist_ok=True)
    (RED_CANVAS / "Prompts").mkdir(parents=True, exist_ok=True)

def save_prompt(prompt, negative="", engine="Not connected yet", size="1024x1024"):
    ensure_red_canvas()
    path = RED_CANVAS / "Prompts" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S_prompt.md")
    path.write_text(
        f"# Red Canvas Prompt\n\nEngine: {engine}\nSize: {size}\n\n## Prompt\n{prompt}\n\n## Negative Prompt\n{negative}\n",
        encoding="utf-8"
    )
    return path
