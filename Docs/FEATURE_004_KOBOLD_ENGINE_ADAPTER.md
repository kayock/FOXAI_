# Feature 004 - Kobold Engine Adapter

This pivots KayocktheOS away from owning the AI runtime directly.

## Design

```text
KayocktheOS Bridge
    ↓
Core API
    ↓
Engine Adapter
    ↓
KoboldCpp
    ↓
GGUF Models in FOXAI
```

## Expected engine path

```text
Z:\KayocktheOS\Engine\KoboldCpp\koboldcpp.exe
```

## Launcher

```text
Z:\KayocktheOS\AI\Gateway\START_KOBOLD_ENGINE.bat
```
