FOXAI USB Commissioning Phase 1 — Guarded Apply

Operator approval received:
  APPROVE USB COMMISSIONING PHASE 1 APPLY

Install location:
  Extract the USBC1_APPLY folder directly into Z:\FOXAI\

Run:
  USBC1_APPLY\APPLY_USB_COMMISSIONING_PHASE1.bat

The local apply still asks for the exact approval phrase to prevent an
accidental double-click.

Exact live additions:
  COMMISSION_FOXAI_USB.bat
  System\Commissioning\commission_usb.py
  00_START_HERE\USB_COMMISSIONING_GUIDE.md

Existing files modified: none
Deleted files during apply: none
Automatic install, repair, download, service start, or model launch: none

The apply verifies the R4 exact-preview receipt, all locked live baselines,
candidate hashes, post-apply no-write commissioning, and all five Boundary
Watch tests. Any partial new-file write is automatically rolled back.

A separate guarded rollback is included but never runs automatically. It
requires this exact local phrase:
  ROLLBACK USB COMMISSIONING PHASE 1
