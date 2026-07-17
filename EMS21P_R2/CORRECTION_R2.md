# EMS21P R2 — Portable Diff Verification

## Why R1 stopped

The R1 verifier called the external Unix-style `patch` executable while
checking the exact diff. That command is not guaranteed to exist on the
portable Windows FOXAI environment.

The verifier therefore stopped fail-closed before completing the live test.

The receipt confirms:

- state: `stopped_fail_closed`
- verified final state: `true`
- live files modified: `false`
- protected changes: none

## R2 correction

R2 replaces the external command with an internal pure-Python unified-diff
parser. It validates every context, deletion, addition, hunk count, and then
requires the reconstructed bytes to equal the approved candidate exactly.

No Git, GNU patch, WSL, or other external patch utility is required.

## Candidate remains unchanged

- Baseline SHA-256: `5cffd8b594c5f91b983b391758fa295b151ca82c97ce8ddfcb085cacdd76a548`
- Candidate SHA-256: `e0ec7d66bae40d3be67653f47f86cde310e50147924ee48778c4634f3c1d7525`
- Exact diff SHA-256: `01e9c29f794536092daefd706ae52afd73dd6baee31fb4860f1c6a8e25712e14`

The R1 fail-closed receipt is preserved at:

`approved/r1_failed_live_verify_receipt.json`

Receipt SHA-256:

`c473f6f1cba289a8636310a67f3c7b8120b32c9739a91d7059b1f7292e14f678`
