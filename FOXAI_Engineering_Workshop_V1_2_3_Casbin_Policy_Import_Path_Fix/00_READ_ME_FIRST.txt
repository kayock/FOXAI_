FOXAI Engineering Workshop V1.2.3 — Casbin Policy Import-Path Fix

The earlier policy installers restored the original policy after validation
failed. No policy change remained installed.

V1.2.3 reproduces the real WebUI startup context:
1. Uses Z:\FOXAI\env\python\python.exe.
2. Inserts Z:\FOXAI into sys.path, just as core\foxai_web.py does.
3. Imports core.security_containment.
4. Clears the cached Casbin enforcer.
5. Verifies operator / engineering_airlock / preview is allowed through Casbin.

Only this file is targeted:
Config\engineering_airlock_policy.csv

Only this line is added:
p, operator, engineering_airlock, preview, allow

Preview:
Z:\FOXAI\Runtime\Desktop\python\python.exe INSTALL_ENGINEERING_WORKSHOP_V1_2_3_POLICY.py

Apply:
Z:\FOXAI\Runtime\Desktop\python\python.exe INSTALL_ENGINEERING_WORKSHOP_V1_2_3_POLICY.py --approve

Restart FOXAI WebUI after installed_verified.
