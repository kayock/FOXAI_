# FOXAI USB Commissioning

Run from the USB root:

`COMMISSION_FOXAI_USB.bat`

The commissioner checks the USB before launch and reports one of:

- **READY** — the selected profile is self-contained and available;
- **READY_WITH_NOTES** — the core WebUI can start, but an optional or portable dependency needs attention;
- **NEEDS_ATTENTION** — a required core item is missing or cannot run.

## What it never does automatically

It never installs packages, downloads models, rewrites drive letters, creates missing ComfyUI folders, updates configuration, deletes files, or starts a service without the operator selecting a launcher.

## Current launcher roles

- `START_FOXAI_WEB_PORTABLE.bat` — primary current WebUI;
- `Start FoxAI.bat` — CustomTkinter desktop;
- `Start_KayocktheOS.bat` — separate alternate shell.

The alternate shell starts its own API, writes `System/Logs/boot.log`, and may update `System/Config/operator.yaml` during first boot. It is intentionally not started by the commissioning menu.

## Reports

Normal checks write a timestamped report under:

`Reports/Commissioning/`

The read-only verifier uses `--no-write`, so it creates no live report.
