# FOXAI Portable Desktop Runtime Phase 3E-P

This preview prepares a separate portable Desktop launcher without changing the existing shortcut or stable launcher.

The verified live diagnostic is:

```text
desktop_runtime_diagnostic_20260717T010709Z.json
SHA-256: 66a517da70407b60d2f03605545c325e1194e664a5083213ceb7e53c6306a12a
```

## Proposed new file

```text
Z:\FOXAI\START_FOXAI_DESKTOP_PORTABLE.bat
```

The launcher:

1. Sets the USB-owned Desktop Python environment.
2. Runs `System\PortableRuntime\verify_desktop_runtime.py`.
3. Stops if the runtime verification fails.
4. Launches `foxai.py` using `Runtime\Desktop\python\python.exe`.
5. Does not start ComfyUI.
6. Does not fall back to host Python.

## Run

1. Extract this complete folder inside `Z:\FOXAI`.
2. Run `RUN_PHASE3E_LAUNCHER_PREVIEW.bat`.
3. Zip and upload only the newest:
   `PREVIEW_OUTPUT\<timestamp>\UPLOAD_THIS`

This package is preview-only and cannot apply or launch the proposed launcher.
