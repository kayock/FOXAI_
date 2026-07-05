import time
import threading
import configparser

import customtkinter as ctk
import psutil
import requests
from PIL import Image

from core.paths import CONFIG, ASSETS
from core.models import find_models
from core.agents import find_agents, load_agent_prompt
from core.server import LlamaServer
from core.memory import OperatorMemory, MissionMemory
from core.library import ensure_library, list_documents, search_documents
from core.red_canvas import save_prompt

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class FoxAIApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FOXAI // Cyber Operations Console")
        self.icon_path = ASSETS / "foxai.ico"
        self.logo_path = ASSETS / "foxai_logo.png"

        if self.icon_path.exists():
            self.iconbitmap(str(self.icon_path))

        self.geometry("1220x780")

        self.server = LlamaServer()
        self.operator_memory = OperatorMemory()
        self.operator = self.operator_memory.load()
        self.mission_memory = MissionMemory()

        self.models = find_models()
        self.agents = find_agents()
        self.messages = []

        self.config = self.load_config()
        self.host = self.config["Server"].get("host", "127.0.0.1")
        self.port = self.config["Server"].get("port", "8080")
        self.threads = self.config["Server"].get("threads", "12")
        self.context = self.config["Server"].get("context", "8192")
        self.api_url = f"http://{self.host}:{self.port}/v1/chat/completions"

        self.status = ctk.StringVar(value="OFFLINE")
        self.stats = ctk.StringVar(value="CPU -- | RAM -- | STATUS OFFLINE")

        self.build_ui()
        self.show_mission_console()
        self.update_stats()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_config(self):
        CONFIG.mkdir(exist_ok=True)
        config_file = CONFIG / "FoxAI.ini"
        config = configparser.ConfigParser()
        if not config_file.exists():
            config["Server"] = {"host": "127.0.0.1", "port": "8080", "threads": "12", "context": "8192"}
            with open(config_file, "w", encoding="utf-8") as f:
                config.write(f)
        config.read(config_file)
        return config

    def build_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        self.sidebar = ctk.CTkFrame(main, width=290)
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))

        self.content = ctk.CTkFrame(main)
        self.content.pack(side="right", fill="both", expand=True)

        self.build_sidebar()

    def build_sidebar(self):
        if self.logo_path.exists():
            logo_img = ctk.CTkImage(light_image=Image.open(self.logo_path), dark_image=Image.open(self.logo_path), size=(165, 165))
            logo_label = ctk.CTkLabel(self.sidebar, image=logo_img, text="")
            logo_label.image = logo_img
            logo_label.pack(pady=(15, 5))

        ctk.CTkLabel(self.sidebar, text="FOXAI // OPS", font=("Consolas", 28, "bold")).pack(pady=(5, 5))
        ctk.CTkLabel(self.sidebar, text="Cyber Operations Console", font=("Consolas", 13)).pack(pady=(0, 18))

        info = (
            f"OPERATOR: {self.operator.get('operator_name', 'Operator')}\n"
            f"ASSISTANT: {self.operator.get('assistant_name', 'Agent Fox')}\n"
            f"MISSION: {self.operator.get('current_mission', 'No active mission')}"
        )
        ctk.CTkLabel(self.sidebar, text=info, justify="left", font=("Consolas", 12)).pack(pady=(0, 15), padx=12)

        ctk.CTkLabel(self.sidebar, text="NEURAL ENGINE", font=("Consolas", 12, "bold")).pack(pady=(5, 5))
        self.model_menu = ctk.CTkOptionMenu(self.sidebar, values=[m.name for m in self.models] or ["No engines found"], width=250)
        self.model_menu.pack(pady=5)

        ctk.CTkLabel(self.sidebar, text="AGENT", font=("Consolas", 12, "bold")).pack(pady=(12, 5))
        self.agent_menu = ctk.CTkOptionMenu(self.sidebar, values=["Agent Fox"] + [a.name for a in self.agents], width=250)
        self.agent_menu.pack(pady=5)

        ctk.CTkLabel(self.sidebar, text="OPERATIONS", font=("Consolas", 12, "bold")).pack(pady=(18, 8))
        ctk.CTkButton(self.sidebar, text="⌂ DASHBOARD", command=self.show_dashboard, width=230).pack(pady=4)
        ctk.CTkButton(self.sidebar, text="> MISSION CONSOLE", command=self.show_mission_console, width=230).pack(pady=4)
        ctk.CTkButton(self.sidebar, text="▣ MISSION ARCHIVE", command=self.show_archive, width=230).pack(pady=4)
        ctk.CTkButton(self.sidebar, text="▤ IRON LIBRARY", command=self.show_iron_library, width=230).pack(pady=4)
        ctk.CTkButton(self.sidebar, text="◈ RED CANVAS", command=self.show_red_canvas, width=230).pack(pady=4)
        ctk.CTkButton(self.sidebar, text="⚙ ARSENAL", command=self.show_arsenal, width=230).pack(pady=4)

        ctk.CTkLabel(self.sidebar, text="MISSION CONTROL", font=("Consolas", 12, "bold")).pack(pady=(14, 8))
        ctk.CTkButton(self.sidebar, text="START MISSION", command=self.start_ai, width=230).pack(pady=4)
        ctk.CTkButton(self.sidebar, text="END MISSION", command=self.stop_ai, width=230).pack(pady=4)
        ctk.CTkButton(self.sidebar, text="SAVE MISSION", command=self.save_mission, width=230).pack(pady=4)

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def make_title(self, title):
        ctk.CTkLabel(self.content, text=title, font=("Consolas", 24, "bold")).pack(pady=(15, 5))

    def make_status_bar(self):
        status_frame = ctk.CTkFrame(self.content)
        status_frame.pack(pady=(0, 8), padx=15, fill="x")
        self.status_led = ctk.CTkLabel(status_frame, text="●", font=("Consolas", 18, "bold"), text_color="#666666")
        self.status_led.pack(side="left", padx=(10, 6))
        ctk.CTkLabel(status_frame, textvariable=self.stats, font=("Consolas", 12)).pack(side="left")

    def show_dashboard(self):
        self.clear_content()
        self.make_title("MISSION DASHBOARD")
        panel = ctk.CTkFrame(self.content)
        panel.pack(fill="both", expand=True, padx=20, pady=20)
        cards = [
            ("OPERATOR", self.operator.get("operator_name", "Operator")),
            ("ASSISTANT", f"{self.operator.get('assistant_name', 'Agent Fox')} // {self.status.get()}"),
            ("CURRENT OPERATION", self.operator.get("current_mission", "Operation Cyber Console")),
            ("NEURAL ENGINES", str(len(self.models))),
            ("AGENTS", str(len(self.agents) + 1)),
            ("ARCHIVE", "ONLINE"),
        ]
        for i, (label, value) in enumerate(cards):
            card = ctk.CTkFrame(panel)
            card.grid(row=i // 2, column=i % 2, padx=14, pady=14, sticky="nsew")
            ctk.CTkLabel(card, text=label, font=("Consolas", 13, "bold")).pack(pady=(18, 5))
            ctk.CTkLabel(card, text=value, font=("Consolas", 18)).pack(pady=(5, 18))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=1)
        self.make_status_bar()

    def show_mission_console(self):
        self.clear_content()
        self.make_title("MISSION CONSOLE")
        self.chat_box = ctk.CTkTextbox(self.content, wrap="word", state="disabled", font=("Consolas", 13))
        self.chat_box.pack(padx=15, pady=10, fill="both", expand=True)
        bottom = ctk.CTkFrame(self.content)
        bottom.pack(padx=15, pady=(0, 10), fill="x")
        self.input_box = ctk.CTkTextbox(bottom, height=90, wrap="word", font=("Consolas", 13))
        self.input_box.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.input_box.bind("<Return>", self.send_message)
        ctk.CTkButton(bottom, text="SEND", command=self.send_message, width=100).pack(side="right", padx=10, pady=10)
        self.make_status_bar()

    def show_red_canvas(self):
        self.clear_content()
        self.make_title("RED CANVAS // IMAGE MISSION DESIGNER")
        frame = ctk.CTkFrame(self.content)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        controls = ctk.CTkFrame(frame, width=360)
        controls.pack(side="left", fill="y", padx=(0, 15), pady=10)
        preview = ctk.CTkFrame(frame)
        preview.pack(side="right", fill="both", expand=True, padx=(15, 0), pady=10)
        ctk.CTkLabel(controls, text="ENGINE", font=("Consolas", 12, "bold")).pack(pady=(15, 5))
        self.canvas_engine = ctk.CTkOptionMenu(controls, values=["Not Connected", "FLUX", "Stable Diffusion", "SDXL"], width=300)
        self.canvas_engine.pack(pady=5)
        ctk.CTkLabel(controls, text="PROMPT", font=("Consolas", 12, "bold")).pack(pady=(15, 5))
        self.canvas_prompt = ctk.CTkTextbox(controls, height=150, width=300, font=("Consolas", 12))
        self.canvas_prompt.pack(pady=5)
        ctk.CTkLabel(controls, text="NEGATIVE PROMPT", font=("Consolas", 12, "bold")).pack(pady=(15, 5))
        self.canvas_negative = ctk.CTkTextbox(controls, height=90, width=300, font=("Consolas", 12))
        self.canvas_negative.pack(pady=5)
        ctk.CTkLabel(controls, text="SIZE", font=("Consolas", 12, "bold")).pack(pady=(15, 5))
        self.canvas_size = ctk.CTkOptionMenu(controls, values=["1024x1024", "768x768", "512x512"], width=300)
        self.canvas_size.pack(pady=5)
        ctk.CTkButton(controls, text="SAVE PROMPT", command=self.save_canvas_prompt, width=300).pack(pady=(20, 5))
        ctk.CTkButton(controls, text="GENERATE // COMING SOON", width=300, state="disabled").pack(pady=5)
        ctk.CTkLabel(preview, text="IMAGE PREVIEW", font=("Consolas", 18, "bold")).pack(pady=(25, 10))
        ctk.CTkLabel(preview, text="Operation Red Canvas engine is not connected yet.\nPrompt design and archiving are online.", font=("Consolas", 14)).pack(pady=20)
        self.make_status_bar()

    def save_canvas_prompt(self):
        path = save_prompt(
            self.canvas_prompt.get("1.0", "end").strip(),
            self.canvas_negative.get("1.0", "end").strip(),
            self.canvas_engine.get(),
            self.canvas_size.get()
        )
        self.status.set("ARCHIVED")
        self.show_mission_console()
        self.add_chat("RED CANVAS", f"Prompt archived:\n{path}")

    def show_iron_library(self):
        ensure_library()
        self.clear_content()
        self.make_title("IRON LIBRARY // LOCAL DOCUMENT INTELLIGENCE")
        frame = ctk.CTkFrame(self.content)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        top = ctk.CTkFrame(frame)
        top.pack(fill="x", padx=10, pady=10)
        self.library_search = ctk.CTkEntry(top, placeholder_text="Search local TXT/MD/code files...", font=("Consolas", 13))
        self.library_search.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        ctk.CTkButton(top, text="SEARCH", command=self.run_library_search, width=120).pack(side="right", padx=10, pady=10)
        self.library_box = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 13))
        self.library_box.pack(fill="both", expand=True, padx=10, pady=10)
        docs = list_documents()
        self.library_box.insert("end", "IRON LIBRARY ONLINE\n\n")
        self.library_box.insert("end", f"Documents detected: {len(docs)}\n\n")
        self.library_box.insert("end", "Drop files into Library/Physics, Library/DnD, Library/Programming, Library/Manuals, or Library/Research.\n")
        self.library_box.insert("end", "Current support: TXT, MD, PY, JSON, INI, BAT, PS1. PDF support coming later.\n")
        self.make_status_bar()

    def run_library_search(self):
        query = self.library_search.get().strip()
        results = search_documents(query)
        self.library_box.delete("1.0", "end")
        self.library_box.insert("end", f"SEARCH: {query}\nRESULTS: {len(results)}\n\n")
        for path, snippet in results[:20]:
            self.library_box.insert("end", f"--- {path.name} ---\n{path}\n\n{snippet}\n\n")

    def show_archive(self):
        self.clear_content()
        self.make_title("MISSION ARCHIVE")
        box = ctk.CTkTextbox(self.content, wrap="word", font=("Consolas", 13))
        box.pack(fill="both", expand=True, padx=20, pady=20)
        box.insert("end", "Mission Archive browser coming soon.\n\nCurrent archives are saved in Mission Archive/Chats.")
        self.make_status_bar()

    def show_arsenal(self):
        self.clear_content()
        self.make_title("ARSENAL // SYSTEM CONFIGURATION")
        box = ctk.CTkTextbox(self.content, wrap="word", font=("Consolas", 13))
        box.pack(fill="both", expand=True, padx=20, pady=20)
        box.insert("end", f"Host: {self.host}\nPort: {self.port}\nThreads: {self.threads}\nContext: {self.context}\n\nModels detected: {len(self.models)}")
        self.make_status_bar()

    def add_chat(self, role, text):
        if not hasattr(self, "chat_box") or not self.chat_box.winfo_exists():
            self.show_mission_console()
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"\n[{role}]\n{text}\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")
        self.mission_memory.add(role, text)

    def start_ai(self):
        if self.server.is_running():
            self.status.set("ONLINE")
            return
        model_name = self.model_menu.get()
        model = next((m for m in self.models if m.name == model_name), None)
        if not model:
            self.add_chat("SYSTEM", "No neural engine selected.")
            return
        self.messages = []
        agent_name = self.agent_menu.get()
        agent_file = next((a for a in self.agents if a.name == agent_name), None)
        prompt = load_agent_prompt(agent_file)
        memory_context = (
            f"Operator name: {self.operator.get('operator_name', 'Eric Fox')}\n"
            f"Assistant name: {self.operator.get('assistant_name', 'Agent Fox')}\n"
            f"Current mission: {self.operator.get('current_mission', 'Operation Cyber Console')}\n"
            f"Project goal: {self.operator.get('project_goal', '')}\n"
        )
        self.messages.append({"role": "system", "content": prompt + "\n\n" + memory_context})
        try:
            started = self.server.start(model, host=self.host, port=self.port, context=self.context, threads=self.threads)
        except Exception as e:
            self.status.set("ERROR")
            self.add_chat("SYSTEM", f"Engine start error: {e}")
            return
        if started:
            self.status.set("BOOTING")
            self.add_chat("SYSTEM", f"Initializing neural engine: {model.name}")
            threading.Thread(target=self.wait_for_server, daemon=True).start()

    def wait_for_server(self):
        for _ in range(90):
            try:
                requests.get(f"http://{self.host}:{self.port}/health", timeout=1)
                self.status.set("ONLINE")
                name = self.operator.get("operator_name", "Operator")
                mission = self.operator.get("current_mission", "No active mission")
                self.add_chat("AGENT FOX", f"Good morning, {name}.\n\nAll systems operational.\nNeural engine online.\n\nMission:\n{mission}\n\nAwaiting your orders.")
                return
            except Exception:
                time.sleep(1)
        self.status.set("ERROR")
        self.add_chat("SYSTEM", "Neural engine failed to respond after 90 seconds.")

    def stop_ai(self):
        self.server.stop()
        self.status.set("OFFLINE")
        self.add_chat("SYSTEM", "Mission ended.")
        self.save_mission()

    def save_mission(self):
        path = self.mission_memory.save()
        if path:
            self.status.set("ARCHIVED")
            self.add_chat("SYSTEM", f"Mission archived:\n{path}")

    def send_message(self, event=None):
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            return "break"
        if not self.server.is_running():
            self.add_chat("SYSTEM", "Start mission first.")
            return "break"
        self.input_box.delete("1.0", "end")
        self.add_chat("ERIC", text)
        self.messages.append({"role": "user", "content": text})
        self.mission_memory.save()
        threading.Thread(target=self.get_ai_response, daemon=True).start()
        return "break"

    def get_ai_response(self):
        try:
            self.status.set("THINKING")
            payload = {
                "model": "local-model",
                "messages": self.messages,
                "temperature": 0.7,
                "max_tokens": 512,
                "stream": False
            }
            response = requests.post(self.api_url, json=payload, timeout=300)
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"].strip()
            self.messages.append({"role": "assistant", "content": answer})
            self.add_chat("AGENT FOX", answer)
            self.mission_memory.save()
            self.status.set("ONLINE")
        except Exception as e:
            self.status.set("ERROR")
            self.add_chat("SYSTEM", f"Error: {e}")

    def update_stats(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        current_status = self.status.get()
        if hasattr(self, "status_led") and self.status_led.winfo_exists():
            colors = {
                "ONLINE": "#00ff66",
                "THINKING": "#ffff00",
                "ERROR": "#ff0033",
                "BOOTING": "#00ccff",
                "ARCHIVED": "#00ccff",
                "OFFLINE": "#666666",
            }
            self.status_led.configure(text_color=colors.get(current_status, "#666666"))
        self.stats.set(f"CPU {cpu:.0f}%  |  RAM {ram.used / (1024 ** 3):.1f}/{ram.total / (1024 ** 3):.1f} GB  |  STATUS {current_status}")
        self.after(1000, self.update_stats)

    def on_close(self):
        if self.server.is_running():
            self.server.stop()
        self.mission_memory.save()
        self.destroy()
