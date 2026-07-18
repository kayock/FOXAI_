FOXAI QUIET COMFYUI STARTUP

This removes the green ComfyUI console from normal Desktop and WebUI startup.

Why:
- FOXAI's progress bar is now accurate.
- The separate comfy_console_tee.py capture wrapper produced an Errno 22 crash.
- The actual ComfyUI process survived, proving the wrapper—not generation—failed.

New behavior:
- ComfyUI starts hidden.
- Its raw output is redirected to a normal unique log file.
- Desktop/WebUI operations panels and Red Canvas can still read progress.
- Duplicate ComfyUI processes are prevented.
- Existing shortcut targets remain unchanged.

Install:
1. Close FOXAI Desktop, WebUI, and the green ComfyUI window.
2. Extract this whole folder directly inside Z:\FOXAI.
3. Run APPLY_QUIET_COMFYUI_STARTUP.bat.
4. Press Y once.
5. Test Desktop, then WebUI.

The old comfy_console_tee.py file is left untouched for rollback/history but is no
longer called by the normal launchers.
