FOXAI Portable Runtime Phase 2A — Read-Only Probe

Extract the PRP2A folder directly inside the FOXAI root:

  Z:\FOXAI\PRP2A\

First run:

  VERIFY_PACKAGE.bat

Then run:

  RUN_PORTABLE_RUNTIME_PROBE.bat

The probe inventories:
- embedded Python, .venv, and possible ComfyUI runtimes;
- normal imports versus user-site-disabled imports;
- package versions and exact origins;
- launcher runtime choices;
- requirements files;
- source imports;
- hard-coded fleet paths.

It does not install, repair, launch, rewrite, delete, or move anything.
Its only runtime writes are a timestamped report.md and receipt.json under:

  Reports\PortableRuntimeProbe\PRP2A_<timestamp>\
