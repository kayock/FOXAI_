MICR1P — Mission Image Continuity + Payload Leakage Repair

This package is an exact preview only. It cannot apply or install anything.

Extract the complete MICR1P folder directly to:

    Z:\FOXAI\MICR1P\

Run:

    VERIFY_PREVIEW.bat

Expected result:

    State: exact_preview_verified
    Verified: True
    Live files modified: False
    Apply capability present: False

Proposed live scope:

    core\foxai_web.py

Explicitly unchanged:

    core\server.py

The preview also performs a read-only scan for image payload strings already
persisted in likely Logs, Reports, Projects, or Mission Archive folders. It
does not clean or rewrite any file.

Nothing in this package authorizes an apply.
