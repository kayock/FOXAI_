import subprocess
import time
import threading
from pathlib import Path

import requests
import customtkinter as ctk
import psutil

BASE = Path(__file__).parent
ENGINE = BASE / "Engine" / "llama-server.exe"
MODELS = BASE / "Models"
PROMPTS = BASE / "Prompts"

HOST = "127.0.0.1"
PORT = "8080"
API_URL = f"http://{HOST}:{PORT}/v1/chat/completions"

THREADS = "12"
CTX_SIZE = "8192"

process = None
messages = []

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


def find_models():
    return sorted(MODELS.rglob("*.gguf"))


def find_profiles():
    return sorted(PROMPTS.glob("*.txt"))


def add_chat(role, text):
    chat_box.configure(state="normal")
    chat_box.insert("end", f"\n{role}:\n{text}\n")
    chat_box.see("end")
    chat_box.configure(state="disabled")


def start_ai():
    global process, messages

    if process and process.poll() is None:
        status.set("Already running.")
        return

    model_name = model_menu.get()
    profile_name = profile_menu.get()

    model = next((m for m in models if m.name == model_name), None)
    profile = next((p for p in profiles if p.name == profile_name), None)

    if not model:
        status.set("No model selected.")
        return

    messages = []

    if profile_name != "Default" and profile:
        system_prompt = profile.read_text(encoding="utf-8")
        messages.append({"role": "system", "content": system_prompt})

    cmd = [
        str(ENGINE),
        "--model", str(model),
        "--host", HOST,
        "--port", PORT,
        "--ctx-size", CTX_SIZE,
        "--threads", THREADS,
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    status.set("Starting...")
    add_chat("System", f"Starting {model.name}...")
    threading.Thread(target=wait_for_server, daemon=True).start()


def wait_for_server():
    for _ in range(60):
        try:
            requests.get(f"http://{HOST}:{PORT}/health", timeout=1)
            status.set("Ready")
            add_chat("AGENT FOX", "Good morning, Eric.\n\nAll systems operational.\nNeural engine online.\nAwaiting mission.")
            return
        except Exception:
            time.sleep(1)

    status.set("Server did not respond.")
    add_chat("System", "Server did not respond after 60 seconds.")


def stop_ai():
    global process

    if process and process.poll() is None:
        process.terminate()
        status.set("Stopped")
        add_chat("System", "FoxAI stopped.")
    else:
        status.set("Not running.")


def send_message(event=None):
    user_text = input_box.get("1.0", "end").strip()

    if not user_text:
        return "break"

    if not process or process.poll() is not None:
        add_chat("System", "Start FoxAI first.")
        return "break"

    input_box.delete("1.0", "end")
    add_chat("Eric", user_text)

    messages.append({"role": "user", "content": user_text})
    threading.Thread(target=get_ai_response, daemon=True).start()
    return "break"


def get_ai_response():
    try:
        status.set("Thinking...")

        payload = {
            "model": "local-model",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 512,
            "stream": False,
        }

        response = requests.post(API_URL, json=payload, timeout=300)
        response.raise_for_status()

        data = response.json()
        answer = data["choices"][0]["message"]["content"].strip()

        messages.append({"role": "assistant", "content": answer})
        add_chat("AGENT FOX", answer)
        status.set("Ready")

    except Exception as e:
        add_chat("System", f"Error: {e}")
        status.set("Error")


def update_stats():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    ram_used = ram.used / (1024 ** 3)
    ram_total = ram.total / (1024 ** 3)

    stats.set(
        f"CPU: {cpu:.0f}%  |  RAM: {ram_used:.1f}/{ram_total:.1f} GB  |  Status: {status.get()}"
    )

    app.after(1000, update_stats)


models = find_models()
profiles = find_profiles()

app = ctk.CTk()
app.title("FoxAI Desktop v2.2")
app.geometry("1100x700")

main = ctk.CTkFrame(app)
main.pack(fill="both", expand=True, padx=10, pady=10)

sidebar = ctk.CTkFrame(main, width=280)
sidebar.pack(side="left", fill="y", padx=(0, 10), pady=0)

content = ctk.CTkFrame(main)
content.pack(side="right", fill="both", expand=True)

title = ctk.CTkLabel(
    sidebar,
    text="FOXAI // OPS",
    font=("Arial", 30, "bold")
)

version = ctk.CTkLabel(sidebar, text="Cyber Operations Console")
version.pack(pady=(0, 20))

ctk.CTkLabel(sidebar, text="Model").pack(pady=(10, 5))
model_menu = ctk.CTkOptionMenu(
    sidebar,
    values=[m.name for m in models] or ["No models found"],
    width=240
)
model_menu.pack(pady=5)

ctk.CTkLabel(sidebar, text="Profile").pack(pady=(20, 5))
profile_menu = ctk.CTkOptionMenu(
    sidebar,
    values=["Default"] + [p.name for p in profiles],
    width=240
)
profile_menu.pack(pady=5)

start_button = ctk.CTkButton(sidebar, text="Start FoxAI", command=start_ai, width=220)
start_button.pack(pady=(30, 8))

stop_button = ctk.CTkButton(sidebar, text="Stop FoxAI", command=stop_ai, width=220)
stop_button.pack(pady=8)

clear_button = ctk.CTkButton(
    sidebar,
    text="Clear Chat",
    command=lambda: [chat_box.configure(state="normal"), chat_box.delete("1.0", "end"), chat_box.configure(state="disabled")],
    width=220
)
clear_button.pack(pady=8)

status = ctk.StringVar(value="Stopped")
stats = ctk.StringVar(value="CPU: -- | RAM: -- | Status: Stopped")

chat_title = ctk.CTkLabel(content, text="Chat", font=("Arial", 24, "bold"))
chat_title.pack(pady=(15, 5))

chat_box = ctk.CTkTextbox(content, wrap="word", state="disabled")
chat_box.pack(padx=15, pady=10, fill="both", expand=True)

bottom = ctk.CTkFrame(content)
bottom.pack(padx=15, pady=(0, 10), fill="x")

input_box = ctk.CTkTextbox(bottom, height=90, wrap="word")
input_box.pack(side="left", padx=10, pady=10, fill="x", expand=True)
input_box.bind("<Return>", send_message)

send_button = ctk.CTkButton(bottom, text="Send", command=send_message, width=100)
send_button.pack(side="right", padx=10, pady=10)

status_bar = ctk.CTkLabel(content, textvariable=stats)
status_bar.pack(pady=(0, 8))

update_stats()
app.mainloop()