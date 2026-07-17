# Phase 2B3 R1 Failure Diagnosis

The first guarded apply stopped before live changes because Windows translated
the generated runtime manifest from LF to CRLF while `Path.write_text()` wrote
the file.

- CRLF file hash: `8827ce801b082732d20c65ea2b2afa88dbcebd97cc95d0cad470c649bd3d35bb`
- Same bytes normalized to LF: `bca61a55178063e5305ac8b5d8ba951f22fdb65d8b29ced443d9fff685668283`
- Exact expected preview hash: `bca61a55178063e5305ac8b5d8ba951f22fdb65d8b29ced443d9fff685668283`
- Live changes started: **False**
- Rollback required: **False**
- Approved live scope changed: **False**

R2 writes the deterministic JSON payload using `write_bytes()` instead.
That preserves the exact LF byte sequence already verified in the preview.
