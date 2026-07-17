import os, sys, subprocess, datetime, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "System" / "Logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
VERSION = "0.1.2"
CODENAME = "Dashboard Live View"
API_URL = "http://127.0.0.1:8844"

api_process = None

def log(message):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line)
    with open(LOG_DIR / "boot.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")

def read_text(path, default=""):
    try: return Path(path).read_text(encoding="utf-8")
    except Exception: return default

def extract_operator_name():
    text = read_text(ROOT / "System/Config/operator.yaml")
    for line in text.splitlines():
        if "display_name:" in line:
            return line.split(":",1)[1].strip() or "Operator"
    return "Operator"

def ensure_operator_profile():
    profile = ROOT / "System/Config/operator.yaml"
    text = read_text(profile)
    if "first_boot: true" not in text:
        return extract_operator_name()
    print("\nDocumentation will refer to the human as: Operator")
    print("Runtime can greet you by any nickname you choose.\n")
    name = input("What should KayocktheOS call you? [Kayock]: ").strip() or "Kayock"
    text = text.replace("display_name: Kayock", f"display_name: {name}").replace("first_boot: true", "first_boot: false")
    profile.write_text(text, encoding="utf-8")
    print(f"\nOperator profile created. Welcome back, {name}.")
    input("Press Enter to continue to the Bridge...")
    return name

def find_browser_exe():
    for folder in [ROOT/"Shell/Kayock_Browser", ROOT/"Interface/Kayock_Browser"]:
        if not folder.exists(): continue
        for pattern in ["Kayock-Browser*.exe", "KayockBrowser*.exe", "*Browser*.exe", "*.exe"]:
            matches = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            if matches: return matches[0]
    return None

def dashboard_path():
    return ROOT / "Shell/Bridge_Dashboard/index.html"

def api_alive():
    try:
        with urllib.request.urlopen(API_URL + "/api/ping", timeout=0.5) as r:
            return r.status == 200
    except Exception:
        return False

def start_api():
    global api_process
    if api_alive():
        return True
    script = ROOT / "System/API/core_api.py"
    try:
        api_process = subprocess.Popen([sys.executable, str(script)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(25):
            if api_alive():
                log("Core API started.")
                return True
            time.sleep(0.12)
    except Exception as e:
        log(f"Core API failed to start: {e}")
    return False

def health_report():
    checks = [
        ("Manifest", ROOT/"manifest.yaml"),
        ("Operator Profile", ROOT/"System/Config/operator.yaml"),
        ("Module Registry", ROOT/"System/Registry/modules"),
        ("Logs", ROOT/"System/Logs"),
        ("Core API Script", ROOT/"System/API/core_api.py"),
        ("Bridge Dashboard", dashboard_path()),
    ]
    print("\nSystem Health\n" + "-"*72)
    for label, path in checks:
        print(f"[{'OK' if path.exists() else 'MISSING':7}] {label:24} {path.relative_to(ROOT) if path.exists() else path}")
    browser = find_browser_exe()
    print(f"[{'OK' if browser else 'MISSING':7}] Kayock Browser EXE        {browser.relative_to(ROOT) if browser else 'Copy EXE into Shell/Kayock_Browser'}")
    print(f"[{'OK' if api_alive() else 'OFFLINE':7}] Local Core API           {API_URL}")

def launch_shell():
    browser = find_browser_exe()
    if not browser:
        print("\nKayock Browser was not found.")
        print("Copy Kayock-Browser*.exe into Shell/Kayock_Browser or Interface/Kayock_Browser.")
        return
    start_api()
    target = str(dashboard_path().resolve())
    log(f"Launching Shell dashboard: {browser} -> {target}")
    try:
        subprocess.Popen([str(browser), target], cwd=str(browser.parent))
        print("\nKayock Browser Shell launch requested.")
        print(f"Dashboard: {target}")
    except Exception as e:
        log(f"Shell launch failed: {e}")
        print(f"Launch failed: {e}")

def show_bridge(name):
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("="*72)
        print(" "*27 + "KayocktheOS")
        print(" "*17 + "Portable AI Operating System")
        print(" "*17 + f"Version {VERSION} - {CODENAME}")
        print("="*72)
        print(f"\nWelcome back, {name}.")
        print('"Wonder is a tool. Build with it."')
        health_report()
        print("\nBridge Menu\n" + "-"*72)
        print("1. Show health report")
        print("2. Start Local Core API")
        print("3. Open raw API status")
        print("4. Launch Kayock Browser Shell Dashboard")
        print("5. Open logs folder")
        print("6. Show dashboard path")
        print("7. Exit")
        choice = input("\nSelect option: ").strip()
        if choice == "1": health_report(); input("\nPress Enter...")
        elif choice == "2":
            print("\nCore API online." if start_api() else "\nCore API failed.")
            input("\nPress Enter...")
        elif choice == "3":
            start_api()
            try: os.startfile(API_URL + "/api/status")
            except Exception: print(API_URL + "/api/status")
            input("\nPress Enter...")
        elif choice == "4": launch_shell(); input("\nPress Enter...")
        elif choice == "5":
            try: os.startfile(LOG_DIR)
            except Exception as e: print(e)
            input("\nPress Enter...")
        elif choice == "6":
            print(f"\nDashboard: {dashboard_path()}")
            print(f"API: {API_URL}/api/status")
            input("\nPress Enter...")
        elif choice == "7":
            log("Bridge exited by Operator.")
            break

def main():
    log(f"KayocktheOS {VERSION} boot started.")
    name = ensure_operator_profile()
    start_api()
    show_bridge(name)

if __name__ == "__main__":
    main()
