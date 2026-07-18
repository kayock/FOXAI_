FOXAI USB C3C R3 — Exact Wheel Acquisition and Cryptographic Staging

R3 REPAIR STATUS
This package includes the reviewed R1 temporary-filename repair, the R2 wheel
RECORD directory-entry repair, and the R3 primary wheel metadata-selection
repair described in C3C_R3_REPAIR_NOTES.txt. None changes the approved manifest
or safety boundary.

PURPOSE
C3C acquires the exact 96 wheel payloads approved by the independently reviewed
C3B closure plan. Accepted wheels are stored only in this package's isolated:

  FOXAI_USBC3C_EXACT_WHEEL_ACQUISITION\STAGING_WHEELHOUSE

C3C DOES NOT INSTALL THEM.

EXACT CONTINUITY GATE
C3C requires the exact reviewed C3B output already on the USB. It verifies all
21 C3B evidence files against externally locked SHA-256 values, then verifies the
internal evidence manifest, receipt, classification, package count, byte total,
CSV/JSON agreement, filenames, URLs, hashes, and Python 3.14 wheel compatibility.

NETWORK BOUNDARY
C3C permits only:

  https://pypi.org/...                  exact JSON release metadata
  https://files.pythonhosted.org/...    exact reviewed wheel payload URLs

Redirects, alternate mirrors, query-string substitutions, source archives, and
unreviewed filenames are rejected.

ACCEPTANCE TESTS FOR EVERY WHEEL
A wheel enters STAGING_WHEELHOUSE only after all of these pass:
- exact PyPI release metadata is still available and not yanked
- exact URL, filename, byte size, upload time, Requires-Python, and SHA-256 match
- response is HTTP 200 with no redirect and exact Content-Length
- downloaded byte count and SHA-256 match exactly
- filename project, version, and tags match portable CPython 3.14 on Windows AMD64
- ZIP paths are safe and contain no encryption, symlinks, duplicates, or traversal
- exactly one top-level wheel dist-info directory provides the primary METADATA, WHEEL, and RECORD
- nested vendored dist-info files remain ordinary cryptographically verified payload files
- primary METADATA project and version match
- primary WHEEL tags agree with the filename
- every non-directory archive file member is represented and cryptographically verified by the primary RECORD
- explicit ZIP directory placeholders remain subject to path, encryption, symlink, and duplicate checks

RESUME BEHAVIOR
Accepted exact wheels remain in STAGING_WHEELHOUSE. A later rerun re-hashes and
re-validates them, then downloads only missing wheels. A mismatched or unexpected
existing file is never overwritten; C3C stops fail-closed.

NO-INSTALL SAFETY BOUNDARY
Running C3C does NOT:
- install, uninstall, upgrade, or downgrade any package
- run pip or uv installation commands
- download source distributions or build packages
- create or modify Runtime\ComfyUI\site-packages
- create or modify Runtime\ComfyUI\wheelhouse
- modify Desktop, Core, ComfyUI source, System, or launchers
- launch FOXAI, WebUI, Desktop, or ComfyUI

PLACEMENT
Extract the complete folder directly inside the verified FOXAI root:

  Z:\FOXAI\FOXAI_USBC3C_EXACT_WHEEL_ACQUISITION\

RUN
Double-click:

  RUN_USB_C3C_ACQUIRE.bat

REVIEW UPLOAD
After completion, open the newest folder under:

  ACQUISITION_OUTPUT\

Upload only:

  UPLOAD_THIS_C3C_REVIEW.zip

That compact review bundle contains evidence only. It excludes the approximately
0.669 GiB wheel payloads.

IMPORTANT
A successful C3C result authorizes review only. It does not authorize isolated
target creation, package installation, launcher changes, or a ComfyUI launch.
