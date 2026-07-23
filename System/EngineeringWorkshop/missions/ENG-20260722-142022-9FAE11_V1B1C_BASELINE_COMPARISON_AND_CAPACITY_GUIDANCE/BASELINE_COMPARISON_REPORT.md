# FOXAI Resource Baseline Comparison

Source missions: `ENG-20260722-062243-69C555` and `ENG-20260722-140518-F13169`.

This report compares two verified point-in-time evidence sets. It performs no new live scan and gives bounded observations rather than a diagnosis or tuning recommendation.

## Minimal versus normal loaded

| Measurement | Minimal load | Normal loaded | Loaded − minimal |
|---|---:|---:|---:|
| Memory load | 17.47% | 83.64% | 66.17 points |
| Physical RAM in use | 8.95 GB | 42.83 GB | 33.89 GB |
| Available physical RAM | 42.27 GB | 8.38 GB | -33.89 GB |
| Committed memory | 14.06 GB | 33.15 GB | 19.09 GB |
| Current page-file use | 773 MiB | 693 MiB | -80 MiB |
| Process count | 276 | 288 | +12 |
| FOXAI workspace process count | 2 | 5 | +3 |

The normal-loaded capture used 33.89 GB more physical RAM than the minimal-load capture. Available physical RAM decreased by the same byte amount because both captures reported the same installed physical-memory total.

## Measured FOXAI component working sets

| Component | Minimal load | Normal loaded | Loaded − minimal |
|---|---:|---:|---:|
| Shared model runtime | 0.00 GB | 29.88 GB | 29.88 GB |
| Idle ComfyUI runtime | 0.00 GB | 0.57 GB | 0.57 GB |
| FOXAI Desktop | 0.00 GB | 0.09 GB | 0.09 GB |
| FOXAI WebUI | 0.08 GB | 0.08 GB | 0.01 GB |

The shared model runtime was the dominant measured FOXAI process at 29.88 GB (27.82 GiB). The WebUI, Desktop, and idle ComfyUI working sets were comparatively smaller. These process working sets are point-in-time values and are not an exclusive additive accounting of all physical memory.

## Capacity headroom observations

- Available physical RAM at normal loaded capture: 8.38 GB (7.80 GiB).
- Point-in-time physical-memory headroom: 16.36%.
- Captured commit headroom: 26.66 GB (24.82 GiB).
- Current page-file usage at the loaded capture was 693 MiB. The 8191 MiB value is a historical peak since boot, not the page-file usage at capture time.

## Known limitations

- The loaded qualification could not determine active ComfyUI generation without connecting to live workflow state; the capture therefore relied on the user’s idle-queue precondition.
- The evidence does not prove capacity during active image generation, longer model contexts, multiple simultaneous large models, additional applications, or future workload changes.
- This comparison does not diagnose the computer and issues no repair, deletion, service, startup, page-file, security, purchasing, model-replacement, or performance-tuning recommendation.

## Evidence integrity

All eight authoritative input files were hash-verified. Both source qualification states and both capture-receipt relationships were verified. The original minimal-load and normal-loaded evidence was read only and unchanged.
