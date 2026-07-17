# FOXAI Repair & Optimization Preflight

## Overall state: **READY_WITH_NOTES**

- Critical failures: **0**
- Notes: **8**
- Elapsed seconds: **5.82**
- Repairs performed: **False**
- Installs/downloads performed: **False**
- FOXAI/ComfyUI launched: **False**

## Portable runtime

- Exact Desktop manifest passed: **True**
- Files checked: **3517**
- Functional USB runtime contract passed: **True**

## Machine and storage

- FOXAI root: `Z:\FOXAI` (**USB**)
- Controller: `Z:\FOXAI\Runtime\Desktop\python\python.exe` (**USB**)
- Free space: **803705192448 bytes**
- Filesystem: **exFAT**

## Offline wheelhouse

- Exists: **True**
- Wheels: **24**
- Direct requirements covered: **5 / 43**
- Invalid wheels: **0**

## Repair tooling

- git: **AVAILABLE** (HOST_PC)
- ripgrep: **MISSING** (NOT_FOUND)
- gitleaks: **MISSING** (NOT_FOUND)
- semgrep: **MISSING** (NOT_FOUND)
- keepassxc: **MISSING** (NOT_FOUND)
- sandboxie: **MISSING** (NOT_FOUND)

## Notes

- **wheelhouse_direct_requirement_gaps** — 38 direct requirement(s) lack an obvious matching wheel.
- **host_only_tool_git** — git is available only from HOST PC at C:\Program Files\Git\cmd\git.exe.
- **recommended_tool_ripgrep** — ripgrep is not available from USB or HOST PC.
- **recommended_tool_gitleaks** — gitleaks is not available from USB or HOST PC.
- **recommended_tool_semgrep** — semgrep is not available from USB or HOST PC.
- **recommended_module_keyring** — Python module keyring is not available in the USB runtime.
- **recommended_module_tree_sitter** — Python module tree_sitter is not available in the USB runtime.
- **recommended_module_pytest** — Python module pytest is not available in the USB runtime.

## Safety receipt

- No live source or configuration file was modified.
- No file was deleted, overwritten, repaired, installed, or downloaded.
- No entire-drive recursive scan was performed.
- Child processes were limited to local import/version probes.
- Dependencies are labeled USB, HOST_PC, or NOT_FOUND.

Upload this complete `UPLOAD_THIS` folder before any repair plan is created.
