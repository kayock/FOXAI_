# Agent Fox Technical Core V1A-3B

V1A-3B builds a static, evidence-backed map of effective Python import contexts and dependency-resolution candidates.

It reads the verified V1A-2R2 launcher/source evidence and V1A-3A-R1 runtime/package evidence. It does not execute FOXAI source, launchers, Python runtimes, `pythonw.exe`, packages, models, PowerShell, services, or repair actions.

The bridge creates one context for every statically identified Python invocation, while keeping called launchers and multi-stage launchers separate. Bare commands such as `python` remain unresolved command aliases. `pythonw.exe` is represented only as a static sibling candidate of the observed Desktop Python runtime.

Provider existence and path order are evidence candidates. They do not prove an import succeeded or that a dependency collision is active.

The generated query interface reads generated JSON indexes only:

- `resolve-import`
- `explain-import-context`
- `show-package-provider`
- `compare-runtime-versions`
