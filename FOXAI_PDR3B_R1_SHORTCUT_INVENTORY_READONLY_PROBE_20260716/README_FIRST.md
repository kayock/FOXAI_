# FOXAI Portable Desktop Runtime Phase 3B-R1
## Read-Only Shortcut Inventory and Resolution Probe

This recovery probe was created after Phase 3B stopped safely because its protected shortcut discovery returned zero matches and empty `inspected` lists.

## Purpose

Identify the real FOXAI `.lnk` files and resolve each shortcut's:

- full shortcut path
- target
- arguments
- working directory
- icon location
- target/icon existence
- USB ownership
- exact desktop/web launcher match
- before/after SHA-256

It searches only:

- a bounded FOXAI USB tree, skipping heavy runtime/model/backup/report folders
- the current user's Desktop
- the Public Desktop
- current/common Start Menu `Programs` folders

It does **not** scan the whole host computer.

## Safety contract

The probe:

- has no apply function
- does not create, edit, move, rename, or delete shortcuts
- does not alter launchers, source, runtime, packages, registry, models, or configuration
- does not launch FOXAI Desktop or WebUI
- does not access the network
- writes only inside this bundle's `probe_output` folder
- hashes the protected Phase 3B baselines before and after
- hashes every discovered shortcut before and after

## Run

1. Extract this folder inside `Z:\FOXAI`.
2. Double-click `RUN_SHORTCUT_INVENTORY_PROBE.bat`.
3. When it finishes, open the newest folder under `probe_output`.
4. Zip that newest output folder and upload it to ChatGPT.

The script normally detects the FOXAI root automatically. An advanced explicit run is also supported:

```bat
RUN_SHORTCUT_INVENTORY_PROBE.bat -Root "Z:\FOXAI"
```

## Expected output

```text
probe_output\<UTC timestamp>\
├─ SHORTCUT_INVENTORY_REPORT.md
├─ SHORTCUT_INVENTORY.json
└─ SHORTCUT_INVENTORY_RECEIPT.json
```

## Phase rule

This is still Phase **3B-R1**, not Phase 3C. Do not begin quarantined Desktop runtime acquisition until the shortcut contract is identified and Phase 3B design passes.
