# USB C3 Safety Contract

Allowed:

- Read and hash relevant FOXAI and ComfyUI files
- Probe Python interpreters in isolated subprocesses
- Import torch only to report version, origin, and CPU/CUDA capability
- Measure folder sizes and free disk space
- Copy small relevant source files into timestamped preflight output
- Write reports only inside this package's `PREFLIGHT_OUTPUT` directory

Forbidden:

- Modify live FOXAI or ComfyUI files
- Install/download packages
- Create missing ComfyUI folders
- Copy torch or other runtime packages
- Change launchers, shortcuts, configuration, models, or source
- Launch FOXAI, WebUI, Desktop, ComfyUI, browser, models, or services
- Use network access
