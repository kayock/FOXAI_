# FOXAI Phase 4C-A — Approved WebUI ComfyUI Patch Apply

Exact operator approval received:

```text
APPROVE FOXAI4C 729AF0685C9C
```

Approved plan ID:

```text
729af0685c9c323e186fb2d8122aff0216da4daa53ee84e3735919b23e38575a
```

## Exact operation

The package backs up and modifies only:

```text
Z:\FOXAI\core\foxai_web.py
```

Expected hash transition:

```text
Before: ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7
After:  2ec7aff76529a9c9a477d247753227bde9f03930f1d3bd05111b3b9a2fd3be2f
```

A verified backup is created under:

```text
Z:\FOXAI\Backups\Phase4C_WebUI_Comfy\<timestamp>\core\foxai_web.py
```

The package stages and syntax-checks the proposed file, rechecks protected state,
performs one atomic replacement, verifies the result, and rolls back from the
backup if verification fails.

It does not change launchers, shortcuts, ComfyUI source, or any other FOXAI
source. It does not launch FOXAI, WebUI, ComfyUI, a browser, or a model.

## Run

1. Extract this complete folder inside `Z:\FOXAI`.
2. Run `RUN_PHASE4C_APPLY.bat`.
3. Type the exact approval phrase when prompted.
4. Upload only the newest:
   `APPLY_OUTPUT\<timestamp>\UPLOAD_THIS`

Do not test the WebUI ComfyUI button until the apply receipt has been reviewed.
