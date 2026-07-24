PROJECT FORGE — OPENCODE PILOT 0.1.0
========================================

PURPOSE
- Test a native Windows coding-agent harness without pip or venv.
- Use the Qwen model currently served at http://127.0.0.1:8080/v1.
- Repair only a disposable Git project.
- Prove tests, rollback, and restore.
- Audit host-profile writes before calling OpenCode portable.

INSTALL
1. Extract this ProjectForgeOpenCodePilot folder under:
   Z:\FOXAI\_LAB\ProjectForgeOpenCodePilot
2. Double-click START_PROJECT_FORGE_OPENCODE_PILOT.bat
3. Click INSTALL NATIVE OPENCODE.
   This downloads the official Windows x64 release from GitHub into Runtime only
   and verifies its Windows Authenticode signature when PowerShell is available.
4. Start Qwen3-Coder on port 8080.
5. Click RUN REPAIR & ROLLBACK PILOT.

IMPORTANT
- The first custom-provider run may need internet access once so OpenCode can obtain
  its OpenAI-compatible provider package. The pilot records where state is written.
- Live FOXAI is never selected or modified.
- A functional pass with host-profile writes is not yet a portability pass.
