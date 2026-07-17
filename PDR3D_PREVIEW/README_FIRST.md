# FOXAI Portable Desktop Runtime Phase 3D-P

## Preview-First Exact Live Apply Plan

Phase 3C passed. This package performs the next safe step: it creates the exact live-apply preview without applying anything.

### It verifies

- The latest successful Phase 3C quarantine run.
- All 3,683 quarantined source-file hashes.
- Protected FOXAI baseline and shortcut hashes before and after.
- Every exact proposed destination path.
- Available USB free space.

### It proposes only new files

```text
Runtime\Desktop\python\**
Runtime\Desktop\site-packages\**
Runtime\Desktop\DESKTOP_RUNTIME_MANIFEST.json
System\PortableRuntime\verify_desktop_runtime.py
START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat
```

It proposes no modification to existing shortcuts, launchers, source, Core runtime, Config files, ComfyUI, or Models.

The normal portable Desktop launcher is deliberately deferred. The diagnostic runtime must pass first.

### Run

1. Extract this folder inside `Z:\FOXAI`.
2. Run `RUN_PHASE3D_PREVIEW.bat`.
3. It hashes 3,683 quarantine files, so it may take roughly 10 seconds to a few minutes on USB.
4. Zip and upload only the newest:
   `PREVIEW_OUTPUT\<timestamp>\UPLOAD_THIS`

No apply script is included. An exact plan ID and approval phrase are generated for review.
