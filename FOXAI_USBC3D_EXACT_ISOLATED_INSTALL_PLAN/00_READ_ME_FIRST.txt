FOXAI USB C3D R1 — Exact Isolated Installation Plan and Approval Preflight

PURPOSE
C3D prepares and verifies the exact offline installation transaction that a
future C3E may perform. C3D does not create the target and does not install any
wheel.

C3D REQUIRES
- the exact reviewed C3B PLAN_OUTPUT already on the USB
- the exact successful C3C ACQUISITION_OUTPUT already on the USB
- all 96 accepted wheels in the C3C STAGING_WHEELHOUSE
- portable Python Z:\FOXAI\Runtime\Desktop\python\python.exe, version 3.14.6
- approved installer fallback C:\Python314\python.exe, CPython 3.14.6 x64 with pip 26.1.2
- Runtime\ComfyUI\site-packages must still be absent
- Runtime\ComfyUI\wheelhouse must still be absent

WHAT C3D CHECKS
- exact externally locked C3C evidence hashes
- exact reviewed C3B install order
- all 96 C3C wheel filenames, sizes, and SHA-256 hashes
- exact compressed and uncompressed payload size
- case-insensitive cross-wheel destination-file collisions
- wheel .data installation schemes
- .pth files and any executable import lines
- console/gui entry-point metadata
- approved installer-engine availability and required safety options
- portable pip is preferred; exact host pip is used only because portable pip is intentionally absent
- one exact local hash-locked pip dry-run containing all 96 packages
- free-space reserve, transaction boundary, activation, verification, and rollback

PIP DRY-RUN BOUNDARY
C3D first probes portable pip. Because the protected portable runtime intentionally
has no pip, it may fall back only to C:\Python314\python.exe after verifying exact
CPython 3.14.6 x64 identity, the interpreter hash, pip 26.1.2, and all required
control options. The host process is only an installer engine; it is not a runtime
dependency of the completed isolated target.

C3D invokes the selected pip engine only with:
- --dry-run
- --ignore-installed
- --no-deps
- --no-index
- --only-binary=:all:
- --require-hashes
- exact local file:// wheel references

Temporary pip files are redirected inside the C3D output folder and removed.
No target path is passed to pip during C3D.

FUTURE C3E DESIGN
After exact review and explicit operator approval, C3E should:
1. create one new timestamped staging target adjacent to the final target
2. re-hash all 96 wheels
3. re-verify the exact installer engine and install offline with --ignore-installed into that empty staging target using the C3D lock
4. verify exact inventory, dependencies, imports, CPU torch, torchvision ops,
   torchaudio, native binaries, and protected boundaries
5. commit only by same-volume rename to Runtime\ComfyUI\site-packages
6. make no launcher change and do not launch ComfyUI

PLACEMENT
Extract this complete folder directly inside:

  Z:\FOXAI\FOXAI_USBC3D_EXACT_ISOLATED_INSTALL_PLAN\

RUN
Double-click:

  RUN_USB_C3D_PLAN.bat

REVIEW UPLOAD
After it finishes, open the newest folder under PLAN_OUTPUT and upload:

  UPLOAD_THIS_C3D_REVIEW.zip

IMPORTANT
A successful C3D result is an approval package only. It does not authorize target
creation, package installation, launcher integration, or a ComfyUI launch.
