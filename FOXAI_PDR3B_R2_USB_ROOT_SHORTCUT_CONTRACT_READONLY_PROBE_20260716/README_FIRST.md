# FOXAI Portable Desktop Runtime Phase 3B-R2

## USB-Root Shortcut Contract Evidence Probe

The Phase 3B-R1 results were safe and useful, but they exposed two diagnostic gaps:

1. R1 searched `Z:\FOXAI` and Windows shortcut surfaces, but not the USB volume root `Z:\`.
2. A blank Windows icon value such as `,0` was incorrectly normalized as though it were a path inside the probe folder.

R2 corrects those diagnostic assumptions. It also reads the existing shortcut-creation script and checks both `Icons` and `assets` icon candidates rather than guessing.

## Run

1. Extract this entire folder inside `Z:\FOXAI`.
2. Double-click `RUN_USB_ROOT_SHORTCUT_CONTRACT_PROBE.bat`.
3. Open the newest folder under `probe_output`.
4. Zip that newest output folder and upload it.

## Safety

This is read-only and evidence-only. It does not create, edit, repair, or delete a shortcut. It does not launch FOXAI, install packages, access the network, or change any live source, launcher, runtime, model, or configuration file.

Phase 3C remains blocked regardless of the probe result.
