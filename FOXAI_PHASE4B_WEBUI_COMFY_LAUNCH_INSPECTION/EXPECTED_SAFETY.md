# Phase 4B Safety Contract

Allowed:

- Read and hash exact known WebUI, launcher, and ComfyUI files
- Perform bounded targeted source inspection under known FOXAI directories
- Parse `core\foxai_web.py` with Python AST
- Run two host-Python `import torch` probes
- Write timestamped reports only inside this package

Forbidden:

- Modify or patch live source
- Change launchers or shortcuts
- Launch FOXAI, WebUI, ComfyUI, browser, models, or services
- Install or download packages
- Use network access
- Recursively scan entire drives
- Treat inspection findings as approval to patch
