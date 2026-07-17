# Extension Manager Phase 2.1 — Operator Clarity

## Proposed live source change

- `core/foxai_web.py` only

## User-facing improvements

- Quick Cheat Sheet and Operator Manual inside Extension Manager.
- Compact action legend for read-only, preview-only, and approval-required actions.
- Advanced Manifest Tools collapsed by default to reduce Engineering clutter.
- Protected system/core/department manifest records display `Protected` instead of `Disable`.
- Optional legacy records display `Preview Enable` or `Preview Disable`.
- State override path now says `EXISTS` or `NOT CREATED` instead of implying existence.
- Manifest-record totals are clearly separated from the 44-component inventory totals.

## Security contract

- Guarded state preview/apply functions are byte-for-byte unchanged.
- No install, removal, update, or download support is added.
- No extension state is changed by this preview.
- No runtime state files or folders are created.
- No delete operation is proposed.

Baseline SHA-256: `5cffd8b594c5f91b983b391758fa295b151ca82c97ce8ddfcb085cacdd76a548`
Candidate SHA-256: `e0ec7d66bae40d3be67653f47f86cde310e50147924ee48778c4634f3c1d7525`
Exact diff SHA-256: `01e9c29f794536092daefd706ae52afd73dd6baee31fb4860f1c6a8e25712e14`
