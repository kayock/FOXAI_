from pathlib import Path
import json
import datetime
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "AI" / "Gateway"
STATE = GATEWAY / "core_working_state.json"
CONFIG = GATEWAY / "core_working_config.json"

FOXAI = Path("Z:/FOXAI")
ANYTHING_PATHS = [
    Path("Z:/Apps/AnythingLLM/AnythingLLM.exe"),
    Path("Z:/Apps/New folder/AnythingLLM/AnythingLLM.exe"),
    Path("Z:/AnythingLLM/AnythingLLM.exe"),
    ROOT / "Apps" / "AnythingLLM" / "AnythingLLM.exe",
]
KOBOLD_PATHS = [
    ROOT / "Engine" / "KoboldCpp" / "koboldcpp.exe",
    FOXAI / "Engine" / "koboldcpp.exe",
    FOXAI / "koboldcpp.exe",
]
COMFY_PATHS = [
    FOXAI / "ComfyUI" / "run_nvidia_gpu.bat",
    FOXAI / "ComfyUI" / "run_cpu.bat",
    FOXAI / "ComfyUI" / "main.py",
]

SAFE_MODEL = FOXAI / "Models" / "Chat" / "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"

def first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def probe(url, timeout=2):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as res:
            return {"ok": True, "status": res.status}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def status():
    anything = first_existing(ANYTHING_PATHS)
    kobold = first_existing(KOBOLD_PATHS)
    comfy = first_existing(COMFY_PATHS)

    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "feature": "Feature 006 - Core Working Launch Cleanup",
        "root": str(ROOT),
        "anythingllm": {
            "found": bool(anything),
            "path": str(anything) if anything else None,
            "health": probe("http://127.0.0.1:3001")
        },
        "koboldcpp": {
            "found": bool(kobold),
            "path": str(kobold) if kobold else None,
            "model": str(SAFE_MODEL) if SAFE_MODEL.exists() else None,
            "health": probe("http://127.0.0.1:5001")
        },
        "comfyui": {
            "found": bool(comfy),
            "path": str(comfy) if comfy else None,
            "health": probe("http://127.0.0.1:8188")
        },
        "notes": [
            "FIRST_CONTACT_START_RUNTIME.bat is now legacy and delegates to START_CORE_WORKING.bat.",
            "No launcher should call llama-batched-bench.exe.",
            "AnythingLLM handles project/code/document scanning.",
            "ComfyUI remains the creative engine in FOXAI.",
            "KoboldCpp or another runtime can be used later for chat models."
        ]
    }

def quote(p):
    return '"' + str(p).replace('"', '') + '"'

def write_launchers():
    GATEWAY.mkdir(parents=True, exist_ok=True)

    anything = first_existing(ANYTHING_PATHS)
    kobold = first_existing(KOBOLD_PATHS)
    comfy = first_existing(COMFY_PATHS)

    core = f"""@echo off
title KayocktheOS Core Working Launcher
color 0A
cd /d "{ROOT}"

echo ==========================================
echo KayocktheOS Core Working Launcher
echo ==========================================
echo.
echo This is the clean startup path.
echo It does NOT call llama-batched-bench.exe.
echo.
echo 1. Start AnythingLLM
echo 2. Start KoboldCpp runtime
echo 3. Start ComfyUI / FOXAI
echo 4. Show status
echo 5. Exit
echo.
set /p choice=Choose option: 

if "%choice%"=="1" goto anything
if "%choice%"=="2" goto kobold
if "%choice%"=="3" goto comfy
if "%choice%"=="4" goto status
goto end

:anything
echo.
"""
    if anything:
        core += f'start "" {quote(anything)}\n'
    else:
        core += 'echo AnythingLLM not found. Expected Z:\\Apps\\AnythingLLM or Z:\\Apps\\New folder\\AnythingLLM.\n'
    core += "pause\ngoto end\n\n:kobold\n"
    if kobold and SAFE_MODEL.exists():
        core += f'start "KayocktheOS KoboldCpp" {quote(kobold)} --model {quote(SAFE_MODEL)} --port 5001 --contextsize 4096\n'
    elif kobold:
        core += f'echo KoboldCpp found at {kobold}, but safe model was not found.\n'
    else:
        core += 'echo KoboldCpp not found. Put koboldcpp.exe in Z:\\KayocktheOS\\Engine\\KoboldCpp\\.\n'
    core += "pause\ngoto end\n\n:comfy\n"
    if comfy:
        if comfy.suffix.lower() == ".bat":
            core += f'start "FOXAI ComfyUI" {quote(comfy)}\n'
        else:
            core += f'echo ComfyUI main.py found at {comfy}. Use your existing FOXAI ComfyUI launcher.\n'
    else:
        core += 'echo ComfyUI launcher not found under Z:\\FOXAI\\ComfyUI.\n'
    core += "pause\ngoto end\n\n:status\n"
    core += 'python AI\\core_working.py\n'
    core += "pause\ngoto end\n\n:end\nexit /b\n"

    (GATEWAY / "START_CORE_WORKING.bat").write_text(core, encoding="utf-8")

    legacy = """@echo off
title KayocktheOS First Contact Runtime - Legacy Redirect
color 0E
echo ==========================================
echo KayocktheOS First Contact Runtime
echo ==========================================
echo.
echo This old launcher has been disabled because it was calling
echo llama-batched-bench.exe, which is not a chat server.
echo.
echo Redirecting to the Core Working Launcher...
echo.
call "%~dp0START_CORE_WORKING.bat"
"""
    (GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat").write_text(legacy, encoding="utf-8")

    anything_bat = "@echo off\n"
    anything_bat += "title KayocktheOS AnythingLLM\ncolor 0A\n"
    if anything:
        anything_bat += f'start "" {quote(anything)}\n'
    else:
        anything_bat += 'echo AnythingLLM not found.\n'
        anything_bat += 'echo Expected: Z:\\Apps\\AnythingLLM\\AnythingLLM.exe\n'
        anything_bat += 'echo Or:       Z:\\Apps\\New folder\\AnythingLLM\\AnythingLLM.exe\npause\n'
    (GATEWAY / "START_ANYTHINGLLM.bat").write_text(anything_bat, encoding="utf-8")

    state = status()
    save_json(STATE, state)
    save_json(CONFIG, {
        "primary_launcher": str(GATEWAY / "START_CORE_WORKING.bat"),
        "legacy_first_contact_redirect": str(GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat"),
        "anythingllm_launcher": str(GATEWAY / "START_ANYTHINGLLM.bat"),
        "created_at": datetime.datetime.now().isoformat(timespec="seconds")
    })
    return state

if __name__ == "__main__":
    print(json.dumps(write_launchers(), indent=2))
