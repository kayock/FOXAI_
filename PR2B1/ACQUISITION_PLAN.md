# Portable Runtime Phase 2B1 — Core Wheelhouse Manifest

## Decision

FOXAI's small core runtime will be repaired separately from Desktop and
Creative Studio.

The core acquisition set is pinned to:

- psutil 7.2.2
- requests 2.34.2
- pycasbin 2.8.0
- watchdog 6.0.0
- pluggy 1.6.0

Their transitive dependencies will be resolved and pinned only after the
actual wheel METADATA has been downloaded into quarantine in Phase 2B2.

## Why the transitive versions are not guessed here

A dependency range is not a reproducible lock. Phase 2B2 must select one
compatible wheel for each dependency, inspect its METADATA, record its
filename and SHA-256, and prove it imports under bundled Python 3.14.6.

That avoids silently choosing whatever happens to be newest on acquisition
day and avoids accidentally accepting an sdist that would require a compiler.

## Wheel acceptance rules

A file is acceptable only when all of these are true:

1. It is a wheel, not a source archive.
2. It is `py3-none-any`, `win_amd64`, or a compatible CPython abi3 wheel.
3. Its SHA-256 matches the official source.
4. Its METADATA satisfies Python 3.14.6.
5. Its dependency graph is complete.
6. It is tested with Windows user-site packages disabled.
7. Nothing is installed into the live runtime during acquisition.

## Explicitly outside Phase 2B

- Pillow and CustomTkinter
- Tcl/Tk and the Desktop runtime
- Torch, NumPy, and ComfyUI
- drive-letter registry repair
- launcher replacement
- removal or cleanup of older launchers

## Expected next artifact

Phase 2B2 will create a quarantined wheelhouse package and an exact inventory.
It will still have no live install capability. Installation belongs to a
later guarded preview and apply milestone.
