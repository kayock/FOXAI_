FOXAI USB C4A — CUSTOM NODE AIRLOCK STATIC PREFLIGHT

This is the first Creative Studio expansion stage after the sealed C3 baseline.
It is read-only and does not import or execute any custom node.

C4A verifies the known-good C3L baseline, re-hashes the isolated runtime,
inventories ComfyUI/custom_nodes, performs AST/text security and dependency
analysis, detects local ComfyUI custom-node control capabilities, and produces
a proposed WebUI profile contract.

The WebUI can already use Safe Normal CPU with custom nodes OFF. After the
later controlled-import and integration gates, it can also offer an explicit
Approved Custom Nodes CPU profile while Safe Normal remains the default.

Run: RUN_USB_C4A_PREFLIGHT.bat
Upload the generated UPLOAD_THIS_C4A_REVIEW.zip.
