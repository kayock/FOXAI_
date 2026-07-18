import time
import threading
import configparser
import json
import re
import tkinter as tk
from tkinter import messagebox
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
from core.application_registry import ApplicationRegistry
from core.comfy_ops_monitor import comfy_operations_snapshot
from core.security_containment import (
    new_airlock_correlation_id,
    record_trip_sentry_test_event,
    redact_mapping,
    verify_airlock_audit_log,
    airlock_chain_alert,
)
from uuid import uuid4

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
        self._mission_context_menus = []
        self.comfy_ops_window = None
        self.comfy_ops_refresh_job = None
        self.red_canvas_progress_job = None
        self.red_canvas_active = False
        self.red_canvas_progress_percent = 0
        self.red_canvas_progress_text = ""
        self.red_canvas_log_path = None
        self.red_canvas_log_offset = 0
        self.red_canvas_log_buffer = ""
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

        self.trip_sentry_button = ctk.CTkButton(
            self.sidebar,
            text="⚠ TRIP SENTRY TEST",
            command=self.show_trip_sentry,
            width=230,
            fg_color="#8f2038",
            hover_color="#b52b4a",
        )
        self.trip_sentry_button.pack(pady=4)

        self.engineer_button = ctk.CTkButton(self.sidebar, text="🛠 ENGINEER", command=self.show_engineer, width=230)
        self.engineer_button.pack(pady=4)

        self.archive_button = ctk.CTkButton(self.sidebar, text="▣ MISSION ARCHIVE", command=self.show_archive, width=230)
        self.archive_button.pack(pady=4)

        self.library_button = ctk.CTkButton(self.sidebar, text="▤ IRON LIBRARY", command=self.show_iron_library, width=230)
        self.library_button.pack(pady=4)

        self.red_canvas_button = ctk.CTkButton(self.sidebar, text="◈ RED CANVAS", command=self.show_red_canvas, width=230)
        self.red_canvas_button.pack(pady=4)

        self.comfy_ops_button = ctk.CTkButton(
            self.sidebar,
            text="▸ COMFYUI OPERATIONS",
            command=self.show_comfy_operations,
            width=230,
        )
        self.comfy_ops_button.pack(pady=4)

        self.arsenal_button = ctk.CTkButton(self.sidebar, text="⚙ ARSENAL", command=self.show_arsenal, width=230)
        self.arsenal_button.pack(pady=4)

        ctk.CTkLabel(self.sidebar, text="MISSION CONTROL", font=("Consolas", 12, "bold")).pack(pady=(14, 8))

        self.start_button = ctk.CTkButton(self.sidebar, text="START MISSION", command=self.start_ai, width=230)
        self.start_button.pack(pady=4)

        self.end_button = ctk.CTkButton(self.sidebar, text="END MISSION", command=self.stop_ai, width=230)
        self.end_button.pack(pady=4)

        self.save_button = ctk.CTkButton(self.sidebar, text="SAVE MISSION", command=self.save_mission, width=230)
        self.save_button.pack(pady=4)

    def show_comfy_operations(self):
        """Open the lightweight read-only ComfyUI operations viewer."""
        if self.comfy_ops_window is not None:
            try:
                if self.comfy_ops_window.winfo_exists():
                    self.comfy_ops_window.deiconify()
                    self.comfy_ops_window.lift()
                    self.comfy_ops_window.focus_force()
                    return
            except Exception:
                pass

        window = ctk.CTkToplevel(self)
        self.comfy_ops_window = window
        window.title("FOXAI // ComfyUI Operations")
        window.geometry("920x560")
        window.minsize(700, 420)
        window.protocol("WM_DELETE_WINDOW", self.hide_comfy_operations)

        header = ctk.CTkFrame(window)
        header.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(
            header,
            text="COMFYUI OPERATIONS",
            font=("Consolas", 20, "bold"),
            text_color="#42ff9e",
        ).pack(side="left", padx=12, pady=10)

        self.comfy_ops_status_var = ctk.StringVar(value="CHECKING")
        ctk.CTkLabel(
            header,
            textvariable=self.comfy_ops_status_var,
            font=("Consolas", 14, "bold"),
            text_color="#42ff9e",
        ).pack(side="right", padx=12, pady=10)

        self.comfy_ops_progress = ctk.CTkProgressBar(window)
        self.comfy_ops_progress.pack(fill="x", padx=18, pady=(2, 8))
        self.comfy_ops_progress.set(0)

        details = ctk.CTkFrame(window)
        details.pack(fill="x", padx=12, pady=(0, 6))
        self.comfy_ops_details_var = ctk.StringVar(
            value="Endpoint: 127.0.0.1:8188"
        )
        ctk.CTkLabel(
            details,
            textvariable=self.comfy_ops_details_var,
            justify="left",
            anchor="w",
            font=("Consolas", 12),
        ).pack(fill="x", padx=12, pady=8)

        self.comfy_ops_text = ctk.CTkTextbox(
            window,
            wrap="none",
            font=("Consolas", 12),
            text_color="#42ff9e",
            fg_color="#030805",
        )
        self.comfy_ops_text.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 8),
        )
        self.comfy_ops_text.insert(
            "end",
            "Waiting for ComfyUI output. This panel is read-only.\n",
        )
        self.comfy_ops_text.configure(state="disabled")

        controls = ctk.CTkFrame(window)
        controls.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(
            controls,
            text="REFRESH",
            width=120,
            command=self._refresh_comfy_operations,
        ).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(
            controls,
            text="OPEN COMFYUI",
            width=150,
            command=lambda: __import__("webbrowser").open(
                "http://127.0.0.1:8188"
            ),
        ).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(
            controls,
            text="HIDE",
            width=100,
            command=self.hide_comfy_operations,
        ).pack(side="right", padx=8, pady=8)

        self._refresh_comfy_operations()

    def hide_comfy_operations(self):
        if self.comfy_ops_refresh_job is not None:
            try:
                self.after_cancel(self.comfy_ops_refresh_job)
            except Exception:
                pass
            self.comfy_ops_refresh_job = None

        if self.comfy_ops_window is not None:
            try:
                if self.comfy_ops_window.winfo_exists():
                    self.comfy_ops_window.withdraw()
            except Exception:
                self.comfy_ops_window = None

    def _refresh_comfy_operations(self):
        if self._closing:
            return

        window = self.comfy_ops_window
        try:
            if (
                window is None
                or not window.winfo_exists()
                or not window.winfo_viewable()
            ):
                return
        except Exception:
            return

        try:
            snapshot = comfy_operations_snapshot(
                Path(__file__).resolve().parents[1],
                line_limit=140,
            )
            state = str(snapshot.get("state") or "UNKNOWN")
            progress = snapshot.get("progress_percent")
            online = bool(snapshot.get("online"))
            log_path = str(
                snapshot.get("log_path") or "No live log located"
            )
            updated = str(snapshot.get("log_modified") or "—")
            tail = str(snapshot.get("tail") or "")
            message = str(snapshot.get("message") or "")

            self.comfy_ops_status_var.set(
                f"{state}"
                + (
                    f"  {progress}%"
                    if isinstance(progress, int)
                    else ""
                )
            )
            self.comfy_ops_progress.set(
                max(0.0, min(1.0, (progress or 0) / 100.0))
            )
            self.comfy_ops_details_var.set(
                f"Endpoint: 127.0.0.1:8188  |  "
                f"Health: {'ONLINE' if online else 'OFFLINE'}\n"
                f"Log: {log_path}\nUpdated: {updated}"
            )

            display = (
                tail
                or message
                or "No ComfyUI console output has been captured yet."
            )
            self.comfy_ops_text.configure(state="normal")
            self.comfy_ops_text.delete("1.0", "end")
            self.comfy_ops_text.insert("end", display)
            self.comfy_ops_text.see("end")
            self.comfy_ops_text.configure(state="disabled")
        except Exception as exc:
            try:
                self.comfy_ops_status_var.set("MONITOR ERROR")
                self.comfy_ops_text.configure(state="normal")
                self.comfy_ops_text.delete("1.0", "end")
                self.comfy_ops_text.insert(
                    "end",
                    f"ComfyUI monitor error: "
                    f"{type(exc).__name__}: {exc}",
                )
                self.comfy_ops_text.configure(state="disabled")
            except Exception:
                pass

        self.comfy_ops_refresh_job = self.after(
            750,
            self._refresh_comfy_operations,
        )

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


    def _load_application_registry_health(self):
        registry = ApplicationRegistry(
            root=Path(__file__).resolve().parents[1],
            timeout=0.6,
        )
        return registry.snapshot()

    def _format_application_registry_health(self, snapshot):
        if snapshot.get("error"):
            return (
                "APPLICATION REGISTRY & HEALTH\n\n"
                "State: UNKNOWN\n"
                f"Reason: {snapshot.get('error')}\n\n"
                "Telemetry only. No Fox Sentry incident was generated."
            )

        summary = snapshot.get("summary") or {}
        applications = snapshot.get("applications") or []
        lines = [
            "APPLICATION REGISTRY & HEALTH",
            "",
            "Boundary: TELEMETRY ONLY — health changes do not create incidents.",
            f"Generated: {snapshot.get('generated_at', '')}",
            f"Canonical Apps: {summary.get('canonical', 0)}",
            f"Fleet Extensions: {summary.get('fleet', 0)}",
            f"Online: {summary.get('online', 0)}",
            f"Ready: {summary.get('ready', 0)}",
            f"Attention: {summary.get('attention', 0)}",
            f"Planned: {summary.get('planned', 0)}",
            "",
        ]

        current_department = None
        for application in applications:
            department = application.get("department") or "Unassigned"
            if department != current_department:
                if current_department is not None:
                    lines.append("")
                lines.append(f"[{department.upper()}]")
                current_department = department

            latency = application.get("latency_ms")
            latency_text = (
                f" // {latency:.1f} ms"
                if isinstance(latency, (int, float))
                else ""
            )
            source_label = "FLEET" if application.get("source") == "fleet" else "APP"
            lines.extend([
                (
                    f"{source_label} [{application.get('status', 'UNKNOWN')}] "
                    f"{application.get('name', application.get('id', 'Unknown'))}"
                    f"{latency_text}"
                ),
                (
                    f"  Lifecycle: {str(application.get('lifecycle', '')).upper()} "
                    f"// Kind: {application.get('kind', 'application')}"
                ),
                f"  {application.get('message', '')}",
            ])

        return "\n".join(lines)

    def refresh_application_registry_health(self):
        try:
            snapshot = self._load_application_registry_health()
            summary = snapshot.get("summary") or {}
            status_text = (
                "REGISTRY READY // "
                f"{summary.get('canonical', 0)} app(s), "
                f"{summary.get('fleet', 0)} fleet extension(s), "
                f"{summary.get('attention', 0)} attention state(s). "
                "Telemetry only."
            )
        except Exception as exc:
            snapshot = {
                "error": f"{type(exc).__name__}: {exc}",
                "applications": [],
                "summary": {},
            }
            status_text = (
                "REGISTRY UNKNOWN // Passive health refresh failed safely. "
                "No incident was generated."
            )

        if hasattr(self, "application_registry_status"):
            self.application_registry_status.set(status_text)

        if hasattr(self, "application_registry_box"):
            self.application_registry_box.configure(state="normal")
            self.application_registry_box.delete("1.0", "end")
            self.application_registry_box.insert(
                "end",
                self._format_application_registry_health(snapshot),
            )
            self.application_registry_box.configure(state="disabled")
        return snapshot

    def _fox_sentry_audit_log_path(self):
        return (
            Path(__file__).resolve().parents[1]
            / "Logs"
            / "Security"
            / "engineering_airlock_events.jsonl"
        )

    def _fox_sentry_event_severity(self, event):
        stored = str(event.get("severity") or "").strip().upper()
        if stored:
            return stored
        return "TEST" if bool(event.get("test_event")) else "LEGACY"


    def _fox_sentry_event_incident_kind(self, event):
        stored = str(event.get("incident_kind") or "").strip()
        return stored or (
            "trip_sentry_test"
            if bool(event.get("test_event"))
            else "legacy_unclassified"
        )

    def _load_fox_sentry_incidents(self, incident_filter="ALL", limit=100):
        log_path = self._fox_sentry_audit_log_path()
        verification = verify_airlock_audit_log(log_path)
        result = {
            "log_path": str(log_path),
            "exists": log_path.exists(),
            "verification": verification,
            "events": [],
            "redactions": 0,
            "read_error": "",
        }
        if not log_path.exists():
            return result

        try:
            lines = log_path.read_text(
                encoding="utf-8",
                errors="strict",
            ).splitlines()
        except Exception as exc:
            result["read_error"] = f"{type(exc).__name__}: {exc}"
            return result

        events = []
        redactions = 0
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            clean_event, count = redact_mapping(event)
            clean_event["_line_number"] = line_number
            redactions += count
            events.append(clean_event)

        selected = str(incident_filter or "ALL").strip().upper()
        if selected == "TEST":
            events = [event for event in events if bool(event.get("test_event"))]
        elif selected == "OPERATIONAL":
            events = [event for event in events if not bool(event.get("test_event"))]
        elif selected in {"INFO", "NOTICE", "WARNING", "CRITICAL"}:
            events = [
                event for event in events
                if self._fox_sentry_event_severity(event) == selected
            ]

        try:
            bounded_limit = max(1, min(int(limit), 500))
        except Exception:
            bounded_limit = 100

        result["events"] = list(reversed(events))[:bounded_limit]
        result["redactions"] = redactions
        return result

    @staticmethod
    def _short_sentry_hash(value):
        text = str(value or "")
        if len(text) <= 18:
            return text
        return f"{text[:10]}…{text[-8:]}"

    def _format_fox_sentry_incidents(self, result):
        verification = result.get("verification") or {}
        chain_valid = bool(verification.get("valid"))
        chain_alert = airlock_chain_alert(verification)
        events = result.get("events") or []
        lines = [
            "FOX SENTRY INCIDENT VIEWER",
            "",
            f"Chain Status: {'VERIFIED' if chain_valid else 'INVALID — UNTRUSTED'}",
            f"Total Chained Events: {verification.get('event_count', 0)}",
            f"Visible Events: {len(events)}",
            f"Final Chain Hash: {self._short_sentry_hash(verification.get('final_hash'))}",
            f"Log: {result.get('log_path', '')}",
        ]
        if chain_alert.get("active"):
            lines.extend([
                "",
                "[CRITICAL] AUDIT CHAIN INVALID — FOX SENTRY FAIL-CLOSED",
                str(chain_alert.get("message") or "Audit chain verification failed."),
                "This is a synthetic viewer state. Nothing was appended to the untrusted chain.",
            ])
        if result.get("read_error"):
            lines.extend(["", f"READ FAILED CLOSED: {result['read_error']}"])
        failures = verification.get("failures") or []
        if failures:
            lines.extend(["", "CHAIN VERIFICATION FAILURES:"])
            for failure in failures[:10]:
                lines.append(
                    f"• Line {failure.get('line', '?')}: "
                    f"{failure.get('reason', 'unknown failure')}"
                )

        if not result.get("exists"):
            lines.extend([
                "",
                "No audit log exists yet.",
                "Run Trip Sentry or enter the Engineering Airlock to create the first event.",
            ])
            return "\n".join(lines)

        if not events:
            lines.extend(["", "No incidents match the selected filter."])
            return "\n".join(lines)

        lines.extend(["", "MOST RECENT FIRST", ""])
        for event in events:
            severity = self._fox_sentry_event_severity(event)
            incident_kind = self._fox_sentry_event_incident_kind(event)
            event_kind = "TEST" if event.get("test_event") else "OPERATIONAL"
            verified_label = "CHAINED" if chain_valid else "UNTRUSTED"
            attempt_count = event.get("attempt_count")
            context_status = str(event.get("context_status") or "legacy").upper()
            lines.extend([
                (
                    f"[{severity}] [{event_kind}] [{verified_label}] "
                    f"{event.get('timestamp', 'unknown time')}"
                ),
                f"Incident Kind: {incident_kind}",
                f"Decision: {str(event.get('decision', '')).upper()}",
                f"Attempt Count: {attempt_count if attempt_count is not None else 'LEGACY'}",
                f"Context Status: {context_status}",
                f"Actor: {event.get('actor', '')}",
                f"Object: {event.get('object', '')}",
                f"Action: {event.get('action', '')}",
                f"Reason: {event.get('reason', '')}",
                f"Policy: {event.get('policy_source', '')}",
                f"Event ID: {event.get('event_id', '')}",
                f"Correlation ID: {event.get('correlation_id', '')}",
                f"Mission ID: {event.get('mission_id', '')}",
                f"Approval ID: {event.get('approval_id', '')}",
                f"Receipt ID: {event.get('receipt_id', '')}",
                f"Previous Hash: {self._short_sentry_hash(event.get('previous_hash'))}",
                f"Event Hash: {self._short_sentry_hash(event.get('event_hash'))}",
                "-" * 70,
            ])
        return "\n".join(lines)

    def refresh_fox_sentry_incidents(self):
        incident_filter = (
            self.fox_sentry_incident_filter.get()
            if hasattr(self, "fox_sentry_incident_filter")
            else "ALL"
        )
        result = self._load_fox_sentry_incidents(incident_filter, limit=100)
        verification = result.get("verification") or {}
        chain_valid = bool(verification.get("valid"))

        if hasattr(self, "fox_sentry_chain_status"):
            if chain_valid:
                self.fox_sentry_chain_status.set(
                    "CHAIN VERIFIED // "
                    f"{verification.get('event_count', 0)} append-only event(s)."
                )
            else:
                self.fox_sentry_chain_status.set(
                    "CRITICAL // CHAIN INVALID // Fox Sentry is fail-closed and incidents are untrusted."
                )

        if hasattr(self, "fox_sentry_incident_box"):
            self.fox_sentry_incident_box.configure(state="normal")
            self.fox_sentry_incident_box.delete("1.0", "end")
            self.fox_sentry_incident_box.insert(
                "end",
                self._format_fox_sentry_incidents(result),
            )
            self.fox_sentry_incident_box.configure(state="disabled")
        return result

    def show_trip_sentry(self):
        self.clear_content()
        self.make_title("FOX SENTRY // TRIP SENTRY")

        outer = ctk.CTkScrollableFrame(self.content)
        outer.pack(fill="both", expand=True, padx=20, pady=15)

        warning = ctk.CTkFrame(
            outer,
            border_width=2,
            border_color="#ff4d6d",
            fg_color="#220b12",
        )
        warning.pack(fill="x", padx=10, pady=(10, 15))

        ctk.CTkLabel(
            warning,
            text="Ω  OMEGA PROTOCOL  //  TEST MODE",
            font=("Consolas", 25, "bold"),
            text_color="#ffd166",
        ).pack(pady=(20, 4))
        ctk.CTkLabel(
            warning,
            text="HARMLESS SECURITY DRILL",
            font=("Consolas", 17, "bold"),
            text_color="#ff758f",
        ).pack(pady=(0, 12))
        ctk.CTkLabel(
            warning,
            text=(
                "This test deliberately creates a clearly labeled TEST denial "
                "event in the append-only Fox Sentry audit log.\n\n"
                "It grants no access, runs no repair, changes no operational "
                "project file, and disables nothing. The security log and its "
                "lock file may be created or appended."
            ),
            justify="left",
            wraplength=760,
            font=("Consolas", 13),
            text_color="#f4f1ff",
        ).pack(padx=24, pady=(0, 18))

        controls = ctk.CTkFrame(outer)
        controls.pack(fill="x", padx=10, pady=(0, 15))
        ctk.CTkButton(
            controls,
            text="TRIP SENTRY — RUN HARMLESS TEST",
            command=self.run_trip_sentry_test,
            width=330,
            fg_color="#a51f3d",
            hover_color="#cc2c52",
        ).pack(pady=16)

        self.trip_sentry_status = ctk.StringVar(
            value="READY // No TEST incident has been generated in this session."
        )
        ctk.CTkLabel(
            controls,
            textvariable=self.trip_sentry_status,
            font=("Consolas", 13, "bold"),
            text_color="#ffd166",
            wraplength=760,
        ).pack(padx=20, pady=(0, 14))

        result_panel = ctk.CTkFrame(outer)
        result_panel.pack(fill="both", expand=True, padx=10, pady=(0, 15))
        ctk.CTkLabel(
            result_panel,
            text="TEST INCIDENT RECEIPT",
            font=("Consolas", 15, "bold"),
            text_color=color("cyan"),
        ).pack(anchor="w", padx=14, pady=(12, 6))
        self.trip_sentry_result_box = ctk.CTkTextbox(
            result_panel,
            wrap="word",
            height=260,
            font=("Consolas", 12),
        )
        self.trip_sentry_result_box.pack(
            fill="both", expand=True, padx=14, pady=(0, 14)
        )
        self.trip_sentry_result_box.insert(
            "end",
            "Awaiting an operator-initiated harmless TEST event.\n",
        )
        self.trip_sentry_result_box.configure(state="disabled")

        registry_panel = ctk.CTkFrame(outer)
        registry_panel.pack(fill="both", expand=True, padx=10, pady=(0, 15))
        registry_header = ctk.CTkFrame(registry_panel, fg_color="transparent")
        registry_header.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            registry_header,
            text="APPLICATION REGISTRY & HEALTH",
            font=("Consolas", 15, "bold"),
            text_color=color("cyan"),
        ).pack(side="left")
        ctk.CTkButton(
            registry_header,
            text="REFRESH HEALTH",
            command=self.refresh_application_registry_health,
            width=160,
        ).pack(side="right")

        self.application_registry_status = ctk.StringVar(
            value=(
                "CHECKING REGISTRY // Telemetry only; "
                "no security incident will be generated."
            )
        )
        ctk.CTkLabel(
            registry_panel,
            textvariable=self.application_registry_status,
            font=("Consolas", 12, "bold"),
            text_color="#ffd166",
            wraplength=760,
        ).pack(anchor="w", padx=14, pady=(0, 8))

        self.application_registry_box = ctk.CTkTextbox(
            registry_panel,
            wrap="word",
            height=320,
            font=("Consolas", 11),
        )
        self.application_registry_box.pack(
            fill="both",
            expand=True,
            padx=14,
            pady=(0, 14),
        )
        self.application_registry_box.insert(
            "end",
            "Loading passive application health telemetry...\n",
        )
        self.application_registry_box.configure(state="disabled")

        incident_panel = ctk.CTkFrame(outer)
        incident_panel.pack(fill="both", expand=True, padx=10, pady=(0, 15))
        incident_header = ctk.CTkFrame(incident_panel, fg_color="transparent")
        incident_header.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            incident_header,
            text="FOX SENTRY INCIDENT VIEWER",
            font=("Consolas", 15, "bold"),
            text_color="#ff758f",
        ).pack(side="left")

        self.fox_sentry_incident_filter = ctk.StringVar(value="ALL")
        ctk.CTkOptionMenu(
            incident_header,
            values=["ALL", "TEST", "OPERATIONAL", "INFO", "NOTICE", "WARNING", "CRITICAL"],
            variable=self.fox_sentry_incident_filter,
            command=lambda _value: self.refresh_fox_sentry_incidents(),
            width=150,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            incident_header,
            text="REFRESH INCIDENTS",
            command=self.refresh_fox_sentry_incidents,
            width=170,
        ).pack(side="right")

        self.fox_sentry_chain_status = ctk.StringVar(
            value="CHECKING CHAIN // Read-only verification pending."
        )
        ctk.CTkLabel(
            incident_panel,
            textvariable=self.fox_sentry_chain_status,
            font=("Consolas", 12, "bold"),
            text_color="#ffd166",
            wraplength=760,
        ).pack(anchor="w", padx=14, pady=(0, 8))

        self.fox_sentry_incident_box = ctk.CTkTextbox(
            incident_panel,
            wrap="word",
            height=360,
            font=("Consolas", 11),
        )
        self.fox_sentry_incident_box.pack(
            fill="both",
            expand=True,
            padx=14,
            pady=(0, 14),
        )
        self.fox_sentry_incident_box.insert(
            "end",
            "Loading the read-only Fox Sentry incident chain...\n",
        )
        self.fox_sentry_incident_box.configure(state="disabled")
        self.after(25, self.refresh_application_registry_health)
        self.after(50, self.refresh_fox_sentry_incidents)
        self.make_status_bar()

    def _show_trip_sentry_omega_alert(self, receipt):
        event = (receipt.get("details") or {}).get("event") or {}
        dialog = ctk.CTkToplevel(self)
        dialog.title("OMEGA PROTOCOL // TEST INCIDENT")
        dialog.geometry("760x500")
        dialog.minsize(660, 430)
        dialog.transient(self)
        dialog.grab_set()

        frame = ctk.CTkFrame(
            dialog,
            border_width=3,
            border_color="#ff4d6d",
            fg_color="#16070c",
        )
        frame.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(
            frame,
            text="Ω",
            font=("Consolas", 70, "bold"),
            text_color="#ff4d6d",
        ).pack(pady=(18, 0))
        ctk.CTkLabel(
            frame,
            text="OMEGA PROTOCOL",
            font=("Consolas", 29, "bold"),
            text_color="#ffd166",
        ).pack()
        ctk.CTkLabel(
            frame,
            text="TEST INCIDENT — FOX SENTRY PATH VERIFIED",
            font=("Consolas", 16, "bold"),
            text_color="#ff758f",
        ).pack(pady=(4, 16))
        ctk.CTkLabel(
            frame,
            text=(
                "DENIAL EVENT RECORDED\n"
                "NO ACCESS GRANTED\n"
                "NO REPAIR EXECUTED\n"
                "NO OPERATIONAL FILE CHANGED"
            ),
            justify="center",
            font=("Consolas", 14, "bold"),
            text_color="#f4f1ff",
        ).pack(pady=8)
        ctk.CTkLabel(
            frame,
            text=(
                f"Event: {event.get('event_id', 'unknown')}\n"
                f"Correlation: {event.get('correlation_id', 'unknown')}\n"
                f"Receipt: {receipt.get('receipt_id', 'unknown')}"
            ),
            justify="left",
            font=("Consolas", 11),
            text_color="#aeb2c8",
        ).pack(padx=20, pady=(12, 14))
        ctk.CTkButton(
            frame,
            text="ACKNOWLEDGE TEST INCIDENT",
            command=dialog.destroy,
            width=280,
        ).pack(pady=(0, 20))

    def run_trip_sentry_test(self):
        confirmed = messagebox.askyesno(
            "Trip Sentry — Harmless TEST",
            (
                "Generate one clearly labeled TEST denial event?\n\n"
                "No access will be granted and no repair will run. "
                "The append-only security audit log and lock file may be "
                "created or updated."
            ),
            parent=self,
        )
        if not confirmed:
            if hasattr(self, "trip_sentry_status"):
                self.trip_sentry_status.set(
                    "CANCELLED // No TEST incident was generated."
                )
            return

        correlation_id = new_airlock_correlation_id()
        mission_id = f"desktop_trip_sentry_{time.strftime('%Y%m%dT%H%M%S')}"
        receipt = record_trip_sentry_test_event(
            correlation_id=correlation_id,
            mission_id=mission_id,
        )
        verified = bool(receipt.get("verified"))
        event = (receipt.get("details") or {}).get("event") or {}
        lines = [
            f"State: {receipt.get('state', 'unknown')}",
            f"Verified: {verified}",
            f"Receipt ID: {receipt.get('receipt_id', '')}",
            f"Event ID: {event.get('event_id', '')}",
            f"Correlation ID: {event.get('correlation_id', correlation_id)}",
            f"Mission ID: {event.get('mission_id', mission_id)}",
            f"Decision: {event.get('decision', '')}",
            f"Action: {event.get('action', '')}",
            f"TEST Event: {event.get('test_event', False)}",
            f"Log: {(receipt.get('details') or {}).get('log_path', '')}",
        ]

        if hasattr(self, "trip_sentry_result_box"):
            self.trip_sentry_result_box.configure(state="normal")
            self.trip_sentry_result_box.delete("1.0", "end")
            self.trip_sentry_result_box.insert("end", "\n".join(lines))
            self.trip_sentry_result_box.configure(state="disabled")

        if verified:
            self.trip_sentry_status.set(
                "VERIFIED TEST INCIDENT // Fox Sentry logging and warning "
                "path completed without granting access."
            )
            self._show_trip_sentry_omega_alert(receipt)
            self.refresh_fox_sentry_incidents()
        else:
            self.trip_sentry_status.set(
                "TEST FAILED CLOSED // No verified security receipt was produced."
            )
            messagebox.showerror(
                "Trip Sentry Test Failed Closed",
                (
                    "Fox Sentry did not produce a verified audit receipt. "
                    "The test is not being reported as successful."
                ),
                parent=self,
            )

    def _destroy_mission_context_menus(self):
        for menu in getattr(self, "_mission_context_menus", []):
            try:
                menu.destroy()
            except Exception:
                pass
        self._mission_context_menus = []

    @staticmethod
    def _mission_text_widget(textbox):
        return getattr(textbox, "_textbox", textbox)

    @staticmethod
    def _select_all_mission_text(text_widget):
        try:
            text_widget.tag_add("sel", "1.0", "end-1c")
            text_widget.mark_set("insert", "1.0")
            text_widget.see("insert")
        except tk.TclError:
            pass
        return "break"

    def _bind_mission_context_menu(self, textbox, editable):
        text_widget = self._mission_text_widget(textbox)
        menu = tk.Menu(self, tearoff=False)

        if editable:
            menu.add_command(
                label="Cut",
                command=lambda: text_widget.event_generate("<<Cut>>"),
            )

        menu.add_command(
            label="Copy",
            command=lambda: text_widget.event_generate("<<Copy>>"),
        )

        if editable:
            menu.add_command(
                label="Paste",
                command=lambda: text_widget.event_generate("<<Paste>>"),
            )

        menu.add_separator()
        menu.add_command(
            label="Select All",
            command=lambda: self._select_all_mission_text(text_widget),
        )

        def show_menu(event):
            try:
                if editable and not text_widget.tag_ranges("sel"):
                    text_widget.mark_set("insert", f"@{event.x},{event.y}")
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
            return "break"

        text_widget.bind("<Button-3>", show_menu, add="+")
        self._mission_context_menus.append(menu)

    def show_mission_console(self):
        self.clear_content()
        self._destroy_mission_context_menus()
        self.make_title("MISSION CONSOLE")
        self.chat_box = ctk.CTkTextbox(self.content, wrap="word", state="disabled", font=("Consolas", 13))
        self.chat_box.pack(padx=15, pady=10, fill="both", expand=True)
        self._bind_mission_context_menu(self.chat_box, editable=False)
        bottom = ctk.CTkFrame(self.content)
        bottom.pack(padx=15, pady=(0, 10), fill="x")
        self.input_box = ctk.CTkTextbox(bottom, height=90, wrap="word", font=("Consolas", 13))
        self.input_box.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self._bind_mission_context_menu(self.input_box, editable=True)
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
        initial_canvas_text = (
            self.red_canvas_progress_text
            if self.red_canvas_active and self.red_canvas_progress_text
            else f"COMFYUI STATUS: {comfy_status}\n\nReady for Operation Red Bridge."
        )
        self.canvas_status = ctk.CTkLabel(
            preview,
            text=initial_canvas_text,
            font=("Consolas", 14),
        )
        self.canvas_status.pack(pady=(20, 10))

        self.canvas_progress = ctk.CTkProgressBar(preview, width=460)
        self.canvas_progress.pack(pady=10)
        self.canvas_progress.set(
            self.red_canvas_progress_percent / 100.0
            if self.red_canvas_active
            else 0
        )

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
        self.canvas_status.configure(
            text=(
                "MISSION ACCEPTED\n\n"
                "Sending prompt to ComfyUI...\n"
                "Waiting for real generation progress."
            )
        )
        self.canvas_progress.set(0)
        self._start_red_canvas_progress_tracking()
        threading.Thread(
            target=self._generate_red_canvas_thread,
            args=(prompt, negative, checkpoint, width, height, seed),
            daemon=True
        ).start()

    def _cancel_red_canvas_progress_tracking(self):
        if self.red_canvas_progress_job is not None:
            try:
                self.after_cancel(self.red_canvas_progress_job)
            except Exception:
                pass
            self.red_canvas_progress_job = None

    def _start_red_canvas_progress_tracking(self):
        """Track only console output appended after this generation starts."""
        self._cancel_red_canvas_progress_tracking()
        self.red_canvas_active = True
        self.red_canvas_progress_percent = 0
        self.red_canvas_progress_text = (
            "MISSION ACCEPTED\n\n"
            "Sending prompt to ComfyUI...\n"
            "Waiting for real generation progress."
        )
        self.red_canvas_log_path = None
        self.red_canvas_log_offset = 0
        self.red_canvas_log_buffer = ""

        try:
            snapshot = comfy_operations_snapshot(
                Path(__file__).resolve().parents[1],
                line_limit=20,
            )
            log_value = snapshot.get("log_path")
            if log_value:
                log_path = Path(str(log_value))
                if log_path.is_file():
                    self.red_canvas_log_path = log_path
                    self.red_canvas_log_offset = log_path.stat().st_size
        except Exception:
            pass

        self.red_canvas_progress_job = self.after(
            250,
            self._poll_red_canvas_progress,
        )

    def _update_red_canvas_progress_widgets(self):
        try:
            if (
                hasattr(self, "canvas_progress")
                and self.canvas_progress.winfo_exists()
            ):
                self.canvas_progress.set(
                    max(
                        0.0,
                        min(
                            1.0,
                            self.red_canvas_progress_percent / 100.0,
                        ),
                    )
                )
            if (
                hasattr(self, "canvas_status")
                and self.canvas_status.winfo_exists()
                and self.red_canvas_progress_text
            ):
                self.canvas_status.configure(
                    text=self.red_canvas_progress_text
                )
        except Exception:
            pass

    def _poll_red_canvas_progress(self):
        if self._closing or not self.red_canvas_active:
            self.red_canvas_progress_job = None
            return

        try:
            snapshot = comfy_operations_snapshot(
                Path(__file__).resolve().parents[1],
                line_limit=20,
            )
            log_value = snapshot.get("log_path")
            log_path = Path(str(log_value)) if log_value else None

            if log_path is not None and log_path.is_file():
                if (
                    self.red_canvas_log_path is None
                    or log_path != self.red_canvas_log_path
                ):
                    self.red_canvas_log_path = log_path
                    self.red_canvas_log_offset = 0
                    self.red_canvas_log_buffer = ""

                size = log_path.stat().st_size
                if size < self.red_canvas_log_offset:
                    self.red_canvas_log_offset = 0
                    self.red_canvas_log_buffer = ""

                if size > self.red_canvas_log_offset:
                    with log_path.open("rb") as handle:
                        handle.seek(self.red_canvas_log_offset)
                        raw = handle.read(
                            min(
                                256 * 1024,
                                size - self.red_canvas_log_offset,
                            )
                        )
                    self.red_canvas_log_offset += len(raw)
                    chunk = raw.decode(
                        "utf-8",
                        errors="replace",
                    ).replace("\r", "\n")
                    self.red_canvas_log_buffer = (
                        self.red_canvas_log_buffer + chunk
                    )[-4096:]

                    # ComfyUI/tqdm lines look like:
                    # 75%|######5 | 15/20 [02:43<00:55, 11.12s/it]
                    matches = re.findall(
                        r"(?<!\d)(100|[1-9]?\d)%\|"
                        r"[^\r\n]*(?:\d+/\d+)",
                        self.red_canvas_log_buffer,
                    )
                    if matches:
                        actual = max(0, min(100, int(matches[-1])))
                        self.red_canvas_progress_percent = actual
                        self.red_canvas_progress_text = (
                            "MISSION IN PROGRESS\n\n"
                            f"ComfyUI generation: {actual}%\n"
                            "Progress is coming from the live console."
                        )
                    else:
                        lower = self.red_canvas_log_buffer.casefold()
                        if "got prompt" in lower:
                            self.red_canvas_progress_text = (
                                "PROMPT RECEIVED\n\n"
                                "ComfyUI accepted the request.\n"
                                "Preparing the image model..."
                            )
                        if (
                            "requested to load" in lower
                            or "model_type" in lower
                            or "loaded completely" in lower
                        ):
                            self.red_canvas_progress_text = (
                                "LOADING IMAGE MODEL\n\n"
                                "ComfyUI is preparing SDXL on the CPU.\n"
                                "The percentage will appear when sampling starts."
                            )

            self._update_red_canvas_progress_widgets()
        except Exception:
            # Progress display must never interfere with generation.
            pass

        self.red_canvas_progress_job = self.after(
            350,
            self._poll_red_canvas_progress,
        )

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
        self._cancel_red_canvas_progress_tracking()
        self.red_canvas_active = False
        self.red_canvas_progress_percent = 100
        self.red_canvas_progress_text = (
            f"MISSION COMPLETE\n\nImage saved:\n{image_path}"
        )
        self.stop_mission_animation("ONLINE")
        self.complete_workshop_mission("ONLINE")
        self.mission_status(f"Red Canvas mission complete.\n\nImage saved:\n{image_path}")
        self.show_red_canvas()
        if hasattr(self, "canvas_progress") and self.canvas_progress.winfo_exists():
            self.canvas_progress.set(1)
        if hasattr(self, "canvas_status") and self.canvas_status.winfo_exists():
            self.canvas_status.configure(text=f"MISSION COMPLETE\n\nImage saved:\n{image_path}")

    def _red_canvas_error(self, error_text):
        self._cancel_red_canvas_progress_tracking()
        self.red_canvas_active = False
        self.red_canvas_progress_text = (
            f"RED BRIDGE ERROR:\n{error_text}"
        )
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

        desktop_mission_id = f"desktop_mission_{uuid4().hex}"
        mission = direct(text, mission_id=desktop_mission_id)
        agent = mission["agent"]
        payload = mission["payload"]
        correlation_id = mission.get("correlation_id")
        mission_id = mission.get("mission_id")
        route_audit_receipt = mission.get("audit_receipt")

        self.mission_status(self.format_director_analysis(mission))

        if agent in self.specialists:
            if agent == "red_canvas":
                self.begin_workshop_mission("Creative", "Red Canvas")
                self.mission_status("Red Canvas mission detected.\n\nDeploying PromptSmith and image bridge.")
                return self.specialists[agent].handle(text, payload)

            if agent == "engineer":
                self.begin_workshop_mission("Engineering", "Engineer")
                self.mission_status("Engineer mission detected.\n\nReading project files in read-only mode.")
                return self.specialists[agent].handle(
                    payload,
                    caller="operator",
                    correlation_id=correlation_id,
                    mission_id=mission_id,
                    route_audit_receipt=route_audit_receipt,
                )

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
        if self.comfy_ops_refresh_job is not None:
            try:
                self.after_cancel(self.comfy_ops_refresh_job)
            except Exception:
                pass
            self.comfy_ops_refresh_job = None
        self._cancel_red_canvas_progress_tracking()
        self.stop_chat_heartbeat()
        self.stop_mission_animation("OFFLINE")
        self.server.release()
        self.mission_memory.save()
        self.destroy()
