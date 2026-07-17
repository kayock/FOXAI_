# EMS2P R2 Verifier Correction

## Why R1 stopped

R1 stopped fail-closed before candidate verification because the verifier
iterated `SNAPSHOT_INDEX.json.files`, which records the original uploaded ZIP
paths, and attempted to read a nonexistent `grounding_path` field.

The packaged grounding files are intentionally indexed by the
`selected_grounding` mapping.

## R2 correction

R2 reads and validates `selected_grounding` directly. It also validates that:

- the mapping exists and is non-empty;
- every packaged path is a string;
- every metadata record is an object;
- every SHA-256 is a 64-character string;
- every packaged grounding file matches its expected SHA-256.

## Unchanged candidate

The source candidate and exact diff are byte-for-byte unchanged:

- Baseline: `ecccf3b4a780d9de6ef2aa56522c6b65d06035c42a4a9050d72b95df530c40d0`
- Candidate: `5cffd8b594c5f91b983b391758fa295b151ca82c97ce8ddfcb085cacdd76a548`
- Exact diff: `86e65fec472f6b5701af24de7e683a81a8340726f1a6fc460feeb0f33a5bdb51`

The R1 live receipt is included at:

`approved/r1_failed_live_verify_receipt.json`

Receipt SHA-256:

`e3ca8b1416a7ef10c06991e7db189fd41906a8448b2355eba21738c9db22aa92`

R1 verified that no live files changed and no protected changes occurred.
