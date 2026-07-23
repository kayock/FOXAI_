AGENT FOX TECHNICAL CORE V1A-3H-R1
Mission: ENG-20260722-012832-1285F2

1. Extract this complete folder directly into Z:\FOXAI.
2. Preview:
   /engineer workshop preview "Z:\FOXAI\AGENT_FOX_V1A3H_R1\PLAN.json"
3. Review the four changed paths and use only the exact hashed Apply command returned by Engineer.

This repair does not broaden V1A-3H. It corrects the path separator that caused Apply to look for
files/core\foxai_web.py. The plan now uses core/foxai_web.py so the Workshop snapshot archive uses
the canonical member files/core/foxai_web.py. Validation 1 verifies that member contains the exact
pre-change 2351757-byte WebUI source with SHA-256 e4e9fd62e6c4736a18781c6b17184441e8852412867cc95dbca94e570921ba77.

No Desktop file, model, runtime, database, launcher, or K: rollback drive is targeted.
