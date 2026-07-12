# Feature 006 - Core Working Launch Cleanup

This patch creates one clean startup path and disables the broken legacy First Contact launcher.

## Primary Launcher

```text
Z:\KayocktheOS\AI\Gateway\START_CORE_WORKING.bat
```

## What changed

- `FIRST_CONTACT_START_RUNTIME.bat` now redirects to the Core Working Launcher.
- It should no longer call `llama-batched-bench.exe`.
- AnythingLLM is treated as the engineering/code/document brain.
- ComfyUI remains in FOXAI for creative workflows.
- KoboldCpp remains optional for local GGUF runtime.
