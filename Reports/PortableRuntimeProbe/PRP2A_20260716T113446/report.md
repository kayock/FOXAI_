# FOXAI Portable Runtime Phase 2A — Read-Only Probe

- Created: `2026-07-16T17:34:46.200942+00:00`
- Root: `Z:\FOXAI`
- State: **read_only_probe_complete**
- Automatic install: **False**
- Automatic repair: **False**
- Automatic launch: **False**

## Must fix before another-computer testing

- Bundled Python borrows packages from the Windows user-site folder: psutil, requests, Pillow, customtkinter
- USB-only (-s) embedded Python lacks required packages: psutil, requests, Pillow, customtkinter, pycasbin/casbin
- Desktop launcher selects system Python instead of an explicitly USB-owned runtime.
- Root .venv base interpreter points outside the USB: C:\Users\kayoc\AppData\Local\Python\pythoncore-3.14-64
- Fleet registry contains 11 drive-bound path fields.

## Separate runtime decisions

- ComfyUI/PyTorch needs a separately verified USB-owned runtime strategy; do not fold a large Torch install into the small core runtime blindly.

## Candidate core packages

- `psutil`
- `requests`
- `Pillow`
- `customtkinter`
- `pycasbin/casbin`
- `watchdog`
- `pluggy`

## Candidate creative packages

- `torch`
- `numpy`

## Proposed architecture

- **Core Runtime:** USB-owned embedded Python package directory; launch with user-site disabled.
- **Desktop:** Use the same USB-owned core runtime where tkinter is available.
- **Creative Runtime:** Keep ComfyUI/Torch isolated from the small core runtime and verify separately.
- **Registry:** Resolve FOXAI and same-drive Hanger Bay paths from the detected USB root instead of Z:.

## Safety

This probe only reads files and executes import checks. It does not install
packages, modify Python paths, rewrite launchers or registries, start
services, create ComfyUI folders, or delete anything. Its only writes are
this timestamped report and receipt.
