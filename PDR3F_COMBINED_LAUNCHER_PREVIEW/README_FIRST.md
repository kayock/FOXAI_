# FOXAI Portable Desktop Runtime Phase 3F-P

## Combined Portable Workshop Launcher Preview

The read-only discovery proved that the current working shortcut performs this sequence:

1. Start `ComfyUI\main.py --cpu` using the host `python` command.
2. Wait eight seconds.
3. Start `foxai.py` using host Python.

The proposed launcher preserves the proven ComfyUI portion while replacing only the FOXAI portion with the already-verified USB Desktop launcher.

## Proposed new file

```text
Z:\FOXAI\START_FOXAI_WORKSHOP_PORTABLE.bat
```

It will:

1. Verify all required files are present.
2. Verify that the host `python.exe` command used by working ComfyUI is resolvable.
3. Verify the USB-owned Desktop runtime before starting anything.
4. Start ComfyUI CPU with `python.exe main.py --cpu`.
5. Wait eight seconds.
6. Start FOXAI through `START_FOXAI_DESKTOP_PORTABLE.bat`.

The ComfyUI child process explicitly clears `PYTHONHOME` and `PYTHONPATH` so the USB Desktop runtime cannot contaminate the proven host-Python ComfyUI environment.

## Run

1. Extract this complete folder inside `Z:\FOXAI`.
2. Run `RUN_PHASE3F_COMBINED_PREVIEW.bat`.
3. Zip and upload only the newest:
   `PREVIEW_OUTPUT\<timestamp>\UPLOAD_THIS`

This package is preview-only. It cannot add or run the launcher and does not change either shortcut.
