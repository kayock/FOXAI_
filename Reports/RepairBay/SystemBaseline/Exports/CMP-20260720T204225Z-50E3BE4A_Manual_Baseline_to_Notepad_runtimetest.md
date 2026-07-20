# Repair Bay System Change Comparison

- Comparison: `CMP-20260720T204225Z-50E3BE4A`
- Before: **Manual Baseline** — 2026-07-20T20:40:45+00:00
- After: **Notepad runtimetest** — 2026-07-20T20:42:02+00:00
- Summary: 2 added, 1 removed.

## Changes

### Added — Notepad.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "Notepad.exe",
    "process_id": 28396,
    "executable_path": "C:\\Program Files\\WindowsApps\\Microsoft.WindowsNotepad_11.2605.34.0_x64__8wekyb3d8bbwe\\Notepad\\Notepad.exe",
    "publisher": "CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 173596672,
    "private_bytes": 107737088,
    "cpu_time_seconds": 0.891,
    "start_time": "07/20/2026 14:41:19",
    "services": []
  }
}
```

### Added — WRSA.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "WRSA.exe",
    "process_id": 2644,
    "executable_path": "",
    "publisher": "",
    "signature_status": "",
    "working_set_bytes": 88084480,
    "private_bytes": 340815872,
    "cpu_time_seconds": 1653.828,
    "start_time": "07/19/2026 16:14:21",
    "services": [
      "C",
      "R",
      "S",
      "V",
      "W"
    ]
  }
}
```

### Removed — RuntimeBroker.exe
- Category: processes
- Classification: Runtime Noise
- Evidence:
```json
{
  "before": {
    "name": "RuntimeBroker.exe",
    "process_id": 2608,
    "executable_path": "C:\\Windows\\System32\\RuntimeBroker.exe",
    "publisher": "CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 52441088,
    "private_bytes": 8912896,
    "cpu_time_seconds": 3.891,
    "start_time": "07/19/2026 16:15:01",
    "services": []
  },
  "after": null
}
```

### Increased — Available Bytes
- Category: resources
- Classification: Runtime Noise
- Evidence:
```json
{
  "before": 37784506368,
  "after": 37808033792,
  "delta": 23527424
}
```

### Decreased — Committed Bytes
- Category: resources
- Classification: Runtime Noise
- Evidence:
```json
{
  "before": 19661590528,
  "after": 19622342656,
  "delta": -39247872
}
```

### Increased — Cached Bytes
- Category: resources
- Classification: Runtime Noise
- Evidence:
```json
{
  "before": 954281984,
  "after": 954888192,
  "delta": 606208
}
```

### Decreased — Free disk space C:\
- Category: resources
- Classification: Observation
- Evidence:
```json
{
  "before": 547745308672,
  "after": 547722670080,
  "delta": -22638592
}
```

### Decreased — Free disk space Z:\
- Category: resources
- Classification: Observation
- Evidence:
```json
{
  "before": 786542886912,
  "after": 786542100480,
  "delta": -786432
}
```

---
Local read-only report. Secret-bearing fields were excluded. No network transmission occurred.
