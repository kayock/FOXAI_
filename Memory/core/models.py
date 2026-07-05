from core.paths import MODELS

def find_models():
    if not MODELS.exists():
        return []
    return sorted(MODELS.rglob("*.gguf"))
