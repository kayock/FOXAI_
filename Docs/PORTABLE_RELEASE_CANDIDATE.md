# Portable Release Candidate

v1.0.0-rc.1 adds a single Foundry command for preparing a portable release candidate.

## Run

```bat
Foundryuild_portable_rc.bat
```

## It runs

1. Dynamic module registry build
2. AI asset scanner
3. Foundry release check
4. Release packager

## Output

```text
Foundry/Reports/portable_rc_report.json
Foundry/Reports/PORTABLE_RC_REPORT.md
Foundry/Releases/KayocktheOS_*.zip
```
