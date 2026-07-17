# FOXAI Portable Desktop Runtime Phase 3C

## Quarantined Runtime Acquisition and Verification

Phase 3B passed with `exact_design_verified`. This package performs the next approved step: copying a full Windows Python/Tcl/Tk runtime and the existing Desktop-only packages into a quarantine area.

It does **not** apply the runtime to live FOXAI.

### Bounded sources

It probes only:

- `Z:\FOXAI\.venv\Scripts\python.exe`, when present
- `C:\Python314\python.exe`
- the small list returned by `where python`, excluding WindowsApps aliases

The actual runtime copy is bounded to the selected Python installation folder. It does not scan other drives.

### Writes

Everything is written under:

```text
PDR3C_QUARANTINE\Q\<timestamp>\
```

No live FOXAI file, shortcut, launcher, runtime, configuration, model, or source file is changed.

### Expected duration

The source probes should take seconds. Copying and hashing a full Python runtime to USB may take roughly 1–10 minutes depending on the USB port and current disk load. Progress appears every 250 runtime files.

### Run

1. Extract this entire folder inside `Z:\FOXAI`.
2. Run `RUN_PHASE3C_QUARANTINE.bat`.
3. Wait for the final state.
4. Open the newest `Q\<timestamp>\UPLOAD_THIS` folder.
5. Zip and upload **only** `UPLOAD_THIS`; do not upload the large quarantine runtime.

A successful receipt reports:

```text
state: quarantine_acquisition_verified
verified: true
```

Phase 3D live apply remains blocked.
