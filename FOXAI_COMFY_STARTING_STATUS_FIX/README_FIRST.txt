FOXAI COMFYUI STARTING STATUS FIX

Use this instead of the earlier OFFLINE-display hotfix.

1. Close FOXAI Desktop and WebUI. ComfyUI may remain open.
2. Extract this entire folder directly into Z:\FOXAI.
3. Run APPLY_COMFY_STARTING_STATUS_FIX.bat.
4. Press Y once.
5. Restart WebUI.

Expected:
- While the green console is loading at 5%, 10%, 25%, etc.: STARTING.
- Once port 8188 responds: READY/ONLINE.
- During image generation: GENERATING where progress is available.

This modifies only:
- core\comfy_ops_monitor.py
- core\foxai_web.py
