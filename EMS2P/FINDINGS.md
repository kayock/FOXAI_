# Extension Manager Phase 2 — Safe State Controls

## Exact scope

Only `core/foxai_web.py` is proposed for source installation. This package is
an exact preview and has no source installer.

## State workflow

1. The inventory remains a read-only GET.
2. Optional manifest-backed extensions display their effective state.
3. Enable, Disable, or Restore Default creates an exact before/after JSON diff.
4. The backend checks dependencies, enabled dependents, required/core locks,
   current state-file hash, manifest hash, and a 30-minute preview lifetime.
5. The operator must type the exact approval phrase.
6. Apply recomputes and verifies the preview digest before writing.
7. A verified backup is created first.
8. The state file is written atomically and read back.
9. A verified JSON receipt is mandatory.
10. Any post-write failure restores the exact prior bytes or prior absence.

## State-file behavior

`Config/extension_state.json` remains absent while all extensions follow their
manifest defaults. The first approved override creates it. Restore Default
removes an extension override. Restoring the final override removes the state
file and returns FOXAI to manifest-default mode.

## Dependency protection

- Required, reserved, core, system, and department items are blocked.
- An enabled extension cannot be disabled while an enabled dependent requires it.
- An extension cannot be enabled while a declared dependency is missing or disabled.
- Disabling does not terminate an already running external process.
- Disabled overrides block Extension Manager launch eligibility.

## Deliberate boundaries

Phase 2 does not install, update, remove, download, stop, or terminate software.
It records guarded state overrides for state-aware components and the Extension
Manager control surface.

## Candidate identities

- Baseline: `ecccf3b4a780d9de6ef2aa56522c6b65d06035c42a4a9050d72b95df530c40d0`
- Candidate: `5cffd8b594c5f91b983b391758fa295b151ca82c97ce8ddfcb085cacdd76a548`
- Exact diff: `86e65fec472f6b5701af24de7e683a81a8340726f1a6fc460feeb0f33a5bdb51`
