# Portable Host Model Library Phase 2C2 — Exact Preview Report

- State: **stopped_fail_closed**
- Verified: **False**
- Apply capability: **False**
- Live files modified: **False**
- Model files modified: **False**
- Automatic model launch: **False**
- Network access: **False**
- Deleted files: **None**

## Exact proposed changes

- Modify `core/foxai_web.py`.
- Add `core/model_sources.py`.
- Add `Config/model_sources.json`.
- Add `tests/test_model_sources.py`.
- Delete nothing.

## Machine profile

- `DESKTOP-G9ERN9B` is preconfigured through the removable registry file.
- Approved root: `C:\KayockModels`.
- Other machines may approve different folders for one session or remember them locally.
- Forget controls remove registry references only.
- Whole-drive scanning and silent fallback remain prohibited.
- LAN and online providers remain disabled.

## Failure

- `RuntimeError: Candidate model-source tests failed: test_model_sources (unittest.loader._FailedTest.test_model_sources) ... ERROR

======================================================================
ERROR: test_model_sources (unittest.loader._FailedTest.test_model_sources)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_model_sources
Traceback (most recent call last):
  File "unittest\loader.py", line 426, in _find_test_path
  File "unittest\loader.py", line 367, in _get_module_from_name
  File "Z:\FOXAI\PHM2C2\candidate\tests\test_model_sources.py", line 9, in <module>
    from core.model_sources import ModelSourceError, ModelSourceRegistry
ModuleNotFoundError: No module named 'core'


----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
`
