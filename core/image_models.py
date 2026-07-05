from core.paths import BASE

CHECKPOINT_DIR = BASE / "ComfyUI" / "models" / "checkpoints"

def find_checkpoints():
    if not CHECKPOINT_DIR.exists():
        return ["Use workflow default"]

    models = sorted(
        p.name for p in CHECKPOINT_DIR.glob("*.safetensors")
    )

    return ["Use workflow default"] + models