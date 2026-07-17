# FOXAI Portable Desktop Runtime Phase 3D-A

## Approved Add-Only Runtime Apply

This package was created only after receiving the exact operator approval:

```text
APPROVE PDR3D 7123A2A06AA7
```

Approved plan ID:

```text
7123a2a06aa7fa0451151dc0689bb2730e11b2ff7c1d6edc18fe438ab0210424
```

## Exact effect

It adds 3,520 new files totaling 145,156,301 bytes:

```text
Runtime\Desktop\python\**
Runtime\Desktop\site-packages\**
Runtime\Desktop\DESKTOP_RUNTIME_MANIFEST.json
System\PortableRuntime\verify_desktop_runtime.py
START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat
```

It does not overwrite or modify any existing file. It does not change the two USB-root shortcuts, existing launchers, source, Runtime/Core, Config, ComfyUI, Models, or protected baselines.

## Safety sequence

1. Validate the approved plan ID and exact scope.
2. Require the approval phrase again locally.
3. Revalidate protected files and shortcuts.
4. Confirm all 3,520 destinations are still absent.
5. Verify every approved source hash and size.
6. Copy all files into temporary staging and verify them again.
7. Recheck protected state and destinations.
8. Commit add-only files, with the diagnostic launcher committed last.
9. Verify every live addition and all protected state.
10. Write an apply receipt.

If a commit fails, rollback removes only files created by this run whose hashes still match the approved plan. It never deletes a preexisting file.

## Run

1. Extract this entire folder inside `Z:\FOXAI`.
2. Run `RUN_PHASE3D_APPLY.bat`.
3. Type the exact approval phrase when prompted.
4. The copy may take roughly 1–10 minutes on USB. Progress is displayed.
5. Zip and upload only the newest:

```text
APPLY_OUTPUT\<timestamp>\UPLOAD_THIS
```

Do not run `START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat` until the apply receipt has been reviewed.
