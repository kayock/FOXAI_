# Feature 004C - Kobold Core Repair

This patch is based on the uploaded KayocktheOS source tree.

## Fixes

- Repairs malformed Core API Kobold return values.
- Replaces the Kobold adapter with a cleaner single source of truth.
- Makes `/api/chat` prefer the Kobold adapter.
- Tries OpenAI-compatible Kobold chat first, then native Kobold generate.
- Rewrites `AI/Gateway/START_KOBOLD_ENGINE.bat`.

## After install

1. Put `koboldcpp.exe` at:

```text
Z:\KayocktheOS\Engine\KoboldCpp\koboldcpp.exe
```

2. Run:

```text
Z:\KayocktheOS\AI\Gateway\START_KOBOLD_ENGINE.bat
```

3. Restart KayocktheOS Core and Bridge.
