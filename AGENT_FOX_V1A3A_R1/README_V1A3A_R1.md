# Agent Fox Technical Core V1A-3A-R1

This isolated correction adopts the already-generated and hash-verified V1A-3A Python runtime evidence without launching any interpreter probes again.

It corrects one validator assumption: `sys.flags.no_site` may be `0` when a verified version-specific `._pth` file explicitly contains the noncomment line `import site`. The runtime remains separately checked for isolated mode, ignored environment variables, disabled user site, and disabled bytecode writing.

It also records `Z:\FOXAI\.venv` as `host_base_dependent` when the adopted probe and `pyvenv.cfg` point to a base installation outside `Z:\FOXAI`. This is portability evidence, not proof of an active package conflict.

The component performs hash-only checks of the four recorded interpreters, their recorded control files, and the six known-good protected candidates. It does not execute FOXAI source, launchers, Python child probes, `pythonw.exe`, pip, models, Llama, ComfyUI, PowerShell, services, or scheduled tasks.
