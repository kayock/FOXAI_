# Project Forge Preview 8 architecture

## Trust boundary

`workspace/project/` is the disposable Git copy. OpenCode never runs there.

`workspace/agent_view_round_N/` is the OpenCode worktree. It contains tests, small support files, the complete symbol map, selected Code Slicer V1 slices, and an empty `PROPOSED.patch`. It does **not** contain `dirty_python_lab.py`.

## Patch path

OpenCode writes a unified diff only. Project Forge independently validates allowed targets, protected-test hashes, traversal, binary content, and `git apply --check`. Only then may the patch be applied to the disposable project.

## Repair path

Compile/test failures are recorded as bounded failure context. The exact slicer reruns against the current disposable target, selects symbols containing reported line numbers or names, and creates a new isolated agent view for the next round.

## Original-source stop gate

The build receipt always records `stopped_before_original_apply: true`. No original-apply implementation exists in this preview.
