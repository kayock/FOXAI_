# FOXAI Phase 3B-R3 FAST

This replaces the slow R2 probe.

R2 recursively walked the USB volume and could take far too long on a large or busy drive. R3 performs no recursive drive scan. It checks only shortcuts directly inside:

- the USB root
- the FOXAI root
- FOXAI\Memory
- the current user's Desktop
- the Public Desktop
- the two top-level Start Menu Programs folders

It also reads the existing shortcut-creation and launcher files as evidence.

## Run

1. Cancel the old R2 window with Ctrl+C, then Y if asked.
2. Extract this folder inside Z:\FOXAI.
3. Double-click RUN_FAST_SHORTCUT_PROBE.bat.
4. Zip the newest folder in probe_output and upload it.

The run should normally finish in seconds, not minutes.

## Safety

This is read-only. It does not create, edit, delete, or launch shortcuts. It does not launch FOXAI, install packages, access the network, or alter live FOXAI files. Phase 3C remains blocked.
