FOXAI Portable Runtime Phase 2B2 — Quarantined Wheelhouse Acquisition

Extract PR2B2 directly inside the FOXAI root:

  Z:\FOXAI\PR2B2\

First run:

  VERIFY_PACKAGE.bat

Then run:

  ACQUIRE_CORE_WHEELHOUSE.bat

At the prompt type:

  ACQUIRE CORE WHEELHOUSE

The acquisition downloads twelve exact wheels from files.pythonhosted.org,
verifies each official SHA-256 and wheel metadata, checks the dependency
contract, extracts them into a quarantined staging tree, and runs imports
with Windows user-site packages disabled.

It does not install the wheels into the live runtime and does not modify a
launcher, source file, configuration, registry, Python path, model, or
security file.

Upload report.md and receipt.json from the timestamped folder printed after
the run:

  Reports\PortableRuntime\PR2B2_<timestamp>\
