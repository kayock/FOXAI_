# Repair Bay System Change Comparison

- Comparison: `CMP-20260720T212839Z-3F6AA024`
- Before: **After Webroot uninstall** — 2026-07-20T21:14:35+00:00
- After: **After Webroot removal  part 2** — 2026-07-20T21:28:13+00:00
- Summary: 11 added, 7 removed, 8 changed, 7 stopped, 1 disabled.

## Changes

### Added — Intel(R) Chipset Device Software
- Category: applications
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "Intel(R) Chipset Device Software",
    "version": "10.1.19468.8385",
    "publisher": "Intel(R) Corporation",
    "install_location": null
  }
}
```

### Removed — Intel(R) Chipset Device Software
- Category: applications
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "Intel(R) Chipset Device Software",
    "version": "10.1.19468.8385",
    "publisher": "Intel Corporation",
    "install_location": ""
  },
  "after": null
}
```

### Removed — Webroot SecureAnywhere
- Category: applications
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "Webroot SecureAnywhere",
    "version": "9.0.45.63",
    "publisher": "Webroot",
    "install_location": "C:\\Program Files\\Webroot\\"
  },
  "after": null
}
```

### Changed — 4K Video Downloader+
- Category: applications
- Classification: Review Suggested
- Evidence:
```json
{
  "install_location": {
    "before": "C:\\Program Files\\4KDownload\\4kvideodownloaderplus\\",
    "after": null
  }
}
```

### Changed — Dell SupportAssist OS Recovery Plugin for Dell Update
- Category: applications
- Classification: Review Suggested
- Evidence:
```json
{
  "install_location": {
    "before": null,
    "after": "C:\\Program Files\\Dell\\SARemediation\\plugin\\"
  }
}
```

### Changed — Dell SupportAssist Remediation
- Category: applications
- Classification: Review Suggested
- Evidence:
```json
{
  "install_location": {
    "before": null,
    "after": "C:\\Program Files\\Dell\\SARemediation\\agent\\"
  }
}
```

### Changed — Foxit PDF Reader
- Category: applications
- Classification: Review Suggested
- Evidence:
```json
{
  "install_location": {
    "before": null,
    "after": "C:\\Program Files (x86)\\Foxit Software\\Foxit PDF Reader\\"
  }
}
```

### Changed — UE Prerequisites (x64)
- Category: applications
- Classification: Review Suggested
- Evidence:
```json
{
  "install_location": {
    "before": "",
    "after": null
  }
}
```

### Added — Microsoft Defender Core Service
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "MDCoreSvc",
    "display_name": "Microsoft Defender Core Service",
    "state": "Running",
    "start_type": "Auto",
    "executable_path": "\"C:\\ProgramData\\Microsoft\\Windows Defender\\Platform\\4.18.26060.3008-0\\MpDefenderCoreService.exe\"",
    "service_account_category": "system",
    "process_id": 22728
  }
}
```

### Stopped — BitLocker Drive Encryption Service
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Running",
    "after": "Stopped"
  }
}
```

### Stopped — Client License Service (ClipSVC)
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Running",
    "after": "Stopped"
  }
}
```

### Stopped — Function Discovery Provider Host
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Running",
    "after": "Stopped"
  }
}
```

### Stopped — Windows Installer
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Running",
    "after": "Stopped"
  }
}
```

### Stopped — Printer Extensions and Notifications
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Running",
    "after": "Stopped"
  }
}
```

### Changed — Microsoft Defender Antivirus Network Inspection Service
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "executable_path": {
    "before": "\"C:\\Program Files\\Windows Defender\\NisSrv.exe\"",
    "after": "\"C:\\ProgramData\\Microsoft\\Windows Defender\\Platform\\4.18.26060.3008-0\\NisSrv.exe\""
  }
}
```

### Changed — Microsoft Defender Antivirus Service
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "executable_path": {
    "before": "\"C:\\Program Files\\Windows Defender\\MsMpEng.exe\"",
    "after": "\"C:\\ProgramData\\Microsoft\\Windows Defender\\Platform\\4.18.26060.3008-0\\MsMpEng.exe\""
  }
}
```

### Stopped — WMI Performance Adapter
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Running",
    "after": "Stopped"
  }
}
```

### Disabled — WRSVC
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Running",
    "after": "Stopped"
  },
  "start_type": {
    "before": "Auto",
    "after": "Disabled"
  }
}
```

### Stopped — Xbox Live Auth Manager
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Running",
    "after": "Stopped"
  }
}
```

### Added — \SoftLanding\S-1-5-21-407754733-4278090185-2299335465-1001\SoftLandingDeferralTask-{8e98b0a3-038c-49f5-b7ac-bd86565fb073}
- Category: scheduled_tasks
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "path": "\\SoftLanding\\S-1-5-21-407754733-4278090185-2299335465-1001\\SoftLandingDeferralTask-{8e98b0a3-038c-49f5-b7ac-bd86565fb073}",
    "state": "Ready",
    "enabled": true
  }
}
```

### Added — \SoftLanding\S-1-5-21-407754733-4278090185-2299335465-1001\SoftLandingTriggerTask-128000000001615609-render-{de4f379d-fde2-4230-b024-6ddf9e21f628}
- Category: scheduled_tasks
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "path": "\\SoftLanding\\S-1-5-21-407754733-4278090185-2299335465-1001\\SoftLandingTriggerTask-128000000001615609-render-{de4f379d-fde2-4230-b024-6ddf9e21f628}",
    "state": "Disabled",
    "enabled": false
  }
}
```

### Removed — \SoftLanding\S-1-5-21-407754733-4278090185-2299335465-1001\SoftLandingDeferralTask-{dd72f164-093c-4e0e-aedd-7378e3432692}
- Category: scheduled_tasks
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "path": "\\SoftLanding\\S-1-5-21-407754733-4278090185-2299335465-1001\\SoftLandingDeferralTask-{dd72f164-093c-4e0e-aedd-7378e3432692}",
    "state": "Ready",
    "enabled": true
  },
  "after": null
}
```

### Removed — \SoftLanding\S-1-5-21-407754733-4278090185-2299335465-1001\SoftLandingTriggerTask-128000000001615609-render-{c5eb7196-bf75-445e-9f3e-0dd0176d81a2}
- Category: scheduled_tasks
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "path": "\\SoftLanding\\S-1-5-21-407754733-4278090185-2299335465-1001\\SoftLandingTriggerTask-128000000001615609-render-{c5eb7196-bf75-445e-9f3e-0dd0176d81a2}",
    "state": "Disabled",
    "enabled": false
  },
  "after": null
}
```

### Changed — \Microsoft\Windows\WlanSvc\CDSSync
- Category: scheduled_tasks
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Running",
    "after": "Ready"
  }
}
```

### Added — 49351
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 49351,
    "process_id": 12304,
    "process_name": "esrv.exe",
    "scope": "localhost"
  }
}
```

### Added — 8188
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 8188,
    "process_id": 7332,
    "process_name": "python.exe",
    "scope": "localhost"
  }
}
```

### Added — DellSupportAssistRemedationService.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "DellSupportAssistRemedationService.exe",
    "process_id": 22756,
    "executable_path": "",
    "publisher": "",
    "signature_status": "",
    "working_set_bytes": 104136704,
    "private_bytes": 70119424,
    "cpu_time_seconds": 2.172,
    "start_time": "07/20/2026 15:12:57",
    "services": [
      "A",
      "D",
      "R",
      "S",
      "a",
      "d",
      "e",
      "i",
      "l",
      "m",
      "n",
      "o",
      "p",
      "r",
      "s",
      "t",
      "u"
    ]
  }
}
```

### Added — esrv.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "esrv.exe",
    "process_id": 12304,
    "executable_path": "C:\\Program Files\\Intel\\SUR\\QUEENCREEK\\x64\\esrv.exe",
    "publisher": "CN=Intel Corporation, O=Intel Corporation, S=California, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 146710528,
    "private_bytes": 139808768,
    "cpu_time_seconds": 3.188,
    "start_time": "07/20/2026 15:14:58",
    "services": []
  }
}
```

### Added — ShellExperienceHost.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "ShellExperienceHost.exe",
    "process_id": 7596,
    "executable_path": "C:\\WINDOWS\\SystemApps\\ShellExperienceHost_cw5n1h2txyewy\\ShellExperienceHost.exe",
    "publisher": "CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 110276608,
    "private_bytes": 47632384,
    "cpu_time_seconds": 0.453,
    "start_time": "07/20/2026 15:23:08",
    "services": []
  }
}
```

### Added — ShellHost.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "ShellHost.exe",
    "process_id": 7224,
    "executable_path": "C:\\WINDOWS\\system32\\shellhost.exe",
    "publisher": "CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 147546112,
    "private_bytes": 84217856,
    "cpu_time_seconds": 0.672,
    "start_time": "07/20/2026 15:15:45",
    "services": []
  }
}
```

### Added — svchost.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "svchost.exe",
    "process_id": 10000,
    "executable_path": "",
    "publisher": "",
    "signature_status": "",
    "working_set_bytes": 84213760,
    "private_bytes": 53751808,
    "cpu_time_seconds": 1.641,
    "start_time": "07/20/2026 15:10:56",
    "services": [
      "A",
      "S",
      "X",
      "c",
      "p",
      "v"
    ]
  }
}
```

### Removed — PowerToys.ColorPickerUI.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "PowerToys.ColorPickerUI.exe",
    "process_id": 19504,
    "executable_path": "C:\\Program Files\\PowerToys\\PowerToys.ColorPickerUI.exe",
    "publisher": "CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 79044608,
    "private_bytes": 165199872,
    "cpu_time_seconds": 1.656,
    "start_time": "07/20/2026 15:11:18",
    "services": []
  },
  "after": null
}
```

### Removed — PowerToys.PowerLauncher.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "PowerToys.PowerLauncher.exe",
    "process_id": 19784,
    "executable_path": "C:\\Program Files\\PowerToys\\PowerToys.PowerLauncher.exe",
    "publisher": "CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 191303680,
    "private_bytes": 224305152,
    "cpu_time_seconds": 12.094,
    "start_time": "07/20/2026 15:11:22",
    "services": []
  },
  "after": null
}
```

### Removed — Widgets.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "Widgets.exe",
    "process_id": 13492,
    "executable_path": "C:\\Program Files\\WindowsApps\\MicrosoftWindows.Client.WebExperience_526.17301.40.0_x64__cw5n1h2txyewy\\Dashboard\\Widgets.exe",
    "publisher": "CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 77971456,
    "private_bytes": 14278656,
    "cpu_time_seconds": 1.562,
    "start_time": "07/20/2026 15:10:59",
    "services": []
  },
  "after": null
}
```

### Decreased — Available Bytes
- Category: resources
- Classification: Runtime Noise
- Evidence:
```json
{
  "before": 36569661440,
  "after": 35996073984,
  "delta": -573587456
}
```

### Increased — Committed Bytes
- Category: resources
- Classification: Runtime Noise
- Evidence:
```json
{
  "before": 15802802176,
  "after": 16391016448,
  "delta": 588214272
}
```

### Increased — Cached Bytes
- Category: resources
- Classification: Runtime Noise
- Evidence:
```json
{
  "before": 342167552,
  "after": 356270080,
  "delta": 14102528
}
```

### Decreased — Free disk space C:\
- Category: resources
- Classification: Observation
- Evidence:
```json
{
  "before": 559158300672,
  "after": 558595457024,
  "delta": -562843648
}
```

### Decreased — Free disk space Z:\
- Category: resources
- Classification: Observation
- Evidence:
```json
{
  "before": 786540003328,
  "after": 786538692608,
  "delta": -1310720
}
```

---
Local read-only report. Secret-bearing fields were excluded. No network transmission occurred.
