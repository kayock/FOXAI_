FOXAI RED CANVAS LIVE PROGRESS FIX

This fixes only the lagging purple Red Canvas progress bar.

Install:
1. Close FOXAI Desktop.
2. Extract this entire folder directly into Z:\FOXAI.
3. Run APPLY_RED_CANVAS_LIVE_PROGRESS.bat.
4. Press Y once.
5. Restart FOXAI Desktop and generate one image.

Expected:
- While SDXL loads: the bar stays at 0 and the text says LOADING IMAGE MODEL.
- When the green console shows 5%, 10%, 25%, 75%, etc., the purple bar
  displays the same real percentage.
- Completion still comes from the existing successful generation result.

The WebUI, launchers, ComfyUI runtime, models, prompts, workflows, and output
files are not modified.
