# Phase 2C2 R1 Exact-Preview Failure Diagnosis

The R1 exact preview stopped before any live change.

The candidate contained all four intended files, and the uploaded candidate
matches the approved preview hashes byte-for-byte.

## Cause

FOXAI's bundled CPython uses `python314._pth` isolated mode. In that mode,
the `PYTHONPATH` environment variable used by R1 was ignored. The test module
therefore could not import:

```text
core.model_sources
```

This was a verifier-launch problem, not a candidate-code failure.

## R2 correction

R2 inserts the candidate directory directly into `sys.path` inside the child
Python process before unittest discovery. It no longer relies on
`PYTHONPATH`.

Verification performed during the R2 build:

- candidate hashes unchanged: **True**
- model-source tests: **10 passed**
- embedded JavaScript blocks checked with Node: **1 passed**
- approved proposed live scope changed: **False**
- apply capability present: **False**
- live files modified: **False**
