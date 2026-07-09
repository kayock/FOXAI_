# Feature 001B - Runtime Auto Launcher

This feature searches `Z:\FOXAI` for runtime executables and creates a launch helper.

## API

```text
http://127.0.0.1:8844/api/runtime-launcher
```

## Launch helper

```text
Z:\KayocktheOS\AI\Gateway\LAUNCH_SELECTED_MODEL_RUNTIME.bat
```

Run that BAT, leave the runtime window open, then test chat through `/api/chat`.

## Notes

This does not silently start executables. The Operator launches the runtime explicitly.
