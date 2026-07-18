FOXAI USB C3E R2 — Exact Isolated Installation / Verified Resume

PURPOSE
C3E is the first authorized write stage for Creative Studio portability. R2
continues the exact approved C3E transaction after the prior run installed all
96 reviewed wheels successfully but stopped before commit during an overly
strict PE architecture inventory check.

OPERATOR APPROVAL
This package remains bound to the explicit approval:

  Proceed to USB C3E exact isolated installation under the reviewed C3D
  transaction and rollback boundaries.

CURRENT REVIEWED STATE
- The prior C3E run completed the exact offline pip installation successfully.
- One exact staging target is preserved:
  Runtime\ComfyUI\.C3E_site-packages_staging_20260718T020221Z
- Runtime\ComfyUI\site-packages does not exist.
- No launcher was changed and ComfyUI was not launched.
- The failure was caused by package-resource binaries that intentionally include
  x86 and ARM64 templates alongside the x64 runtime payload.

R2 VERIFIED RESUME
R2 does not reinstall when the exact preserved staging target and its exact prior
evidence verify. It binds the staging name to the matching INSTALL_OUTPUT run,
rehashes that run's evidence, confirms pip return code 0, wheelhouse integrity,
installer identity, no network, no launcher change, no commit, and unchanged
protected boundaries. Only then does it continue inventory and portable testing.

PE ARCHITECTURE POLICY
- Every .pyd import extension must be AMD64.
- Every unreviewed .dll or .exe must be AMD64.
- Exactly 12 reviewed cross-architecture package resources are allowed:
  six explicitly named PyOpenGL 32-bit legacy GLUT/GLE DLL resources and six
  Setuptools x86/ARM64 launcher-template resources.
- The exact path and PE machine value must match the sealed allowlist.
- PyOpenGL is now a required isolated import test under portable Python.
- Any additional non-AMD64 binary still fails closed.

AUTHORIZED TRANSACTION
1. Verify this R2 package and embedded approval.
2. Verify the exact reviewed C3D lock and all 96 C3C wheel hashes.
3. Verify host CPython 3.14.6 / pip 26.1.2 and protected runtime boundaries.
4. Verify and resume the one exact preserved staging target without reinstalling.
5. Build a complete installed-file hash inventory and classify every PE binary.
6. Run portable Python with -I -B -S to verify exact distributions, dependencies,
   RECORD hashes, Setuptools .pth activation, critical imports including PyOpenGL,
   CPU torch, torchvision compiled operations, and torchaudio.
7. Commit only after every pre-commit gate passes, using one same-volume rename to
   Runtime\ComfyUI\site-packages.
8. Repeat inventory and portable verification after commit.

FAIL-CLOSED BEHAVIOR
- Any resume-evidence mismatch stops without modifying the staging target.
- Any unreviewed non-AMD64 binary stops before commit.
- Any portable verification failure preserves staging for review.
- A post-commit failure preserves the isolated final target disabled from all
  launchers.
- C3E never deletes, uninstalls, merges, overwrites, or automatically rolls back.

WINDOW BEHAVIOR
RUN_USB_C3E_INSTALL.bat now pauses at the end on both success and failure so the
result cannot vanish before it is read.

FORBIDDEN
- No network access.
- No Runtime\ComfyUI\wheelhouse creation.
- No writes to Desktop, Core, host Python, ComfyUI source, models, input, output,
  custom_nodes, System, or launchers.
- No FOXAI, WebUI, Desktop, or ComfyUI launch.

PLACEMENT
Extract the complete folder directly inside Z:\FOXAI\ and allow replacement
only inside FOXAI_USBC3E_EXACT_ISOLATED_INSTALL. Preserve INSTALL_OUTPUT and the
existing Runtime\ComfyUI\.C3E_site-packages_staging_* directory.

Run:
  Z:\FOXAI\FOXAI_USBC3E_EXACT_ISOLATED_INSTALL\RUN_USB_C3E_INSTALL.bat

REVIEW
Upload UPLOAD_THIS_C3E_REVIEW.zip from the newest INSTALL_OUTPUT folder before
any launcher integration or ComfyUI launch.
