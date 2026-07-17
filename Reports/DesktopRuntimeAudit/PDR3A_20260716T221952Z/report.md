# FOXAI Portable Desktop Runtime Phase 3A
## Read-Only Audit

- Created: `2026-07-16T22:19:52.871020+00:00`
- State: **desktop_runtime_audit_verified**
- Verified: **True**
- Machine: `DESKTOP-G9ERN9B`
- Desktop GUI launched: **False**
- Model or ComfyUI action: **None**
- Pip/package installation: **None**
- Live files modified: **False**
- Network access: **False**

## Stable shortcut

- Matching resolved shortcut found: **True**
- Matching resolved shortcut count: **1**

## Runtime findings

- Bundled embedded Python has Tk: **False**
- Existing `.venv` has Tk: **True**
- Discovered system Pythons with Tk: **7**

## Must fix

- The current USB embedded Python has no usable Tcl/Tk runtime; it cannot become the Desktop GUI runtime by wheels alone.
- The USB embedded runtime does not own CustomTkinter.
- The USB embedded runtime does not own Pillow/PIL.
- The existing .venv is tied to a Python home outside the USB.
- At least one Desktop launcher invokes system Python by name.

## Reusable portable-core components

- Runtime/Core already owns psutil; the Desktop runtime can reuse it if import isolation remains explicit.
- Runtime/Core already owns requests; the Desktop runtime can reuse it if import isolation remains explicit.
- Runtime/Core already owns pycasbin; the Desktop runtime can reuse it if import isolation remains explicit.
- Runtime/Core already owns watchdog; the Desktop runtime can reuse it if import isolation remains explicit.
- Runtime/Core already owns pluggy; the Desktop runtime can reuse it if import isolation remains explicit.

## Preserve

- Keep the currently working Desktop shortcut and launcher unchanged until the USB-owned Desktop runtime passes guarded launch testing.
- Keep the working portable WebUI runtime and launcher unchanged.
- Keep ComfyUI/PyTorch outside this Desktop-runtime milestone.
- Keep all model files and model-source registry behavior unchanged.

## Phase 3B design direction

- Acquire or assemble a complete USB-owned CPython runtime that includes Tcl/Tk rather than modifying the embedded WebUI runtime.
- Give the Desktop runtime its own isolated site-packages layer.
- Reuse approved Runtime/Core packages through an explicit path contract where versions are compatible.
- Add Desktop-only packages such as CustomTkinter and Pillow to a separate verified wheelhouse/runtime manifest.
- Create a new portable Desktop launcher beside the existing stable launcher; do not overwrite the stable launcher initially.
- Validate icon/assets, working directory, context menus, and model launch integration before changing shortcuts.

## Safety

This audit only reads explicitly scoped FOXAI files, known runtime
locations, and Desktop shortcut metadata. It does not open the GUI,
run pip, install packages, change shortcuts, start models, contact
network services, or modify FOXAI.
