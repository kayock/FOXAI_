FOXAI USB C3F — CONTROLLED ACTIVATION / LAUNCHER INTEGRATION PREFLIGHT

This package is NO-LAUNCH and NO-CHANGE.

It will:
- Bind to the exact accepted C3E result from 20260718T023211Z.
- Reverify all 39,046 files and the exact 1,520,221,467-byte committed target.
- Run portable Python 3.14.6 with -I -B -S.
- Activate only Runtime\ComfyUI\site-packages.
- Compile ComfyUI Python source without writing bytecode.
- Import critical ComfyUI/dependency modules in CPU mode.
- Block network connections, server binds, subprocess launches, and os.startfile.
- Inventory every current ComfyUI launch surface.
- Copy relevant source files only into timestamped evidence snapshots.
- Generate a proposed C3G integration change set and exact small diffs where safe.

It will NOT:
- Edit a launcher or source file.
- Modify Runtime\ComfyUI\site-packages.
- Install, uninstall, download, or copy packages.
- Launch ComfyUI, FOXAI, WebUI, or Desktop.
- Bind port 8188 or access the network.

Run:
  RUN_USB_C3F_PREFLIGHT.bat

Then upload:
  PREFLIGHT_OUTPUT\<newest-run>\UPLOAD_THIS_C3F_REVIEW.zip

Do not launch ComfyUI after C3F. C3G integration requires fresh operator approval,
and the first controlled ComfyUI start remains a later gate.

C3F R2: Mirrors the exact local ComfyUI main.py CPU argument initialization order before importing CUDA-sensitive modules. Still no launch and no changes.
