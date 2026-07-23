# Agent Fox Technical Core V1A-3C1-R1

Mission: `ENG-20260721-220855-64D244`

This corrective component preserves the original failed V1A-3C1 builder unchanged and installs a new
Web Portable closure builder that fixes two zero-value integrity defects.

The original expression `int(value or -1)` converted a legitimate `size_bytes` value of `0` into `-1`.
That caused the verified zero-byte file `Z:/FOXAI/core/__init__.py` to be falsely reported as drifted. The
same truthiness error existed in generated-output size validation.

R1 uses explicit `None` handling. A real zero remains zero; a missing size field is rejected with a clear
error. Regression tests cover a valid zero-byte source, a missing size field, a nonzero mismatch, and a
valid zero-byte generated output.

The protected context remains:

- `Z:/FOXAI/START_FOXAI_WEB_PORTABLE.bat`
- `Z:/FOXAI/env/python/python.exe`
- `Z:/FOXAI/core/foxai_web.py`

The preliminary closure must reproduce exactly 57 reached sources, 165
edges, and 1 unresolved branch before source parsing. Only reached
first-party files are read, each at most once, with an 8 MiB source-buffer ceiling.

No FOXAI source, launcher, import, package, model, Llama component, ComfyUI component, Hanger Bay content,
immutable evidence, original failed builder, or rollback drive K: is executed or modified.
