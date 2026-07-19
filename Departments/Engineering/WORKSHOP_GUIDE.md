# Engineering Workshop V1

Engineering Workshop V1 adds a controlled implementation worker to the existing
Engineering Department. It uses only the Python standard library and does not
install packages or use the network.

## What V1 can do

- Route search, diagnosis, planning, implementation, and repair missions separately.
- Preserve an active mission so **continue** resumes it.
- Discover live source while excluding runtime documentation, quarantine, snapshots,
  backups, caches, archives, wheelhouses, and generated receipts.
- Preview an exact UTF-8 text change plan as a unified diff.
- Require approval of the exact plan SHA-256 before changing anything.
- Snapshot every targeted file before applying the plan.
- Apply only `replace_text` and `write_file` operations atomically.
- Run explicitly listed local validation commands without a shell.
- Restore the snapshot automatically if validation fails.
- Produce JSON receipts from real file hashes and real command output.

## What V1 deliberately cannot do

- Delete or rename files.
- Modify binary files.
- Execute shell command strings, PowerShell scripts, or chained commands.
- Search the network or install packages.
- Invent command output or claim a change without a receipt.
- Generate a code patch from natural language by itself.

Agent Fox or a future Project Forge planner creates an exact plan. Workshop V1 is
the trusted worker that previews, snapshots, applies, validates, rolls back, and
records that plan.

## Safe workflow

From `Z:\FOXAI`:

```bat
Departments\Engineering\RUN_ENGINEERING_WORKSHOP.bat begin study-v16 "Study V1.6" "Implement the approved Study V1.6 mission. Proceed with targeted source changes." --project-root "Z:\FOXAI\path\to\live\study"

Departments\Engineering\RUN_ENGINEERING_WORKSHOP.bat locate study-v16 study bibliotheca launcher

Departments\Engineering\RUN_ENGINEERING_WORKSHOP.bat preview "Z:\FOXAI\Plans\study-v16.json"
```

Review the generated `.diff`. The preview returns the exact plan SHA-256.

```bat
Departments\Engineering\RUN_ENGINEERING_WORKSHOP.bat apply "Z:\FOXAI\Plans\study-v16.json" --approve EXACT_SHA256_FROM_PREVIEW
```

Receipts, mission state, snapshots, and previews are stored under:

`Z:\FOXAI\System\EngineeringWorkshop\`

## Integration boundary

This ZIP supplies the working backend foundation and CLI. The current Engineer
WebUI is still labeled read-only. Connecting buttons and Mission Director calls to
this backend requires the live FOXAI server/controller source, which was not part
of the uploaded Engineering department folder.
