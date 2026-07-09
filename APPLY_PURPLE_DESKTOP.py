from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil
import json

ROOT = Path(__file__).resolve().parent
UI = ROOT / "ui"
BACKUP_ROOT = ROOT / "Backups" / f"purple_desktop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path) -> None:
    if path.exists():
        dest = BACKUP_ROOT / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

def write_theme() -> None:
    src = ROOT / "_purple_payload" / "ui" / "foxai_theme.py"
    dst = UI / "foxai_theme.py"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def patch_main_window() -> dict:
    path = UI / "main_window.py"
    if not path.exists():
        raise SystemExit("ERROR: ui\\main_window.py not found. Extract into Z:\\FOXAI.")
    backup(path)
    text = path.read_text(encoding="utf-8")
    changed = []

    if "import json" not in text:
        text = text.replace("import configparser\n", "import configparser\nimport json\n")
        changed.append("added json import")
    if "from pathlib import Path" not in text:
        text = text.replace("import json\n", "import json\nfrom pathlib import Path\n")
        changed.append("added Path import")

    if "from ui.foxai_theme import" not in text and "from .foxai_theme import" not in text:
        marker = "from core.chat_resilience import ChatResilience, ChatTimeoutError\n"
        insert = marker + "\ntry:\n    from .foxai_theme import configure_ctk_identity, apply_foxai_theme, color\nexcept Exception:\n    from ui.foxai_theme import configure_ctk_identity, apply_foxai_theme, color\n"
        text = text.replace(marker, insert)
        changed.append("added FOXAI theme import")

    text = text.replace('ctk.set_default_color_theme("green")', 'configure_ctk_identity()')
    text = text.replace('self.title("FOXAI // Cyber Operations Console")', 'self.title("FOXAI Command OS // Ultimate Edifier Platform")')

    if "apply_foxai_theme(self)\n        self.after(750, self._foxai_theme_watchdog)" not in text:
        text = text.replace(
            "        self.build_ui()\n        self.show_mission_console()\n",
            "        self.build_ui()\n        apply_foxai_theme(self)\n        self.after(750, self._foxai_theme_watchdog)\n        self.show_command_bridge()\n"
        )
        changed.append("startup now opens Command Bridge")

    if "def _foxai_theme_watchdog(self):" not in text:
        method = '''
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
            ctk.CTkLabel(dept_panel, text="Run BUILD_FOXAI.bat to generate OpsBridge\\\\outbox\\\\bridge_feed.json.", font=("Consolas", 13)).pack(anchor="w", padx=14, pady=(0, 14))
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
        ctk.CTkLabel(mission_panel, text=f"Latest Mission: {latest_mission}\\nLatest Event: {latest_event}", justify="left", font=("Consolas", 13)).pack(anchor="w", padx=14, pady=(0, 12))

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
                log_box.insert("end", f"{entry.get('timestamp')} — {entry.get('source')}\\n[{entry.get('severity')}] {entry.get('message')}\\n\\n")
        else:
            log_box.insert("end", "Captain's Log waiting for bridge feed.\\n")
        log_box.configure(state="disabled")

        self.make_status_bar()
        try:
            apply_foxai_theme(self)
        except Exception:
            pass

'''
        text = text.replace("    def load_config(self):\n", method + "\n    def load_config(self):\n")
        changed.append("added Command Bridge view")

    if "self.command_bridge_button" not in text:
        needle = '        ctk.CTkLabel(self.sidebar, text="DEPARTMENTS", font=("Consolas", 12, "bold")).pack(pady=(18, 8))\n\n'
        replacement = needle + '        self.command_bridge_button = ctk.CTkButton(self.sidebar, text="🚀 COMMAND BRIDGE", command=self.show_command_bridge, width=230)\n        self.command_bridge_button.pack(pady=4)\n\n'
        text = text.replace(needle, replacement)
        changed.append("added Command Bridge sidebar button")

    text = text.replace('ctk.CTkLabel(self.sidebar, text="FOXAI // OPS", font=("Consolas", 28, "bold")).pack(pady=(5, 5))',
                        'ctk.CTkLabel(self.sidebar, text="FOXAI COMMAND OS", font=("Consolas", 24, "bold"), text_color=color("purple_soft")).pack(pady=(5, 5))')
    text = text.replace('ctk.CTkLabel(self.sidebar, text="Cyber Operations Console", font=("Consolas", 13)).pack(pady=(0, 18))',
                        'ctk.CTkLabel(self.sidebar, text="Ultimate Edifier Platform", font=("Consolas", 13), text_color=color("muted")).pack(pady=(0, 18))')

    path.write_text(text, encoding="utf-8")
    return {"file": str(path), "changed": changed}

def patch_splash() -> dict:
    path = UI / "splash.py"
    if not path.exists():
        raise SystemExit("ERROR: ui\\splash.py not found. Extract into Z:\\FOXAI.")
    backup(path)
    text = path.read_text(encoding="utf-8")
    changed = []

    if "from ui.foxai_theme import" not in text and "from .foxai_theme import" not in text:
        marker = "from PIL import Image\n"
        text = text.replace(marker, marker + "\ntry:\n    from .foxai_theme import configure_ctk_identity, apply_foxai_theme, color\nexcept Exception:\n    from ui.foxai_theme import configure_ctk_identity, apply_foxai_theme, color\n")
        changed.append("added FOXAI theme import")

    text = text.replace('ctk.set_default_color_theme("green")', 'configure_ctk_identity()')
    text = text.replace('ctk.CTkLabel(frame, text="FOXAI BIOS", font=("Consolas", 34, "bold")).pack(pady=(5, 0))',
                        'ctk.CTkLabel(frame, text="FOXAI COMMAND OS", font=("Consolas", 32, "bold"), text_color=color("purple_soft")).pack(pady=(5, 0))')
    text = text.replace('ctk.CTkLabel(frame, text="Cyber Operations Console // Local Runtime", font=("Consolas", 14)).pack(pady=(0, 15))',
                        'ctk.CTkLabel(frame, text="Ultimate Edifier Platform // Local Runtime", font=("Consolas", 14), text_color=color("muted")).pack(pady=(0, 15))')
    text = text.replace('"Cyber Console..........READY"', '"Command Bridge.........READY"')
    text = text.replace('"Launching Agent Fox..."', '"Launching FOXAI Bridge..."')

    if "apply_foxai_theme(splash)" not in text:
        text = text.replace('    frame.pack(fill="both", expand=True, padx=18, pady=18)\n',
                            '    frame.pack(fill="both", expand=True, padx=18, pady=18)\n    apply_foxai_theme(splash)\n')
        changed.append("applied splash theme")

    path.write_text(text, encoding="utf-8")
    return {"file": str(path), "changed": changed}

def main() -> None:
    if not UI.exists():
        raise SystemExit("ERROR: ui folder not found. Extract this package into Z:\\FOXAI and run again.")
    if not (ROOT / "_purple_payload").exists():
        raise SystemExit("ERROR: _purple_payload missing. Re-extract package and try again.")

    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    write_theme()
    result = {
        "ok": True,
        "patch": "FOXAI Orion v9.1 Purple Desktop Shell",
        "backup_root": str(BACKUP_ROOT),
        "main_window": patch_main_window(),
        "splash": patch_splash(),
    }

    outbox = ROOT / "OpsBridge" / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    (outbox / "purple_desktop_patch_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (outbox / "purple_desktop_patch_report.txt").write_text(
        "FOXAI Orion v9.1 Purple Desktop Shell\n"
        "=====================================\n\n"
        f"OK: {result['ok']}\n"
        f"Backup Root: {result['backup_root']}\n\n"
        "Green identity retired. Graphite + purple desktop shell applied.\n",
        encoding="utf-8"
    )

    print("FOXAI Orion v9.1 Purple Desktop Shell")
    print("=====================================")
    print()
    print("OK: True")
    print(f"Backup Root: {BACKUP_ROOT}")
    print()
    print("Patched:")
    print("- ui\\main_window.py")
    print("- ui\\splash.py")
    print("- ui\\foxai_theme.py")
    print()
    print("Next:")
    print("Run your normal FOXAI start command.")

if __name__ == "__main__":
    main()
