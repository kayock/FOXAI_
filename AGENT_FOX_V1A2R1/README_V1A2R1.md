# Agent Fox Technical Core V1A-2R1

Mission: `ENG-20260721-060224-2EA5A3`

This isolated refinement improves the V1A-2 static launcher and source-reference bridge.

## Improvements

- Separates launcher calls, Python interpreter invocations, Python scripts, URLs, OS-shell references, working directories, existence checks, diagnostics, file operations, and control flow.
- Resolves sequential `SET` assignments, `%~dp0`, and the common `FOR %%I ... %%~fI` FOXAI-root canonicalization pattern.
- Keeps `%ComSpec%` as an operating-system shell reference.
- Does not treat shell built-ins, comments, diagnostic text, or URLs as filesystem launch targets.
- Replaces the global 60,000-line ceiling with deterministic reference shards and explicit per-file coverage.
- Preserves the verified V1A-2 code, symbol, import, setting, reference, known-good, and source-hash evidence.

## Safety

The component uses only the Python standard library. It does not execute FOXAI source, launchers, interpreters, PowerShell, models, services, tasks, shortcuts, repairs, package installers, or network operations.

Generated evidence belongs to the Engineering mission output. Static evidence never proves runtime activity.
