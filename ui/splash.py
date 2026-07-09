import time
from pathlib import Path
import customtkinter as ctk
from PIL import Image

try:
    from .foxai_theme import configure_ctk_identity, apply_foxai_theme, color
except Exception:
    from ui.foxai_theme import configure_ctk_identity, apply_foxai_theme, color

ctk.set_appearance_mode("dark")
configure_ctk_identity()

def show_splash():
    splash = ctk.CTk()
    splash.title("FOXAI Boot")
    splash.geometry("620x620")
    splash.resizable(False, False)

    base = Path(__file__).resolve().parent.parent
    logo_path = base / "assets" / "foxai_logo.png"
    icon_path = base / "assets" / "foxai.ico"
    if icon_path.exists():
        splash.iconbitmap(str(icon_path))

    frame = ctk.CTkFrame(splash)
    frame.pack(fill="both", expand=True, padx=18, pady=18)
    apply_foxai_theme(splash)

    if logo_path.exists():
        logo = ctk.CTkImage(light_image=Image.open(logo_path), dark_image=Image.open(logo_path), size=(175, 175))
        logo_label = ctk.CTkLabel(frame, image=logo, text="")
        logo_label.image = logo
        logo_label.pack(pady=(15, 5))

    ctk.CTkLabel(frame, text="FOXAI COMMAND OS", font=("Consolas", 32, "bold"), text_color=color("purple_soft")).pack(pady=(5, 0))
    ctk.CTkLabel(frame, text="Ultimate Edifier Platform // Local Runtime", font=("Consolas", 14), text_color=color("muted")).pack(pady=(0, 15))

    terminal = ctk.CTkTextbox(frame, width=520, height=240, font=("Consolas", 13))
    terminal.pack(padx=15, pady=10)
    terminal.configure(state="disabled")
    progress = ctk.CTkProgressBar(frame, width=520)
    progress.pack(pady=(8, 10))
    progress.set(0)

    steps = [
        "FOXAI BIOS v0.4.0-alpha",
        "Memory.................OK",
        "Operator Profile.......OK",
        "Agent Fox..............LOADED",
        "Mission Archive........ONLINE",
        "Neural Engines.........SCANNED",
        "Red Canvas.............STANDBY",
        "Iron Library...........ONLINE",
        "Security Mode..........LOCAL ONLY",
        "Network................OFFLINE",
        "Command Bridge.........READY",
        "Launching FOXAI Bridge..."
    ]
    for i, step in enumerate(steps, start=1):
        terminal.configure(state="normal")
        terminal.insert("end", f"> {step}\n")
        terminal.see("end")
        terminal.configure(state="disabled")
        progress.set(i / len(steps))
        splash.update()
        time.sleep(0.22)
    time.sleep(0.35)
    splash.destroy()
