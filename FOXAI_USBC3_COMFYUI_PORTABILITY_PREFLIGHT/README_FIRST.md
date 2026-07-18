# FOXAI USB C3 — Creative Studio / ComfyUI Portability Preflight

This read-only preflight determines exactly what remains before Creative Studio
can be called fully portable.

It inspects:

- USB and host Python runtimes
- `torch`, `torchvision`, and `torchaudio` availability and origin
- Whether torch is USB-owned or host-supplied
- Current ComfyUI launchers and WebUI launch logic
- Required ComfyUI directories and safe-create candidates
- Existing ComfyUI models and folder sizes
- Relevant USB wheelhouse contents
- USB free space
- Existing torch package footprint
- Exact source snapshots needed for a later preview

## Run

1. Extract this complete folder inside `Z:\FOXAI`.
2. Run `RUN_USBC3_PREFLIGHT.bat`.
3. Upload the newest:

```text
PREFLIGHT_OUTPUT\<timestamp>\UPLOAD_THIS
```

The preflight does not install or download anything, create missing folders,
modify FOXAI, or launch ComfyUI.
