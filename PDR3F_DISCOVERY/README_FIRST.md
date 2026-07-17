# FOXAI Portable Desktop Runtime Phase 3F

## Combined Startup Read-Only Discovery

This package inspects the existing working Desktop shortcut and launcher chain so its proven ComfyUI behavior can be reproduced without guessing.

It captures:

- Both USB-root shortcut targets, arguments, working directories, and icon settings
- The exact working Desktop launcher and bounded local script chain
- Exact hashes and UTF-8 snapshots of discovered launcher scripts
- ComfyUI-related startup lines and port/argument references
- Shallow listings of likely ComfyUI/System/Scripts/Runtime locations
- Targeted ComfyUI/startup references in `foxai.py`, `ui/main_window.py`, and `core/foxai_web.py`
- Protected-file and shortcut hashes before and after

It does not modify FOXAI, launch FOXAI or ComfyUI, use the network, install anything, or scan entire drives.

## Run

1. Extract this complete folder inside `Z:\FOXAI`.
2. Run `RUN_PHASE3F_DISCOVERY.bat`.
3. Zip and upload only the newest:

```text
PDR3F_DISCOVERY\DISCOVERY_OUTPUT\<timestamp>\UPLOAD_THIS
```
