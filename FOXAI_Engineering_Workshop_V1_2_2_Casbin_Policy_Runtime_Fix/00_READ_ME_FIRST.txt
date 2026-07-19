FOXAI Engineering Workshop V1.2.2 — Casbin Policy Runtime Fix

This replaces the failed V1.2.1 installer.

Diagnosis:
V1.2.1 correctly targeted the policy file, but validated through
Runtime\Desktop\python\python.exe. FOXAI WebUI actually runs through
env\python\python.exe, which is the runtime containing the active Casbin setup.
The mismatch caused a false validation failure, and V1.2.1 restored the original
policy automatically.

This installer targets only:
Config\engineering_airlock_policy.csv

It adds:
p, operator, engineering_airlock, preview, allow

Direct use:
Z:\FOXAI\Runtime\Desktop\python\python.exe INSTALL_ENGINEERING_WORKSHOP_V1_2_2_POLICY.py

Apply:
Z:\FOXAI\Runtime\Desktop\python\python.exe INSTALL_ENGINEERING_WORKSHOP_V1_2_2_POLICY.py --approve

Validation is performed through:
Z:\FOXAI\env\python\python.exe

Restart FOXAI WebUI after an installed_verified result.
