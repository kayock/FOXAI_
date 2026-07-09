from __future__ import annotations

import customtkinter as ctk

FOXAI_COLORS = {
    "bg": "#070811", "panel": "#121420", "panel2": "#181b2a", "panel3": "#202436",
    "text": "#f4f1ff", "muted": "#aeb2c8", "purple": "#8f5cff",
    "purple_hover": "#7c4de6", "purple_soft": "#b18cff", "cyan": "#23d7ff",
    "green": "#42ff9e", "orange": "#ff9f43", "blue": "#3ba7ff",
    "magenta": "#ff5ccf", "gold": "#ffd166", "red": "#ff4d6d"
}

def configure_ctk_identity() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

def color(name: str) -> str:
    return FOXAI_COLORS.get(name, FOXAI_COLORS["purple"])

def _safe(widget, **kwargs) -> None:
    try:
        widget.configure(**kwargs)
    except Exception:
        pass

def apply_foxai_theme(root) -> None:
    c = FOXAI_COLORS

    def visit(widget):
        cls = widget.__class__.__name__
        if cls in {"CTk", "CTkToplevel"}:
            _safe(widget, fg_color=c["bg"])
        elif cls in {"CTkFrame", "CTkScrollableFrame"}:
            _safe(widget, fg_color=c["panel"], border_color="#2a2d42")
        elif cls == "CTkButton":
            text = ""
            try:
                text = str(widget.cget("text")).lower()
            except Exception:
                pass
            fg, hover = c["purple"], c["purple_hover"]
            if any(w in text for w in ["engineer", "repair", "diagnostic", "inspection"]):
                fg, hover = c["orange"], "#dd862f"
            elif any(w in text for w in ["library", "science", "iron"]):
                fg, hover = c["blue"], "#2d86d4"
            elif any(w in text for w in ["canvas", "creative", "prompt"]):
                fg, hover = c["magenta"], "#df45b2"
            elif any(w in text for w in ["end", "error", "stop"]):
                fg, hover = c["red"], "#d93c59"
            _safe(widget, fg_color=fg, hover_color=hover, text_color=c["text"], border_width=1, border_color="#332a55", corner_radius=12)
        elif cls == "CTkLabel":
            _safe(widget, text_color=c["text"])
        elif cls in {"CTkTextbox", "CTkEntry"}:
            _safe(widget, fg_color="#0b0d17", text_color=c["text"], border_color="#332a55", border_width=1)
        elif cls == "CTkOptionMenu":
            _safe(widget, fg_color=c["panel3"], button_color=c["purple"], button_hover_color=c["purple_hover"],
                  text_color=c["text"], dropdown_fg_color=c["panel2"], dropdown_text_color=c["text"], dropdown_hover_color="#2a2142")
        elif cls == "CTkProgressBar":
            _safe(widget, fg_color="#24263a", progress_color=c["purple"])
        try:
            for child in widget.winfo_children():
                visit(child)
        except Exception:
            pass

    visit(root)
