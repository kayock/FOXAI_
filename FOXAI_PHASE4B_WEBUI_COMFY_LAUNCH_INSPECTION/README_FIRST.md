# FOXAI Phase 4B — WebUI ComfyUI Launch Inspection

This read-only package determines why the WebUI ComfyUI launch control does not work while the combined portable BAT does.

## It inspects

- `START_FOXAI_WEB_PORTABLE.bat`
- `core\foxai_web.py`
- Related bounded source references under `core`, `ui`, `web`, `static`, and `templates`
- Exact ComfyUI subprocess command, arguments, working directory, and environment handling
- Port `8188` and route references
- Whether stderr or startup failures are captured
- Host Python under:
  - the inherited USB-controller environment
  - the clean environment used by the working combined launcher

## Expected decisive result

When inherited host Python cannot import `torch`, but clean host Python can, the result is:

```text
CONFIRMED_ENVIRONMENT_INHERITANCE_FAILURE
```

The WebUI risk classifier then checks whether the Web launcher blocks user-site packages and whether `core\foxai_web.py` supplies an explicit clean child environment.

## Safety

No live source is modified. FOXAI, WebUI, ComfyUI, browser, models, and network are not started. The only child processes are two local `import torch` probes.

## Run

1. Extract this complete folder inside `Z:\FOXAI`.
2. Run `RUN_PHASE4B_WEBUI_COMFY_INSPECTION.bat`.
3. Zip and upload only the newest:

```text
FOXAI_PHASE4B_WEBUI_COMFY_LAUNCH_INSPECTION\INSPECTION_OUTPUT\<timestamp>\UPLOAD_THIS
```
