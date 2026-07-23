AGENT FOX TECHNICAL CORE V1A-0
Mission: ENG-20260721-042128-CF3008

PURPOSE
This package binds one read-only live-baseline audit payload to the staged Engineering Workshop mission.

EXTRACT EXACTLY HERE
Z:\FOXAI\AGENT_FOX_V1A0

RESULTING PLAN PATH
Z:\FOXAI\AGENT_FOX_V1A0\PLAN.json

PACKAGE LAYOUT
PLAN.json
V1A0_READ_ONLY_AUDIT.py
REPOSITORY_REFERENCE.json
PACKAGE_BUILD_RECEIPT.json
PACKAGE_MANIFEST.json
README_FIRST.txt

SAFETY BOUNDARY
- PLAN.json targets exactly one new file in the Engineering mission workspace.
- No existing FOXAI source file is targeted.
- No launcher, runtime, model, database, archive, personal file, or existing receipt is modified.
- The audit executes no FOXAI source or launcher.
- Network use, package installation, elevation, deletion, and renaming are prohibited.
- Audit outputs are limited to:
  Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-042128-CF3008_V1A0_AUDIT
- Output ceiling: 128 MiB.
- The Engineer-generated preview hash is the authorization boundary.
- This package's preparation hashes are not implementation authority.
- The final Engineering receipt is authoritative.

PREVIEW COMMAND
/engineer workshop preview "Z:\FOXAI\AGENT_FOX_V1A0\PLAN.json"
