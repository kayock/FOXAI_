import os
import subprocess
import webbrowser
import configparser
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
ENGINE = BASE / "Engine" / "llama-server.exe"
MODELS = BASE / "Models"
PROMPTS = BASE / "Prompts"
LOGS = BASE / "Logs"
CONFIG_DIR = BASE / "Config"
CONFIG_FILE = CONFIG_DIR / "FoxAI.ini"

def clear():
    os.system("cls")

def load_config():
    CONFIG_DIR.mkdir(exist_ok=True)
    config = configparser.ConfigParser()

    if not CONFIG_FILE.exists():
        config["Server"] = {
            "host": "127.0.0.1",
            "port": "8080",
            "threads": "12",
            "context": "8192"
        }
        with open(CONFIG_FILE, "w") as f:
            config.write(f)

    config.read(CONFIG_FILE)
    return config

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        config.write(f)

def log(message):
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / "launch_history.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {message}\n")

def find_models():
    return sorted(MODELS.rglob("*.gguf"))

def find_profiles():
    return sorted(PROMPTS.glob("*.txt"))

def header():
    print("=" * 52)
    print("                 FOX AI v1.4")
    print("          Portable AI Workstation")
    print("=" * 52)

def choose(items, title):
    if not items:
        print(f"No {title.lower()} found.")
        input("Press Enter...")
        return None

    while True:
        clear()
        header()
        print()
        print(title)
        print("-" * len(title))

        for i, item in enumerate(items, start=1):
            print(f"{i}) {item.name}")

        print()
        print("Q) Back")
        choice = input("Choose: ").strip().lower()

        if choice == "q":
            return None

        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(items):
                return items[n - 1]

def start_server(model, profile=None):
    config = load_config()
    host = config["Server"]["host"]
    port = config["Server"]["port"]
    threads = config["Server"]["threads"]
    context = config["Server"]["context"]

    clear()
    header()
    print()
    print(f"Model:   {model.name}")
    print(f"Profile: {profile.stem if profile else 'Default'}")
    print(f"Threads: {threads}")
    print(f"Context: {context}")
    print()
    print(f"Opening browser at http://{host}:{port}")
    print()

    cmd = [
        str(ENGINE),
        "--model", str(model),
        "--host", host,
        "--port", port,
        "--ctx-size", context,
        "--threads", threads,
    ]

    if profile:
        cmd.extend(["--system-prompt-file", str(profile)])

    log(f"Started model={model.name}, profile={profile.name if profile else 'Default'}")
    webbrowser.open(f"http://{host}:{port}")
    subprocess.run(cmd)
    log(f"Stopped model={model.name}")

def show_settings():
    config = load_config()

    while True:
        clear()
        header()
        print()
        print("Settings")
        print("-" * 8)
        print(f"1) Host:     {config['Server']['host']}")
        print(f"2) Port:     {config['Server']['port']}")
        print(f"3) Threads:  {config['Server']['threads']}")
        print(f"4) Context:  {config['Server']['context']}")
        print()
        print("Q) Back")
        print()

        choice = input("Choose setting to edit: ").strip().lower()

        if choice == "q":
            save_config(config)
            return

        if choice == "1":
            config["Server"]["host"] = input("New host: ").strip()
        elif choice == "2":
            config["Server"]["port"] = input("New port: ").strip()
        elif choice == "3":
            config["Server"]["threads"] = input("New threads: ").strip()
        elif choice == "4":
            config["Server"]["context"] = input("New context size: ").strip()

        save_config(config)

def show_logs():
    clear()
    header()
    print()
    log_file = LOGS / "launch_history.txt"

    if not log_file.exists():
        print("No launch history yet.")
    else:
        print(log_file.read_text(encoding="utf-8")[-3000:])

    input("\nPress Enter...")

def main():
    if not ENGINE.exists():
        print("ERROR: Engine\\llama-server.exe not found.")
        input("Press Enter...")
        return

    while True:
        models = find_models()
        profiles = find_profiles()

        clear()
        header()
        print()
        print(f"Models found:   {len(models)}")
        print(f"Profiles found: {len(profiles)}")
        print()
        print("1) Start Chat")
        print("2) Start With Profile")
        print("3) List Models")
        print("4) List Profiles")
        print("5) Settings")
        print("6) Launch History")
        print("7) Quit")
        print()

        choice = input("Choose: ").strip()

        if choice == "1":
            model = choose(models, "Choose Model")
            if model:
                start_server(model)

        elif choice == "2":
            model = choose(models, "Choose Model")
            if model:
                profile = choose(profiles, "Choose Profile")
                if profile:
                    start_server(model, profile)

        elif choice == "3":
            clear()
            header()
            print()
            for m in models:
                print(m)
            input("\nPress Enter...")

        elif choice == "4":
            clear()
            header()
            print()
            for p in profiles:
                print(p)
            input("\nPress Enter...")

        elif choice == "5":
            show_settings()

        elif choice == "6":
            show_logs()

        elif choice == "7":
            break

if __name__ == "__main__":
    main()