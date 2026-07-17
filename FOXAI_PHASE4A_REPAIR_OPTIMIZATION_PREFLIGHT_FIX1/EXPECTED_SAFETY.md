# Phase 4A Safety Contract

Allowed:

- Read and hash known FOXAI files
- Hash files explicitly listed by the Desktop runtime manifest
- Perform bounded scans inside known FOXAI directories
- Parse selected Python files with `ast` without writing bytecode
- Run local interpreter import probes
- Run installed-tool version probes
- Inventory wheel/model filenames and sizes
- Write reports only inside this preflight package

Forbidden:

- Modify, repair, patch, move, rename, or delete live FOXAI files
- Install or download packages
- Access the network
- Launch FOXAI, ComfyUI, browser, models, or background services
- Recursively scan entire drives
- Execute the FOXAI test suite
- Treat missing optional tools as approval to install them


## FIX1 host-probe boundary

The host-Python probe may enable the host user's normal Python user-site search
because that matches the already-proven ComfyUI launcher. It remains an import-only
probe: no ComfyUI service, GUI, model, installer, or network operation is started.
