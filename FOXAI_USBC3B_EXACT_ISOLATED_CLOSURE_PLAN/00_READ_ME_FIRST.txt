FOXAI USB C3B — Exact Isolated Dependency Closure Plan

PURPOSE
C3B converts the reviewed C3A evidence into an exact, no-install dependency plan
for the preferred isolated ComfyUI target:

  Z:\FOXAI\Runtime\ComfyUI\site-packages

C3B DOES NOT CREATE OR POPULATE THAT TARGET.

CONTINUITY GATE
C3B requires the exact reviewed C3A output already on the USB. It verifies the
reviewed receipt, classification, evidence-integrity manifest, and critical file
SHA-256 values before resolving anything.

NETWORK BOUNDARY
C3B requires internet access for package metadata. It allows only:

  https://pypi.org/... JSON metadata

It records selected HTTPS wheel URLs hosted at files.pythonhosted.org, but it does
not request or download wheel payloads.

NO-ACTION SAFETY BOUNDARY
Running C3B does NOT:
- install, uninstall, upgrade, or downgrade any package
- run pip or uv installation commands
- download wheel payloads or source archives
- copy torch or any dependency
- create Runtime\ComfyUI\site-packages
- edit Desktop, Core, ComfyUI, System, or launcher files
- launch FOXAI, WebUI, Desktop, or ComfyUI

The only writes are NEW planning evidence inside:

  PLAN_OUTPUT\<UTC timestamp>\

PLACEMENT
Extract the complete folder directly inside the verified FOXAI root:

  Z:\FOXAI\FOXAI_USBC3B_EXACT_ISOLATED_CLOSURE_PLAN\

RUN
Double-click:

  RUN_USB_C3B_PLAN.bat

Then upload the newest timestamped folder under PLAN_OUTPUT for exact review.

WHAT C3B PRODUCES
- exact direct pins based on the C3A-verified working host versions
- recursively resolved transitive dependency closure
- exact Windows CPython 3.14 wheel filename for every package
- exact SHA-256, byte size, source URL, and compatibility tag
- independent dependency-edge verification
- requirements file with one approved hash per selected wheel
- CSV wheel acquisition manifest
- advisory dependency order
- exact compressed size and conservative future space reservation
- protected write boundaries and rollback concept
- full metadata request log and evidence integrity manifest

IMPORTANT
A successful C3B result is a plan for review only. It does not authorize wheel
acquisition, target creation, package installation, launcher changes, or a
ComfyUI launch.
