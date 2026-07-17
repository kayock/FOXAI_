# Portable Host Model Library Phase 2C3 R2 — Exact Test Plan

## Live read-only checks

1. Verify all Phase 2C2 and protected security hashes.
2. Verify the current machine is `DESKTOP-G9ERN9B`.
3. Verify the approved host model is present, readable, and registered as
   `HOST_PC`.
4. Verify USB models remain independently available.
5. Verify no-silent-switch, never-modify-models, and online-disabled policies.
6. Record model size and modified time before and after validation without
   hashing the 17+ GiB GGUF.

## Isolated temporary scenarios

The following use tiny fixture models and a temporary copied registry only:

1. Unknown machine starts with USB models and no inherited host paths.
2. Session-only folder approval does not alter registry bytes.
3. A fresh registry instance forgets session-only approval.
4. Remembered approval survives a fresh registry instance.
5. A folder path containing spaces works.
6. Missing remembered folder is reported unavailable.
7. A missing preferred host model does not resolve to a USB model.
8. Forget preferred model removes only the preference.
9. Forget folder removes only FOXAI's reference.
10. Forget computer removes only the machine profile.
11. Whole-drive approval is rejected.
12. LAN and online providers remain disabled.
13. External-send consent and credential-reference-only flags remain present.

## Clarity finding

The current WebUI wording `ONLINE • HOST PC` will be inspected but not
changed. Phase 2C3 R2 should classify it for a later exact preview:

- Engine: RUNNING
- Model source: HOST PC
- Network use: NONE

## Pass condition

All live checks and all isolated scenarios pass, model metadata is unchanged,
and no live registry, model, source, launcher, model process, or network state
changes.
