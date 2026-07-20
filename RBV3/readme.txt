REPAIR BAY V3.0 — SYSTEM BASELINE AND CHANGE COMPARISON

Mission: ENG-20260720-201421-7CA510

Adds Capture Baseline, Capture After Snapshot, Compare Snapshots, explicit known-good selection, historical preservation, Change Sessions, neutral evidence-backed reports, and local HTML/Markdown/JSON exports.

Read-only inventory covers Windows, CPU, memory, disks, major processes, services, startup entries, scheduled tasks, listeners, applications, optional features, runtimes, browsers, GPU drivers, and audio drivers when Windows exposes them locally.

Excluded: passwords, environment variables, browser/document contents, tokens, clipboard data, and full command-line arguments.

New data stays under:
  Z:\FOXAI\Reports\RepairBay\SystemBaseline

Changed files:
- core/foxai_web.py
- core/repair_bay_baseline.py
- core/VERIFY_REPAIR_BAY_V3.py

Plan SHA-256:
731ff83ad12a3e2b2c2fc7b2e1b2da30045cc058a1cc5a5519872f694e18d40f

Extract RBV3 directly into Z:\FOXAI, then preview:
/engineer workshop preview "Z:\FOXAI\RBV3\plan.json"
