import time
import threading
import configparser
import json
from pathlib import Path

import customtkinter as ctk
import psutil
import requests
from PIL import Image

from core.paths import CONFIG, ASSETS
from core.models import find_models
from core.agents import find_agents, load_agent_prompt, display_name
from core.memory import OperatorMemory, MissionMemory
from core.library import ensure_library, list_documents, search_documents
from core.red_canvas import save_prompt
from core.comfy_bridge import is_comfy_running, generate_image
from core.promptsmith import build_prompt
from core.image_models import find_checkpoints
from core.director import direct
from core.chat_agent import ChatAgent
from core.red_canvas_agent import RedCanvasAgent
from core.library_agent import LibraryAgent
from core.engineer_agent import EngineerAgent
from core.brainstem import Brainstem
from core.server import LlamaServer
from core import diagnostics
from core.chat_resilience import ChatResilience, ChatTimeoutError

try:
    from .foxai_theme import configure_ctk_identity, apply_foxai_theme, color
except Exception:
    from ui.foxai_theme import configure_ctk_identity, apply_foxai_theme, color

ctk.set_appearance_mode("dark")
configure_ctk_identity()


class FoxAIApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FOXAI Command OS // Ultimate Edifier Platform")
        self.icon_path = ASSETS / "foxai.ico"
        self.logo_path = ASSETS / "foxai_logo.png"
        if self.icon_path.exists():
            self.iconbitmap(str(self.icon_path))
        self.geometry("1220x720")
        self.minsize(1050, 700)

        self.server = LlamaServer(interface_name="Desktop")
        self.operator_memory = OperatorMemory()
        self.operator = self.operator_memory.load()
        self.mission_memory = MissionMemory()
        self.models = find_models()
        self.agents = find_agents()
        self.messages = []
        self.last_canvas_image = None
        self.mission_animation_job = None
        self.mission_animation_step = 0
        self._closing = False
        self.specialists = {
            "chat": ChatAgent(self),
            "red_canvas": RedCanvasAgent(self),
            "iron_library": LibraryAgent(self),
            "engineer": EngineerAgent(self),
        }

        self.config = self.load_config()
        self.host = self.config["Server"].get("host", "127.0.0.1")
        self.port = self.config["Server"].get("port", "8080")
        self.threads = self.config["Server"].get("threads", "12")
        self.context = self.config["Server"].get("context", "8192")
        self.api_url = f"http://{self.host}:{self.port}/v1/chat/completions"
        self.brainstem = Brainstem(self.host, self.port)
        self.chat_resilience = ChatResilience(self)
        self.long_think_after_seconds = 120
        self.chat_heartbeat_job = None
        self.chat_heartbeat_started_at = None
        self.chat_heartbeat_count = 0

        self.status = ctk.StringVar(value="OFFLINE")
        self.stats = ctk.StringVar(value="CPU -- | RAM -- | STATUS OFFLINE")
        self.build_ui()
        apply_foxai_theme(self)
        self.after(750, self._foxai_theme_watchdog)
        self.show_command_bridge()
        self.update_stats()
        self.protocol("WM_DELETE_WINDOW", self.on_close)


    def _foxai_theme_watchdog(self):
        if self._closing:
            return
        try:
            apply_foxai_theme(self)
        except Exception:
            pass
        self.after(1200, self._foxai_theme_watchdog)

    def read_bridge_feed(self):
        path = Path(__file__).resolve().parent.parent / "OpsBridge" / "outbox" / "bridge_feed.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                return None
        return None

    def show_command_bridge(self):
        self.clear_content()
        self.make_title("FOXAI COMMAND BRIDGE")
        feed = self.read_bridge_feed()

        outer = ctk.CTkScrollableFrame(self.content)
        outer.pack(fill="both", expand=True, padx=20, pady=15)

        hero = ctk.CTkFrame(outer)
        hero.pack(fill="x", padx=10, pady=(10, 15))

        identity = (feed or {}).get("identity", {})
        summary = (feed or {}).get("summary", {})
        kernel = (feed or {}).get("kernel", {})

        title = identity.get("name", "FOXAI Command OS")
        subtitle = identity.get("subtitle", "Ultimate Edifier Platform")
        kernel_status = kernel.get("status", "WAITING")

        ctk.CTkLabel(hero, text=title, font=("Consolas", 28, "bold"), text_color=color("purple_soft")).pack(pady=(18, 2))
        ctk.CTkLabel(hero, text=f"{subtitle}  //  Kernel: {kernel_status}", font=("Consolas", 14), text_color=color("muted")).pack(pady=(0, 18))

        metrics = ctk.CTkFrame(outer)
        metrics.pack(fill="x", padx=10, pady=(0, 15))
        for i in range(4):
            metrics.grid_columnconfigure(i, weight=1)

        metric_data = [
            ("Departments", summary.get("department_count", "—")),
            ("Online", summary.get("departments_online", "—")),
            ("Runtime Packages", summary.get("runtime_packages", "—")),
            ("Log Entries", summary.get("captains_log_entries", "—")),
        ]
        for i, (label, value) in enumerate(metric_data):
            card = ctk.CTkFrame(metrics)
            card.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            ctk.CTkLabel(card, text=label.upper(), font=("Consolas", 12, "bold"), text_color=color("muted")).pack(pady=(14, 4))
            ctk.CTkLabel(card, text=str(value), font=("Consolas", 24, "bold"), text_color=color("purple_soft")).pack(pady=(0, 14))

        dept_panel = ctk.CTkFrame(outer)
        dept_panel.pack(fill="x", padx=10, pady=(0, 15))
        ctk.CTkLabel(dept_panel, text="DEPARTMENTS", font=("Consolas", 16, "bold"), text_color=color("cyan")).pack(anchor="w", padx=14, pady=(12, 6))

        cards = (feed or {}).get("department_cards", [])
        if not cards:
            ctk.CTkLabel(dept_panel, text="Run BUILD_FOXAI.bat to generate OpsBridge\\outbox\\bridge_feed.json.", font=("Consolas", 13)).pack(anchor="w", padx=14, pady=(0, 14))
        else:
            grid = ctk.CTkFrame(dept_panel)
            grid.pack(fill="x", padx=10, pady=(0, 12))
            grid.grid_columnconfigure(0, weight=1)
            grid.grid_columnconfigure(1, weight=1)
            for i, card in enumerate(cards):
                panel = ctk.CTkFrame(grid)
                panel.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="nsew")
                status_color = color("green") if card.get("ok") else color("gold")
                ctk.CTkLabel(panel, text=card.get("title", "Department"), font=("Consolas", 15, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
                ctk.CTkLabel(panel, text=card.get("officer", "Unassigned"), font=("Consolas", 12), text_color=color("muted")).pack(anchor="w", padx=14)
                ctk.CTkLabel(panel, text=card.get("status", "UNKNOWN"), font=("Consolas", 13, "bold"), text_color=status_color).pack(anchor="w", padx=14, pady=(8, 12))

        mission_panel = ctk.CTkFrame(outer)
        mission_panel.pack(fill="x", padx=10, pady=(0, 15))
        ctk.CTkLabel(mission_panel, text="MISSION SNAPSHOT", font=("Consolas", 16, "bold"), text_color=color("cyan")).pack(anchor="w", padx=14, pady=(12, 6))
        latest_mission = summary.get("latest_mission") or "No recent mission."
        latest_event = summary.get("latest_event") or "Awaiting latest event."
        ctk.CTkLabel(mission_panel, text=f"Latest Mission: {latest_mission}\nLatest Event: {latest_event}", justify="left", font=("Consolas", 13)).pack(anchor="w", padx=14, pady=(0, 12))

        actions = ctk.CTkFrame(mission_panel)
        actions.pack(fill="x", padx=10, pady=(0, 12))
        ctk.CTkButton(actions, text="REFRESH BRIDGE", command=self.show_command_bridge, width=160).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(actions, text="MISSION CONSOLE", command=self.show_mission_console, width=170).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(actions, text="DIAGNOSTICS", command=self.show_diagnostics, width=150).pack(side="left", padx=8, pady=8)

        log_panel = ctk.CTkFrame(outer)
        log_panel.pack(fill="both", expand=True, padx=10, pady=(0, 15))
        ctk.CTkLabel(log_panel, text="CAPTAIN'S LOG", font=("Consolas", 16, "bold"), text_color=color("cyan")).pack(anchor="w", padx=14, pady=(12, 6))
        log_box = ctk.CTkTextbox(log_panel, wrap="word", height=220, font=("Consolas", 12))
        log_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        entries = ((feed or {}).get("captains_log") or {}).get("entries", [])[-8:]
        if entries:
            for entry in reversed(entries):
                log_box.insert("end", f"{entry.get('timestamp')} — {entry.get('source')}\n[{entry.get('severity')}] {entry.get('message')}\n\n")
        else:
            log_box.insert("end", "Captain's Log waiting for bridge feed.\n")
        log_box.configure(state="disabled")

        self.make_status_bar()
        try:
            apply_foxai_theme(self)
        except Exception:
            pass


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
        self.sidebar = ctk.CTkScrollableFrame(main, width=290)
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

        ctk.CTkLabel(self.sidebar, text="FOXAI COMMAND OS", font=("Consolas", 24, "bold"), text_color=color("purple_soft")).pack(pady=(5, 5))
        ctk.CTkLabel(self.sidebar, text="Ultimate Edifier Platform", font=("Consolas", 13), text_color=color("muted")).pack(pady=(0, 18))
        info = (
            f"OPERATOR: {self.operator.get('operator_name', 'Operator')}\n"
            f"ASSISTANT: {self.operator.get('assistant_name', 'Agent Fox')}\n"
            f"MISSION: {self.operator.get('current_mission', 'Operation Red Bridge')}"
        )
        ctk.CTkLabel(self.sidebar, text=info, justify="left", font=("Consolas", 12)).pack(pady=(0, 15), padx=12)

        ctk.CTkLabel(self.sidebar, text="NEURAL ENGINE", font=("Consolas", 12, "bold")).pack(pady=(5, 5))
        self.model_menu = ctk.CTkOptionMenu(self.sidebar, values=[m.name for m in self.models] or ["No engines found"], width=250)
        self.model_menu.pack(pady=5)

        ctk.CTkLabel(self.sidebar, text="AGENT", font=("Consolas", 12, "bold")).pack(pady=(12, 5))
        self.agent_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["🦊 Agent Fox"] + [display_name(a) for a in self.agents],
            width=250
        )
        self.agent_menu.pack(pady=5)
        ctk.CTkLabel(self.sidebar, text="DEPARTMENTS", font=("Consolas", 12, "bold")).pack(pady=(18, 8))

        self.command_bridge_button = ctk.CTkButton(self.sidebar, text="🚀 COMMAND BRIDGE", command=self.show_command_bridge, width=230)
        self.command_bridge_button.pack(pady=4)

        self.dashboard_button = ctk.CTkButton(self.sidebar, text="⌂ DASHBOARD", command=self.show_dashboard, width=230)
        self.dashboard_button.pack(pady=4)

        self.console_button = ctk.CTkButton(self.sidebar, text="> MISSION CONSOLE", command=self.show_mission_console, width=230)
        self.console_button.pack(pady=4)

        self.diagnostics_button = ctk.CTkButton(self.sidebar, text="🩺 DIAGNOSTICS", command=self.show_diagnostics, width=230)
        self.diagnostics_button.pack(pady=4)

        self.engineer_button = ctk.CTkButton(self.sidebar, text="🛠 ENGINEER", command=self.show_engineer, width=230)
        self.engineer_button.pack(pady=4)

        self.archive_button = ctk.CTkButton(self.sidebar, text="▣ MISSION ARCHIVE", command=self.show_archive, width=230)
        self.archive_button.pack(pady=4)

        self.library_button = ctk.CTkButton(self.sidebar, text="▤ IRON LIBRARY", command=self.show_iron_library, width=230)
        self.library_button.pack(pady=4)

        self.red_canvas_button = ctk.CTkButton(self.sidebar, text="◈ RED CANVAS", command=self.show_red_canvas, width=230)
        self.red_canvas_button.pack(pady=4)

        self.arsenal_button = ctk.CTkButton(self.sidebar, text="⚙ ARSENAL", command=self.show_arsenal, width=230)
        self.arsenal_button.pack(pady=4)

        ctk.CTkLabel(self.sidebar, text="MISSION CONTROL", font=("Consolas", 12, "bold")).pack(pady=(14, 8))

        self.start_button = ctk.CTkButton(self.sidebar, text="START MISSION", command=self.start_ai, width=230)
        self.start_button.pack(pady=4)

        self.end_button = ctk.CTkButton(self.sidebar, text="END MISSION", command=self.stop_ai, width=230)
        self.end_button.pack(pady=4)

        self.save_button = ctk.CTkButton(self.sidebar, text="SAVE MISSION", command=self.save_mission, width=230)
        self.save_button.pack(pady=4)

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
            ("CURRENT OPERATION", self.operator.get("current_mission", "Operation Red Bridge")),
            ("NEURAL ENGINES", str(len(self.models))),
            ("AGENTS", str(len(self.agents) + 1)),
            ("COMFYUI", "ONLINE" if is_comfy_running() else "OFFLINE"),
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
        self.send_button = ctk.CTkButton(bottom, text="SEND", command=self.send_message, width=100)
        self.send_button.pack(side="right", padx=10, pady=10)
        self.apply_workshop_state()
        self.make_status_bar()

    def show_red_canvas(self):
        self.clear_content()
        self.make_title("RED CANVAS // VISUAL OPERATIONS")
        frame = ctk.CTkFrame(self.content)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        controls = ctk.CTkScrollableFrame(frame, width=360)
        controls.pack(side="left", fill="y", padx=(0, 15), pady=10)
        preview = ctk.CTkFrame(frame)
        preview.pack(side="right", fill="both", expand=True, padx=(15, 0), pady=10)

        ctk.CTkLabel(controls, text="CHECKPOINT", font=("Consolas", 12, "bold")).pack(pady=(15, 5))
        self.canvas_checkpoint = ctk.CTkOptionMenu(
            controls,
            values=find_checkpoints(),
            width=300
        )
        self.canvas_checkpoint.pack(pady=5)

        ctk.CTkLabel(controls, text="STYLE", font=("Consolas", 12, "bold")).pack(pady=(12, 5))
        self.prompt_style = ctk.CTkOptionMenu(
            controls,
            values=["Fantasy", "Cyberpunk", "Creature Design", "Photorealistic"],
            width=300
        )
        self.prompt_style.pack(pady=5)

        ctk.CTkLabel(controls, text="QUALITY", font=("Consolas", 12, "bold")).pack(pady=(12, 5))
        self.prompt_quality = ctk.CTkOptionMenu(
            controls,
            values=["Fast", "Balanced", "Masterpiece"],
            width=300
        )
        self.prompt_quality.set("Masterpiece")
        self.prompt_quality.pack(pady=5)

        ctk.CTkLabel(controls, text="PROMPT", font=("Consolas", 12, "bold")).pack(pady=(15, 5))
        self.canvas_prompt = ctk.CTkTextbox(controls, height=145, width=300, font=("Consolas", 12))
        self.canvas_prompt.pack(pady=5)
        self.canvas_prompt.insert("1.0", "A humanoid Prototaxites wearing ornate medieval plate armor, glowing spores, cinematic lighting, fantasy concept art")

        ctk.CTkLabel(controls, text="NEGATIVE PROMPT", font=("Consolas", 12, "bold")).pack(pady=(15, 5))
        self.canvas_negative = ctk.CTkTextbox(controls, height=80, width=300, font=("Consolas", 12))
        self.canvas_negative.pack(pady=5)
        self.canvas_negative.insert("1.0", "blurry, low quality, watermark, text, deformed, extra limbs")

        ctk.CTkLabel(controls, text="SIZE", font=("Consolas", 12, "bold")).pack(pady=(15, 5))
        self.canvas_size = ctk.CTkOptionMenu(controls, values=["1024x1024", "768x768", "512x512"], width=300)
        self.canvas_size.pack(pady=5)

        ctk.CTkLabel(controls, text="SEED", font=("Consolas", 12, "bold")).pack(pady=(15, 5))
        self.canvas_seed = ctk.CTkEntry(controls, placeholder_text="Leave blank to use workflow seed", width=300)
        self.canvas_seed.pack(pady=5)

        self.promptsmith_button = ctk.CTkButton(controls, text="PROMPTSMITH", command=self.run_promptsmith, width=300)
        self.promptsmith_button.pack(pady=(20, 5))

        self.save_prompt_button = ctk.CTkButton(controls, text="SAVE PROMPT", command=self.save_canvas_prompt, width=300)
        self.save_prompt_button.pack(pady=5)

        self.generate_button = ctk.CTkButton(controls, text="GENERATE", command=self.generate_red_canvas, width=300)
        self.generate_button.pack(pady=5)
        self.apply_workshop_state()

        comfy_status = "ONLINE" if is_comfy_running() else "OFFLINE"
        self.canvas_status = ctk.CTkLabel(preview, text=f"COMFYUI STATUS: {comfy_status}\n\nReady for Operation Red Bridge.", font=("Consolas", 14))
        self.canvas_status.pack(pady=(20, 10))

        self.canvas_progress = ctk.CTkProgressBar(preview, width=460)
        self.canvas_progress.pack(pady=10)
        self.canvas_progress.set(0)

        self.preview_area = preview
        ctk.CTkLabel(preview, text="IMAGE PREVIEW", font=("Consolas", 18, "bold")).pack(pady=(20, 10))
        if self.last_canvas_image and self.last_canvas_image.exists():
            self.display_canvas_image(self.last_canvas_image, preview)
        else:
            ctk.CTkLabel(preview, text="Generated images will appear here.\nOutputs save to Red Canvas\\Outputs.", font=("Consolas", 14)).pack(pady=20)
        self.make_status_bar()

    def save_canvas_prompt(self):
        path = save_prompt(
            self.canvas_prompt.get("1.0", "end").strip(),
            self.canvas_negative.get("1.0", "end").strip(),
            self.canvas_checkpoint.get(),
            self.canvas_size.get()
        )
        self.status.set("ARCHIVED")
        self.show_mission_console()
        self.add_chat("RED CANVAS", f"Prompt archived:\n{path}")


    def run_promptsmith(self):
        simple_prompt = self.canvas_prompt.get("1.0", "end").strip()
        style = self.prompt_style.get()
        quality = self.prompt_quality.get()

        positive, negative = build_prompt(
            simple_prompt,
            style=style,
            quality=quality
        )

        self.canvas_prompt.delete("1.0", "end")
        self.canvas_prompt.insert("1.0", positive)

        self.canvas_negative.delete("1.0", "end")
        self.canvas_negative.insert("1.0", negative)

        self.status.set("PROMPTSMITH")
        self.canvas_status.configure(
            text=f"PROMPTSMITH COMPLETE\n\nStyle: {style}\nQuality: {quality}\nPrompt upgraded for Red Canvas."
        )


    def generate_red_canvas(self):
        if self.brainstem.is_busy() and self.brainstem.active_specialist != "Red Canvas":
            self.mission_status("MISSION LOCK ACTIVE\n\nAnother mission is already in progress.")
            return

        if not self.brainstem.is_busy():
            self.begin_workshop_mission("Creative", "Red Canvas")

        prompt = self.canvas_prompt.get("1.0", "end").strip()
        negative = self.canvas_negative.get("1.0", "end").strip()
        checkpoint = self.canvas_checkpoint.get()
        size = self.canvas_size.get()
        seed = self.canvas_seed.get().strip()
        if checkpoint == "Use workflow default":
            checkpoint = None
        try:
            width, height = [int(x) for x in size.lower().split("x")]
        except Exception:
            width, height = 1024, 1024

        save_prompt(prompt, negative, checkpoint or "workflow default", size)
        self.status.set("RENDERING")
        self.canvas_status.configure(text="MISSION ACCEPTED\n\nRendering through ComfyUI...\nCPU mode may take a while.")
        self.canvas_progress.set(0.15)
        threading.Thread(
            target=self._generate_red_canvas_thread,
            args=(prompt, negative, checkpoint, width, height, seed),
            daemon=True
        ).start()

    def _generate_red_canvas_thread(self, prompt, negative, checkpoint, width, height, seed):
        try:
            images = generate_image(prompt, negative, checkpoint, width, height, seed)
            if images:
                self.last_canvas_image = images[0]
                self.after(0, self._red_canvas_done, images[0])
            else:
                self.after(0, self._red_canvas_error, "No image returned from ComfyUI.")
        except Exception as e:
            self.after(0, self._red_canvas_error, str(e))

    def _red_canvas_done(self, image_path):
        self.stop_mission_animation("ONLINE")
        self.complete_workshop_mission("ONLINE")
        self.mission_status(f"Red Canvas mission complete.\n\nImage saved:\n{image_path}")
        self.show_red_canvas()
        if hasattr(self, "canvas_progress") and self.canvas_progress.winfo_exists():
            self.canvas_progress.set(1)
        if hasattr(self, "canvas_status") and self.canvas_status.winfo_exists():
            self.canvas_status.configure(text=f"MISSION COMPLETE\n\nImage saved:\n{image_path}")

    def _red_canvas_error(self, error_text):
        self.stop_mission_animation("ERROR")
        self.fail_workshop_mission(error_text)
        self.mission_status(f"Red Canvas error.\n\n{error_text}")
        if hasattr(self, "canvas_status") and self.canvas_status.winfo_exists():
            self.canvas_status.configure(text=f"RED BRIDGE ERROR:\n{error_text}")

    def display_canvas_image(self, image_path, parent):
        try:
            img = Image.open(image_path)
            img.thumbnail((560, 420))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            label = ctk.CTkLabel(parent, image=ctk_img, text="")
            label.image = ctk_img
            label.pack(pady=10)
            ctk.CTkLabel(parent, text=str(image_path), font=("Consolas", 11)).pack(pady=4)
        except Exception as e:
            ctk.CTkLabel(parent, text=f"Could not display image:\n{e}", font=("Consolas", 12)).pack(pady=10)


    def show_engineer(self):
        self.clear_content()
        self.make_title("ENGINEER // WORKSHOP CODE ANALYSIS")

        frame = ctk.CTkFrame(self.content)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        intro = (
            "Engineer is a read-only code and architecture specialist.\n\n"
            "Try:\n"
            "• review your own code\n"
            "• explain the architecture\n"
            "• find where Red Canvas is handled\n"
            "• search for diagnostics\n"
            "• where is the timeout defined\n\n"
            "Safety rule: Engineer does not modify files in this version."
        )

        ctk.CTkLabel(frame, text=intro, justify="left", font=("Consolas", 13)).pack(anchor="w", padx=15, pady=(15, 10))

        input_row = ctk.CTkFrame(frame)
        input_row.pack(fill="x", padx=15, pady=10)

        self.engineer_query = ctk.CTkEntry(input_row, placeholder_text="Ask Engineer about the FOXAI codebase...", font=("Consolas", 13))
        self.engineer_query.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)

        self.engineer_run_button = ctk.CTkButton(input_row, text="RUN ANALYSIS", command=self.run_engineer_query, width=150)
        self.engineer_run_button.pack(side="right", padx=(10, 0), pady=10)

        self.engineer_box = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 12))
        self.engineer_box.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.engineer_box.insert("end", "ENGINEER ONLINE\n\nAwaiting analysis request.")
        self.apply_workshop_state()
        self.make_status_bar()

    def run_engineer_query(self):
        if self.brainstem.is_busy():
            self.mission_status("MISSION LOCK ACTIVE\n\nEngineer cannot start while another mission is active.")
            return

        query = self.engineer_query.get().strip()
        if not query:
            return

        self.begin_workshop_mission("Engineering", "Engineer")
        self.mission_status("Engineer mission detected.\n\nReading project files in read-only mode.")

        result = self.specialists["engineer"].handle(query)

        if hasattr(self, "engineer_box") and self.engineer_box.winfo_exists():
            self.engineer_box.delete("1.0", "end")
            # The full report is already in Mission Control; show a concise confirmation here.
            self.engineer_box.insert("end", "Analysis complete.\n\nReport sent to Mission Control.")

        return result

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


    def _health_color(self, score):
        if score >= 90:
            return "#00ff66"
        if score >= 75:
            return "#ccff00"
        if score >= 50:
            return "#ffaa00"
        return "#ff0033"

    def _check_symbol(self, ok):
        return "✓" if ok else "⚠"

    def _format_check_line(self, check):
        symbol = self._check_symbol(check.get("ok"))
        name = check.get("name", "Unknown")
        status = check.get("status", "UNKNOWN")
        detail = check.get("detail", "")
        impact = check.get("impact", "")
        action = check.get("action", "")

        line = f"{symbol} {name}: {status}"
        if detail:
            line += f"\n    {detail}"
        if impact:
            line += f"\n    Impact: {impact}"
        if action:
            line += f"\n    Action: {action}"
        return line

    def show_diagnostics(self):
        self.clear_content()
        self.make_title("DIAGNOSTICS // WORKSHOP HEALTH")

        data = diagnostics.run_full_inspection(self)
        summary = data["summary"]
        hardware = data["hardware"]
        neural = data["neural"]
        creative = data["creative"]
        library = data["library"]
        advisor = data["advisor"]
        workshop = data["workshop"]

        outer = ctk.CTkScrollableFrame(self.content)
        outer.pack(fill="both", expand=True, padx=20, pady=15)

        health_frame = ctk.CTkFrame(outer)
        health_frame.pack(fill="x", padx=10, pady=(10, 15))

        score = summary["health_score"]
        label = summary["health_label"]

        ctk.CTkLabel(
            health_frame,
            text="WORKSHOP HEALTH",
            font=("Consolas", 16, "bold")
        ).pack(pady=(16, 4))

        ctk.CTkLabel(
            health_frame,
            text=f"{score}%",
            text_color=self._health_color(score),
            font=("Consolas", 46, "bold")
        ).pack(pady=(0, 0))

        ctk.CTkLabel(
            health_frame,
            text=f"{label}  |  {summary['checks_passed']}/{summary['checks_total']} checks passed",
            font=("Consolas", 14)
        ).pack(pady=(0, 16))

        grid = ctk.CTkFrame(outer)
        grid.pack(fill="x", padx=10, pady=10)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        def card(row, col, title, body):
            panel = ctk.CTkFrame(grid)
            panel.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
            ctk.CTkLabel(panel, text=title, font=("Consolas", 14, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
            ctk.CTkLabel(panel, text=body, font=("Consolas", 12), justify="left").pack(anchor="w", padx=14, pady=(0, 14))
            return panel

        brain = workshop["brainstem"]
        card(
            0,
            0,
            "BRAINSTEM",
            f"State: {brain.get('state')}\n"
            f"Busy: {brain.get('busy')}\n"
            f"Mission: {brain.get('active_mission') or 'Idle'}\n"
            f"Specialist: {brain.get('active_specialist') or 'None'}\n"
            f"Elapsed: {brain.get('elapsed_label')}"
        )

        card(
            0,
            1,
            "HARDWARE",
            f"CPU: {hardware['cpu_percent']:.0f}%\n"
            f"RAM: {hardware['ram_used_gb']} / {hardware['ram_total_gb']} GB ({hardware['ram_percent']}%)\n"
            f"Disk Free: {hardware['disk_free_gb']} GB\n"
            f"Uptime: {hardware['uptime']}"
        )

        card(
            1,
            0,
            "NEURAL ENGINE",
            f"Selected Model: {neural.get('selected_model') or 'None'}\n"
            f"Models Found: {neural['model_count']}\n"
            f"Server Alive: {neural['server_alive']}\n"
            f"Brainstem State: {neural['brainstem_state']}\n"
            f"Host: {self.host}:{self.port}\n"
            f"Threads: {self.threads}\n"
            f"Context: {self.context}"
        )

        card(
            1,
            1,
            "RED CANVAS",
            f"ComfyUI Online: {creative['comfy_online']}\n"
            f"Checkpoints: {creative['checkpoint_count']}\n"
            f"Workflow Found: {creative['workflow_exists']}\n"
            f"Output Folder: {creative['output_dir_exists']}"
        )

        card(
            2,
            0,
            "IRON LIBRARY",
            f"Documents Detected: {library['document_count']}\n"
            "Search Engine: Ready"
        )

        card(
            2,
            1,
            "WORKSHOP ADVISOR",
            f"Recommended Model:\n{advisor.get('recommended_model') or 'None'}\n\n"
            f"Recommended Threads: {advisor['recommended_threads']}\n"
            f"Context: {advisor['recommended_context']}\n"
            f"Reply Tokens: {advisor['recommended_reply_tokens']}\n\n"
            f"Reason:\n{advisor['reason']}"
        )

        checks_frame = ctk.CTkFrame(outer)
        checks_frame.pack(fill="both", expand=True, padx=10, pady=(15, 10))

        ctk.CTkLabel(
            checks_frame,
            text="FULL INSPECTION REPORT",
            font=("Consolas", 15, "bold")
        ).pack(anchor="w", padx=14, pady=(12, 4))

        report_box = ctk.CTkTextbox(checks_frame, wrap="word", font=("Consolas", 12), height=260)
        report_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        report_box.insert("end", "WORKSHOP CHECKS\n\n")
        for section_name in ["workshop", "neural", "creative", "library"]:
            report_box.insert("end", f"--- {section_name.upper()} ---\n")
            for check in data[section_name].get("checks", []):
                report_box.insert("end", self._format_check_line(check) + "\n\n")

        report_box.configure(state="disabled")

        actions = ctk.CTkFrame(outer)
        actions.pack(fill="x", padx=10, pady=(0, 15))
        ctk.CTkButton(actions, text="RUN FULL INSPECTION", command=self.show_diagnostics, width=220).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(actions, text="SEND REPORT TO MISSION CONTROL", command=self.send_diagnostics_to_mission_control, width=280).pack(side="left", padx=10, pady=10)

        self.make_status_bar()

    def send_diagnostics_to_mission_control(self):
        data = diagnostics.run_full_inspection(self)
        summary = data["summary"]
        advisor = data["advisor"]
        neural = data["neural"]
        creative = data["creative"]

        self.show_mission_console()
        self.mission_status(
            "WORKSHOP DIAGNOSTICS REPORT\n\n"
            f"Health: {summary['health_score']}% - {summary['health_label']}\n"
            f"Checks Passed: {summary['checks_passed']}/{summary['checks_total']}\n\n"
            f"Neural Engine Online: {neural['server_alive']}\n"
            f"ComfyUI Online: {creative['comfy_online']}\n\n"
            "Workshop Advisor Recommendation:\n"
            f"Model: {advisor.get('recommended_model') or 'None'}\n"
            f"Threads: {advisor['recommended_threads']}\n"
            f"Context: {advisor['recommended_context']}\n"
            f"Reply Tokens: {advisor['recommended_reply_tokens']}\n\n"
            f"Reason: {advisor['reason']}"
        )

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
        box.insert("end", f"Host: {self.host}\nPort: {self.port}\nThreads: {self.threads}\nContext: {self.context}\n\n")
        box.insert("end", self.chat_resilience.config.report() + "\n\n")
        box.insert("end", f"Language models detected: {len(self.models)}\nComfyUI: {'ONLINE' if is_comfy_running() else 'OFFLINE'}")
        self.make_status_bar()

    def add_chat(self, role, text, force_console=True):
        if force_console and (not hasattr(self, "chat_box") or not self.chat_box.winfo_exists()):
            self.show_mission_console()

        if hasattr(self, "chat_box") and self.chat_box.winfo_exists():
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"\n[{role}]\n{text}\n")
            self.chat_box.see("end")
            self.chat_box.configure(state="disabled")

        self.mission_memory.add(role, text)

    def mission_status(self, text):
        self.add_chat("MISSION CONTROL", text, force_console=False)

    def start_mission_animation(self, label="Processing mission"):
        self.stop_mission_animation(final_status=self.status.get())
        self.mission_animation_step = 0

        def animate():
            if self._closing:
                return

            dots = "." * ((self.mission_animation_step % 3) + 1)
            self.status.set("MISSION")
            self.mission_animation_step += 1

            if hasattr(self, "stats"):
                ram = psutil.virtual_memory()
                self.stats.set(
                    f"CPU {psutil.cpu_percent():.0f}%  |  RAM {ram.used / (1024 ** 3):.1f}/{ram.total / (1024 ** 3):.1f} GB  |  STATUS {label}{dots}"
                )

            self.mission_animation_job = self.after(500, animate)

        animate()

    def stop_mission_animation(self, final_status="ONLINE"):
        if self.mission_animation_job:
            try:
                self.after_cancel(self.mission_animation_job)
            except Exception:
                pass
            self.mission_animation_job = None

        self.status.set(final_status)


    def set_control_state(self, widget_name, state):
        widget = getattr(self, widget_name, None)
        if widget and widget.winfo_exists():
            try:
                widget.configure(state=state)
            except Exception:
                pass

    def apply_workshop_state(self):
        busy = self.brainstem.is_busy() if hasattr(self, "brainstem") else False
        locked = "disabled" if busy else "normal"

        for name in [
            "send_button",
            "generate_button",
            "promptsmith_button",
            "save_prompt_button",
            "library_button",
            "red_canvas_button",
            "arsenal_button",
            "archive_button",
            "diagnostics_button",
            "engineer_button",
        ]:
            self.set_control_state(name, locked)

        self.set_control_state("console_button", "normal")
        self.set_control_state("dashboard_button", "normal")
        self.set_control_state("diagnostics_button", "normal")
        self.set_control_state("end_button", "normal")
        self.set_control_state("save_button", "normal")
        self.set_control_state("start_button", "disabled" if busy else "normal")

    def begin_workshop_mission(self, mission_type, specialist):
        self.brainstem.begin_mission(mission_type, specialist)
        self.status.set("MISSION")
        self.apply_workshop_state()

    def complete_workshop_mission(self, final_status="ONLINE"):
        self.brainstem.complete_mission()
        self.status.set(final_status)
        self.apply_workshop_state()

    def fail_workshop_mission(self, error_text):
        self.brainstem.fail_mission(str(error_text))
        self.status.set("ERROR")
        self.apply_workshop_state()

    def format_director_analysis(self, mission):
        agent = mission.get("agent", "chat")
        scores = mission.get("scores", {})
        reasons = mission.get("reasons", [])

        department_names = {
            "chat": "Agent Fox",
            "red_canvas": "Red Canvas",
            "iron_library": "Iron Library",
            "engineer": "Engineer",
        }

        mission_names = {
            "chat": "Conversation",
            "red_canvas": "Creative",
            "iron_library": "Research",
            "engineer": "Engineering",
        }

        selected_score = scores.get(agent, 0)
        evidence = "\n".join(f"✓ {reason}" for reason in reasons[:8]) if reasons else "✓ default routing"

        return (
            "DIRECTOR ANALYSIS\n\n"
            f"Mission Type:\n{mission_names.get(agent, agent.title())}\n\n"
            f"Confidence Score:\n{selected_score}\n\n"
            f"Evidence:\n{evidence}\n\n"
            f"Selected Department:\n{department_names.get(agent, agent.title())}"
        )

    def start_ai(self):
        model_name = self.model_menu.get()
        model = next((m for m in self.models if m.name == model_name), None)
        if not model:
            self.add_chat("SYSTEM", "No neural engine selected.")
            return
        self.messages = []
        agent_name = self.agent_menu.get()
        agent_file = None

        if agent_name != "🦊 Agent Fox":
            agent_file = next(
                (a for a in self.agents if display_name(a) == agent_name or a.name == agent_name),
                 None
            )
        prompt = load_agent_prompt(agent_file)
        memory_context = (
            f"Operator name: {self.operator.get('operator_name', 'Eric Fox')}\n"
            f"Assistant name: {self.operator.get('assistant_name', 'Agent Fox')}\n"
            f"Current mission: {self.operator.get('current_mission', 'Operation Red Bridge')}\n"
            f"Project goal: {self.operator.get('project_goal', '')}\n"
        )
        self.messages.append({"role": "system", "content": prompt + "\n\n" + memory_context})

        result = self.server.ensure_running(
            model,
            host=self.host,
            port=self.port,
            context=self.context,
            threads=self.threads,
        )
        if not result.ok:
            self.status.set("ERROR")
            self.apply_workshop_state()
            self.add_chat("SYSTEM", result.message)
            return

        self.brainstem.set_state(self.brainstem.STATE_STARTING)
        self.status.set("BOOTING")
        self.apply_workshop_state()

        if result.action == "attached":
            self.add_chat(
                "SYSTEM",
                f"Attaching to shared neural engine: {model.name}",
            )
        elif result.action == "waiting":
            self.add_chat(
                "SYSTEM",
                f"Shared neural engine is already starting: {model.name}",
            )
        else:
            self.add_chat("SYSTEM", f"Initializing neural engine: {model.name}")

        threading.Thread(target=self.wait_for_server, daemon=True).start()

    def wait_for_server(self):
        ready = self.server.wait_until_ready(timeout=90)
        if ready.ok:
            self.brainstem.set_state(self.brainstem.STATE_READY)
            self.status.set("ONLINE")
            self.after(0, self.apply_workshop_state)
            name = self.operator.get("operator_name", "Operator")
            mission = self.operator.get("current_mission", "No active mission")
            self.add_chat(
                "AGENT FOX",
                f"Good morning, {name}.\n\n"
                "All systems operational.\n"
                "Shared neural engine online.\n\n"
                f"Mission:\n{mission}\n\n"
                "Awaiting your orders.",
            )
            return

        self.brainstem.set_error(ready.message)
        self.status.set("ERROR")
        self.after(0, self.apply_workshop_state)
        self.add_chat("SYSTEM", ready.message)

    def stop_ai(self):
        self.stop_chat_heartbeat()
        result = self.server.stop()
        self.brainstem.set_state(self.brainstem.STATE_OFFLINE)
        self.status.set("OFFLINE" if result.ok else "ERROR")
        self.apply_workshop_state()
        self.add_chat("SYSTEM", result.message)
        self.add_chat("SYSTEM", "Mission ended.")
        self.save_mission()

    def save_mission(self):
        path = self.mission_memory.save()
        if path:
            self.status.set("ARCHIVED")
            self.add_chat("SYSTEM", f"Mission archived:\n{path}")





    def send_message(self, event=None):
        if self.brainstem.is_busy():
            self.mission_status(
                "MISSION LOCK ACTIVE\n\n"
                f"Current Specialist: {self.brainstem.active_specialist}\n"
                f"Elapsed: {self.brainstem.elapsed_label()}\n\n"
                "Please wait for the active mission to complete."
            )
            return "break"

        text = self.input_box.get("1.0", "end").strip()

        if not text:
            return "break"

        self.mission_status("Receiving request...\n\nDirector analyzing mission parameters.")
        self.start_mission_animation("Director analyzing")

        mission = direct(text)
        agent = mission["agent"]
        payload = mission["payload"]

        self.mission_status(self.format_director_analysis(mission))

        if agent in self.specialists:
            if agent == "red_canvas":
                self.begin_workshop_mission("Creative", "Red Canvas")
                self.mission_status("Red Canvas mission detected.\n\nDeploying PromptSmith and image bridge.")
                return self.specialists[agent].handle(text, payload)

            if agent == "engineer":
                self.begin_workshop_mission("Engineering", "Engineer")
                self.mission_status("Engineer mission detected.\n\nReading project files in read-only mode.")
                return self.specialists[agent].handle(payload)

            if agent == "iron_library":
                self.begin_workshop_mission("Research", "Iron Library")
                self.mission_status("Iron Library mission detected.\n\nSearching local files and project knowledge.")
                result = self.specialists[agent].handle(payload)
                self.complete_workshop_mission("ONLINE")
                return result

            self.begin_workshop_mission("Conversation", "Agent Fox")
            self.mission_status("Chat mission detected.\n\nRouting to selected neural specialist.")
            result = self.specialists[agent].handle(payload)
            self.status.set("THINKING")
            return result

        self.fail_workshop_mission(f"No specialist found for mission agent: {agent}")
        self.add_chat("SYSTEM", f"No specialist found for mission agent: {agent}")
        return "break"

    def route_image_request(self, original_text, image_prompt):
        self.add_chat("ERIC", original_text)
        self.add_chat(
            "DIRECTOR",
            "🎨 Image request detected.\n\n"
            "Routing to Red Canvas...\n"
            "Running PromptSmith...\n"
            "Starting render..."
        )
        self.mission_status("Red Canvas online.\n\nPromptSmith preparing visual mission packet.")

        self.show_red_canvas()
        self.canvas_prompt.delete("1.0", "end")
        self.canvas_prompt.insert("1.0", image_prompt)
        self.run_promptsmith()
        self.mission_status("PromptSmith complete.\n\nSending render request to ComfyUI.")
        self.generate_red_canvas()


    def start_chat_heartbeat(self, model_name=None, mission_type="conversation"):
        self.stop_chat_heartbeat()
        self.chat_heartbeat_started_at = time.time()
        self.chat_heartbeat_count = 0

        def heartbeat():
            if self._closing:
                return

            if not self.brainstem.is_busy() and self.brainstem.state != getattr(self.brainstem, "STATE_LONG_THINK", "LONG_THINK"):
                return

            elapsed = int(time.time() - self.chat_heartbeat_started_at)
            timeout = self.chat_resilience.timeout_for(mission_type=mission_type)

            if elapsed >= self.long_think_after_seconds and self.brainstem.state != getattr(self.brainstem, "STATE_LONG_THINK", "LONG_THINK"):
                if hasattr(self.brainstem, "enter_long_think"):
                    self.brainstem.enter_long_think(timeout_seconds=timeout)
                self.status.set("LONG_THINK")
                self.mission_status(
                    "LONG THINK MODE ENGAGED\n\n"
                    "The neural engine is still reasoning through a complex request.\n\n"
                    f"Elapsed: {self.brainstem.elapsed_label()}\n"
                    f"Model: {model_name or self.model_menu.get()}\n"
                    f"Configured Timeout: {timeout} seconds\n\n"
                    "No fault detected. Continue waiting unless you want to end the mission."
                )

            if hasattr(self.brainstem, "touch_heartbeat"):
                self.brainstem.touch_heartbeat()

            if elapsed >= self.long_think_after_seconds:
                self.chat_heartbeat_count += 1

                messages = [
                    "Neural engine continues reasoning.",
                    "Complex request still in progress.",
                    "No fault detected. Reasoning continues.",
                    "Large-context mission still active.",
                    "Workshop heartbeat confirmed.",
                ]
                note = messages[self.chat_heartbeat_count % len(messages)]

                self.mission_status(
                    "MISSION HEARTBEAT\n\n"
                    f"{note}\n\n"
                    f"Elapsed: {self.brainstem.elapsed_label()}\n"
                    f"Heartbeat: {self.chat_heartbeat_count}\n"
                    f"Model: {model_name or self.model_menu.get()}\n"
                    f"State: {self.brainstem.state}"
                )

            self.chat_heartbeat_job = self.after(
                self.chat_resilience.config.heartbeat_interval_seconds * 1000,
                heartbeat
            )

        self.chat_heartbeat_job = self.after(
            self.chat_resilience.config.heartbeat_interval_seconds * 1000,
            heartbeat
        )

    def stop_chat_heartbeat(self):
        if self.chat_heartbeat_job:
            try:
                self.after_cancel(self.chat_heartbeat_job)
            except Exception:
                pass
            self.chat_heartbeat_job = None

        self.chat_heartbeat_started_at = None
        self.chat_heartbeat_count = 0

    def get_ai_response(self):
        try:
            self.status.set("THINKING")
            model_used = self.model_menu.get()

            payload = {
                "model": "local-model",
                "messages": self.messages,
                "temperature": 0.7,
                "max_tokens": 2048,
                "stream": False
            }

            self.after(0, lambda: self.start_chat_heartbeat(model_name=model_used, mission_type="conversation"))

            response = self.chat_resilience.post_json(
                self.api_url,
                payload,
                mission_type="conversation",
                long_think=False,
                model_name=model_used,
            )

            answer = response.json()["choices"][0]["message"]["content"].strip()

            if not answer:
                answer = "[BLANK RESPONSE]\nThe model returned no text. Try restarting the mission or lowering context/max tokens."

            answer = f"[Model: {model_used}]\n\n{answer}"
            self.messages.append({"role": "assistant", "content": answer})
            self.add_chat("AGENT FOX", answer)
            self.mission_memory.save()
            self.after(0, self.stop_chat_heartbeat)
            self.stop_mission_animation("ONLINE")
            self.complete_workshop_mission("ONLINE")

        except ChatTimeoutError as e:
            self.after(0, self.stop_chat_heartbeat)
            self.stop_mission_animation("ERROR")
            self.fail_workshop_mission(str(e))
            self.add_chat("MISSION CONTROL", str(e))

        except Exception as e:
            self.after(0, self.stop_chat_heartbeat)
            self.stop_mission_animation("ERROR")
            self.fail_workshop_mission(str(e))
            self.add_chat(
                "MISSION CONTROL",
                "The neural engine returned an unexpected error.\n\n"
                f"Details:\n{e}\n\n"
                "Recommended actions:\n"
                "• Retry the request.\n"
                "• Restart the neural engine if the error repeats.\n"
                "• Try a smaller model or shorter response."
            )

    def update_stats(self):
        if self._closing:
            return

        try:
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
                    "RENDERING": "#ff0033",
                    "PROMPTSMITH": "#ff00ff",
                    "MISSION": "#00ccff",
                    "LONG_THINK": "#ffcc00",
                    "OFFLINE": "#666666"
                }
                self.status_led.configure(text_color=colors.get(current_status, "#666666"))
            if hasattr(self, "brainstem") and self.brainstem.is_busy():
                self.stats.set(
                    f"CPU {cpu:.0f}%  |  RAM {ram.used / (1024 ** 3):.1f}/{ram.total / (1024 ** 3):.1f} GB  |  "
                    f"MISSION {self.brainstem.active_specialist}  |  ELAPSED {self.brainstem.elapsed_label()}"
                )
            else:
                self.stats.set(
                    f"CPU {cpu:.0f}%  |  RAM {ram.used / (1024 ** 3):.1f}/{ram.total / (1024 ** 3):.1f} GB  |  STATUS {current_status}"
                )
            self.after(1000, self.update_stats)
        except Exception:
            return

    def on_close(self):
        self._closing = True
        self.stop_chat_heartbeat()
        self.stop_mission_animation("OFFLINE")
        self.server.release()
        self.mission_memory.save()
        self.destroy()
