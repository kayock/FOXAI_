# FOXAI Model Profile Selector + Verified Runtime — Phase 3 Exact Preview

- State: **combined_exact_preview_ready**
- Verified: **True**
- Live files modified: **False**
- Candidate included: **True**
- Apply capability present: **False**
- Proposed files: **core/foxai_web.py, core/server.py**
- WebUI candidate SHA-256: `b94ac8e3b3a01b86cf34a509a64178e5efe047f38ac48e8ab5d08306ddf7ea48`
- Server candidate SHA-256: `9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07`

## Combined behavior

The five profile cards remain pending-selection-only. Clicking a card
does not call an API or affect the running engine. Starting remains an
explicit operator button action.

A backend-owned allowlist validates each profile/model pairing and
selects its runtime settings. Browser-supplied arbitrary engine flags
are not accepted.

### Profile settings

- ⚡ Fast Text: reasoning off, budget 0
- ⚖️ Balanced Text: reasoning off, budget 0
- 🎭 Creative Text: reasoning off, budget 0
- 👁️ Fast Vision: current engine reasoning behavior
- 🔎 Quality Vision: current engine reasoning behavior

The raw-GGUF fallback remains available.

Profile launches track model, context, threads, reasoning mode, and
reasoning budget. Different or unverifiable profile settings conflict
fail-closed instead of silently attaching.

## Verification passed

- Exact live, candidate, and diff hashes
- Exact diff-to-candidate reconstruction
- Baseline and candidate Python compilation
- Complete embedded JavaScript node checks
- Selection/no-API and explicit-start payload harness
- Backend profile allowlist harness
- Shared runtime reasoning/state/compatibility harness
- Boundary Watch tests
- Locked Chat Timing, archive, receipt, navigation, accordion, and Sentry markers
- Live source, configuration, and security-log immutability

No apply mechanism is present.
