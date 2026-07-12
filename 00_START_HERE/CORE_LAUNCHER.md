# Core Launcher v0.0.2

The Core Launcher is the first executable heart of KayocktheOS.

It is responsible for:

- Reading `manifest.yaml`
- Reading `System/Config/operator.yaml`
- Starting the Bridge-style startup screen
- Verifying the folder structure
- Detecting local model files
- Reporting department status
- Writing boot logs to `System/Logs`

The launcher does not contain Academy, Repair Bay, Creative Studio, Browser, or AI logic. It only verifies and coordinates the operating environment.

## Human Naming Standard

Documentation uses **Operator**.
Runtime greeting uses the nickname stored in `operator.yaml`.

## How to Start

Double-click:

```text
Start_KayocktheOS.bat
```

Or run directly:

```text
python System/Launchers/launch.py
```

## Model Detection

The launcher checks `AI/Models` for common local model file types:

- `.gguf`
- `.safetensors`
- `.bin`
- `.pt`
- `.pth`
- `.onnx`

It is okay if no models are copied into this folder yet. KayocktheOS may reference external FOXAI models through `AI/Model_Links`.
