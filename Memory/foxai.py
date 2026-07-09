from ui.splash import show_splash
from ui.main_window import FoxAIApp

if __name__ == "__main__":
    show_splash()
    app = FoxAIApp()
    app.mainloop()
