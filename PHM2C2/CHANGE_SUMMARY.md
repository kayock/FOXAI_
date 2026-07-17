# Portable Host Model Library Phase 2C2 — Exact Preview

## Exact proposed filesystem changes

### Modified

- `core/foxai_web.py`
  - adds backend-owned USB/HOST PC source identity;
  - adds per-machine folder approval and forget controls;
  - adds the approved `DESKTOP-G9ERN9B` host profile to the task selector;
  - records the exact source/path in the verified runtime receipt;
  - blocks unapproved paths and silent fallback;
  - keeps LAN/online source types disabled.

### Added

- `core/model_sources.py`
- `Config/model_sources.json`
- `tests/test_model_sources.py`

### Deleted

- None.

## Current-machine registry preview

- Machine: `DESKTOP-G9ERN9B`
- Display name: `Eric's Main Desktop`
- Approved host root: `C:\KayockModels`
- Preferred general model: `C:\KayockModels\General\Qwen3-30B-A3B\Qwen3-30B-A3B-Q4_K_M.gguf`
- Fallback policy: `ASK_OR_APPROVED_USB`
- Online/LAN sources: disabled

## Operator behavior

- Unknown computers may choose different folders.
- Choosing a folder does not register it.
- `Use This Session` keeps the answer in memory only.
- `Remember on This Computer` writes only the approved folder path and preferences.
- `Forget folder`, `Forget preferred model`, and `Forget computer profile` remove only registry references.
- Whole-drive scanning is rejected.
- No model starts automatically.
- An unavailable host profile does not silently select a USB model.
- Model files are never copied, moved, renamed, overwritten, or deleted.

## Future provider boundary

`LAN_OPENAI_COMPATIBLE` and `ONLINE_PROVIDER` are reserved schema types only.
They remain disabled and have no endpoint, external-send, or credential behavior
in this milestone.
