FOXAI COMFYUI OPERATIONS QUICK PANEL

1. Close FOXAI Desktop, WebUI, and ComfyUI.
2. Extract this whole folder directly inside Z:\FOXAI.
   Expected folder:
   Z:\FOXAI\FOXAI_COMFY_OPS_QUICK_PANEL\
3. Run APPLY_COMFY_OPS_QUICK_PANEL.bat.
4. Answer Y once.
5. Start FOXAI using the shortcuts that already work.

Desktop:
- Click COMFYUI OPERATIONS in the sidebar.

WebUI:
- Expand the green COMFYUI OPERATIONS panel at the lower-right.

The existing two-window recovery launcher keeps the same filename, so its shortcut
continues to work. It now mirrors the visible ComfyUI console to:
Runtime\ComfyUI\logs\live\current.log

The patch creates a timestamped backup before replacing anything.
Run ROLLBACK_COMFY_OPS_QUICK_PANEL.bat only if the patch causes a problem.
