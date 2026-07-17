# FOXAI Phase 4C-P — WebUI ComfyUI Exact Patch Preview

Phase 4B confirmed the WebUI launches ComfyUI with the wrong Python/environment:

- `pycmd()` prefers `Z:\FOXAI\env\python\python.exe`.
- PyTorch 2.12.1+cpu is installed in the host Python user-site.
- The Web launcher sets `PYTHONNOUSERSITE=1`.
- The ComfyUI child receives no explicit clean environment.

This preview proposes one modification only:

```text
Z:\FOXAI\core\foxai_web.py
```

It resolves host Python from PATH first and removes portable Python isolation variables only from the ComfyUI child. The WebUI controller remains isolated.

This package cannot apply the patch.
