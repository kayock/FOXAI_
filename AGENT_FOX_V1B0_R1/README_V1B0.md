# Agent Fox Technical Core V1B-0

Mission: `ENG-20260722-043649-699E75`

This component creates a bounded, read-only baseline of the current Windows host and the active `Z:\FOXAI` workspace. It gathers first-party local evidence only. It does not decide that the PC is healthy, unhealthy, infected, damaged, optimized, or broken.

## Boundaries

- Queries only `C:`, `Z:`, and `S:` for drive capacity when present.
- Does not access rollback drive `K:`.
- Does not install, remove, tune, repair, stop, start, or reconfigure anything.
- Does not inspect personal documents, browser history, credentials, command-line arguments, environment values, MAC addresses, product keys, or hardware serials.
- Does not import live FOXAI modules or launch FOXAI, models, ComfyUI, or a GUI.
- Uses bounded read-only Windows collectors and isolated Python identity probes.

## Evidence

The collector writes exactly eight LF-only JSON files to the mission evidence directory. Facts and observations are separated. Attention items are evidence-linked observations, not diagnoses or repair instructions.

## Commands

```text
python pc_foxai_baseline_v1.py self-test
python pc_foxai_baseline_v1.py collect --mission-id ENG-20260722-043649-699E75 --output-dir <mission-output-directory>
```
