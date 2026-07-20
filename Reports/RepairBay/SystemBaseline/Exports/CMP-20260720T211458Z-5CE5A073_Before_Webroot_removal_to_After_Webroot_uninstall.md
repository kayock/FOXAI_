# Repair Bay System Change Comparison

- Comparison: `CMP-20260720T211458Z-5CE5A073`
- Before: **Before Webroot removal** — 2026-07-20T20:57:43+00:00
- After: **After Webroot uninstall** — 2026-07-20T21:14:35+00:00
- Summary: 39 added, 53 removed, 5 changed, 9 started, 6 stopped.

## Changes

### Removed — calibre 64bit
- Category: applications
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "calibre 64bit",
    "version": "9.1.0",
    "publisher": "Kovid Goyal",
    "install_location": "C:\\Program Files\\Calibre2\\"
  },
  "after": null
}
```

### Removed — EA app
- Category: applications
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "EA app",
    "version": "13.725.0.6238",
    "publisher": "Electronic Arts",
    "install_location": null
  },
  "after": null
}
```

### Removed — FocusWriter
- Category: applications
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "FocusWriter",
    "version": "1.9.0",
    "publisher": "Graeme Gott",
    "install_location": "\"C:\\Program Files\\FocusWriter\""
  },
  "after": null
}
```

### Removed — Microsoft Power BI Desktop (x64)
- Category: applications
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "Microsoft Power BI Desktop (x64)",
    "version": "2.146.705.0",
    "publisher": "Microsoft Corporation",
    "install_location": ""
  },
  "after": null
}
```

### Removed — Microsoft PowerBI Desktop (x64)
- Category: applications
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "Microsoft PowerBI Desktop (x64)",
    "version": "2.146.705.0",
    "publisher": "Microsoft Corporation",
    "install_location": null
  },
  "after": null
}
```

### Removed — Star Wars: Galaxy of Heroes
- Category: applications
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "Star Wars: Galaxy of Heroes",
    "version": "1.0.40.2012955",
    "publisher": "Electronic Arts, Inc. (en_US)",
    "install_location": "C:\\Program Files\\EA Games\\SWGoH\\"
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
    "before": null,
    "after": "C:\\Program Files\\4KDownload\\4kvideodownloaderplus\\"
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
    "before": "C:\\Program Files\\Dell\\SARemediation\\plugin\\",
    "after": null
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
    "before": "C:\\Program Files (x86)\\Foxit Software\\Foxit PDF Reader\\",
    "after": null
  }
}
```

### Added — AarSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "AarSvc_13f7d9",
    "display_name": "AarSvc_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k AarSvcGroup -p",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — BcastDVRUserService_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "BcastDVRUserService_13f7d9",
    "display_name": "BcastDVRUserService_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k BcastDVRUserService",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — BluetoothUserService_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "BluetoothUserService_13f7d9",
    "display_name": "BluetoothUserService_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k BthAppGroup -p",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — CaptureService_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "CaptureService_13f7d9",
    "display_name": "CaptureService_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k LocalService -p",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — cbdhsvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "cbdhsvc_13f7d9",
    "display_name": "cbdhsvc_13f7d9",
    "state": "Running",
    "start_type": "Auto",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k ClipboardSvcGroup -p",
    "service_account_category": "unknown",
    "process_id": 3872
  }
}
```

### Added — CDPUserSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "CDPUserSvc_13f7d9",
    "display_name": "CDPUserSvc_13f7d9",
    "state": "Running",
    "start_type": "Auto",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 10380
  }
}
```

### Added — CloudBackupRestoreSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "CloudBackupRestoreSvc_13f7d9",
    "display_name": "CloudBackupRestoreSvc_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — ConsentUxUserSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "ConsentUxUserSvc_13f7d9",
    "display_name": "ConsentUxUserSvc_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k DevicesFlow",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — CredentialEnrollmentManagerUserSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "CredentialEnrollmentManagerUserSvc_13f7d9",
    "display_name": "CredentialEnrollmentManagerUserSvc_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\CredentialEnrollmentManager.exe",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — DeviceAssociationBrokerSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "DeviceAssociationBrokerSvc_13f7d9",
    "display_name": "DeviceAssociationBrokerSvc_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k DevicesFlow -p",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — DevicePickerUserSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "DevicePickerUserSvc_13f7d9",
    "display_name": "DevicePickerUserSvc_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k DevicesFlow",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — DevicesFlowUserSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "DevicesFlowUserSvc_13f7d9",
    "display_name": "DevicesFlowUserSvc_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k DevicesFlow",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — MessagingService_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "MessagingService_13f7d9",
    "display_name": "MessagingService_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — NPSMSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "NPSMSvc_13f7d9",
    "display_name": "NPSMSvc_13f7d9",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k LocalService -p",
    "service_account_category": "unknown",
    "process_id": 16960
  }
}
```

### Added — OneSyncSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "OneSyncSvc_13f7d9",
    "display_name": "OneSyncSvc_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — P9RdrService_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "P9RdrService_13f7d9",
    "display_name": "P9RdrService_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k P9RdrService -p",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — PenService_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "PenService_13f7d9",
    "display_name": "PenService_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k PenService",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — PimIndexMaintenanceSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "PimIndexMaintenanceSvc_13f7d9",
    "display_name": "PimIndexMaintenanceSvc_13f7d9",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 18944
  }
}
```

### Added — PrintWorkflowUserSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "PrintWorkflowUserSvc_13f7d9",
    "display_name": "PrintWorkflowUserSvc_13f7d9",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k PrintWorkflow",
    "service_account_category": "unknown",
    "process_id": 0
  }
}
```

### Added — UdkUserSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "UdkUserSvc_13f7d9",
    "display_name": "UdkUserSvc_13f7d9",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UdkSvcGroup",
    "service_account_category": "unknown",
    "process_id": 13452
  }
}
```

### Added — UnistoreSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "UnistoreSvc_13f7d9",
    "display_name": "UnistoreSvc_13f7d9",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\System32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 18944
  }
}
```

### Added — UserDataSvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "UserDataSvc_13f7d9",
    "display_name": "UserDataSvc_13f7d9",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 18944
  }
}
```

### Added — webthreatdefusersvc_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "webthreatdefusersvc_13f7d9",
    "display_name": "webthreatdefusersvc_13f7d9",
    "state": "Running",
    "start_type": "Auto",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k LocalSystemNetworkRestricted -p",
    "service_account_category": "unknown",
    "process_id": 10780
  }
}
```

### Added — WpnUserService_13f7d9
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "WpnUserService_13f7d9",
    "display_name": "WpnUserService_13f7d9",
    "state": "Running",
    "start_type": "Auto",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 10964
  }
}
```

### Removed — Agent Activation Runtime_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "AarSvc_202248",
    "display_name": "Agent Activation Runtime_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k AarSvcGroup -p",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — GameDVR and Broadcast User Service_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "BcastDVRUserService_202248",
    "display_name": "GameDVR and Broadcast User Service_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k BcastDVRUserService",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — Bluetooth User Support Service_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "BluetoothUserService_202248",
    "display_name": "Bluetooth User Support Service_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k BthAppGroup -p",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — CaptureService_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "CaptureService_202248",
    "display_name": "CaptureService_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k LocalService -p",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — Clipboard User Service_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "cbdhsvc_202248",
    "display_name": "Clipboard User Service_202248",
    "state": "Running",
    "start_type": "Auto",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k ClipboardSvcGroup -p",
    "service_account_category": "unknown",
    "process_id": 17384
  },
  "after": null
}
```

### Removed — Connected Devices Platform User Service_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "CDPUserSvc_202248",
    "display_name": "Connected Devices Platform User Service_202248",
    "state": "Running",
    "start_type": "Auto",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 14076
  },
  "after": null
}
```

### Removed — Cloud Backup and Restore Service_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "CloudBackupRestoreSvc_202248",
    "display_name": "Cloud Backup and Restore Service_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — ConsentUX User Service_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "ConsentUxUserSvc_202248",
    "display_name": "ConsentUX User Service_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k DevicesFlow",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — CredentialEnrollmentManagerUserSvc_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "CredentialEnrollmentManagerUserSvc_202248",
    "display_name": "CredentialEnrollmentManagerUserSvc_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\CredentialEnrollmentManager.exe",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — DeviceAssociationBroker_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "DeviceAssociationBrokerSvc_202248",
    "display_name": "DeviceAssociationBroker_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k DevicesFlow -p",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — DevicePicker_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "DevicePickerUserSvc_202248",
    "display_name": "DevicePicker_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k DevicesFlow",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — DevicesFlow_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "DevicesFlowUserSvc_202248",
    "display_name": "DevicesFlow_202248",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k DevicesFlow",
    "service_account_category": "unknown",
    "process_id": 13348
  },
  "after": null
}
```

### Removed — EABackgroundService
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "EABackgroundService",
    "display_name": "EABackgroundService",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "\"C:\\Program Files\\Electronic Arts\\EA Desktop\\EA Desktop\\EABackgroundService.exe\"",
    "service_account_category": "system",
    "process_id": 0
  },
  "after": null
}
```

### Removed — MessagingService_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "MessagingService_202248",
    "display_name": "MessagingService_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — Now Playing Session Manager Service_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "NPSMSvc_202248",
    "display_name": "Now Playing Session Manager Service_202248",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k LocalService -p",
    "service_account_category": "unknown",
    "process_id": 18212
  },
  "after": null
}
```

### Removed — Sync Host_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "OneSyncSvc_202248",
    "display_name": "Sync Host_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — P9RdrService_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "P9RdrService_202248",
    "display_name": "P9RdrService_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k P9RdrService -p",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — PenService_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "PenService_202248",
    "display_name": "PenService_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k PenService",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — Contact Data_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "PimIndexMaintenanceSvc_202248",
    "display_name": "Contact Data_202248",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 19676
  },
  "after": null
}
```

### Removed — PrintWorkflow_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "PrintWorkflowUserSvc_202248",
    "display_name": "PrintWorkflow_202248",
    "state": "Stopped",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k PrintWorkflow",
    "service_account_category": "unknown",
    "process_id": 0
  },
  "after": null
}
```

### Removed — Udk User Service_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "UdkUserSvc_202248",
    "display_name": "Udk User Service_202248",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UdkSvcGroup",
    "service_account_category": "unknown",
    "process_id": 7632
  },
  "after": null
}
```

### Removed — User Data Storage_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "UnistoreSvc_202248",
    "display_name": "User Data Storage_202248",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\System32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 19676
  },
  "after": null
}
```

### Removed — User Data Access_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "UserDataSvc_202248",
    "display_name": "User Data Access_202248",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 19676
  },
  "after": null
}
```

### Removed — Web Threat Defense User Service_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "webthreatdefusersvc_202248",
    "display_name": "Web Threat Defense User Service_202248",
    "state": "Running",
    "start_type": "Auto",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k LocalSystemNetworkRestricted -p",
    "service_account_category": "unknown",
    "process_id": 7268
  },
  "after": null
}
```

### Removed — Windows Push Notifications User Service_202248
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "WpnUserService_202248",
    "display_name": "Windows Push Notifications User Service_202248",
    "state": "Running",
    "start_type": "Auto",
    "executable_path": "C:\\WINDOWS\\system32\\svchost.exe -k UnistackSvcGroup",
    "service_account_category": "unknown",
    "process_id": 13532
  },
  "after": null
}
```

### Removed — Web Threat Shield Service
- Category: services
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "name": "WRWTSSvc",
    "display_name": "Web Threat Shield Service",
    "state": "Running",
    "start_type": "Manual",
    "executable_path": "\"c:\\Program Files\\Webroot\\WebThreatShield\\WRWTSSvc.exe\"",
    "service_account_category": "system",
    "process_id": 9832
  },
  "after": null
}
```

### Stopped — Application Management
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

### Started — BitLocker Drive Encryption Service
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Stopped",
    "after": "Running"
  }
}
```

### Stopped — Background Intelligent Transfer Service
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
    "after": "Manual"
  }
}
```

### Started — Client License Service (ClipSVC)
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Stopped",
    "after": "Running"
  }
}
```

### Started — Display Enhancement Service
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Stopped",
    "after": "Running"
  }
}
```

### Stopped — Data Sharing Service
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

### Started — Windows Installer
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Stopped",
    "after": "Running"
  }
}
```

### Started — Printer Extensions and Notifications
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Stopped",
    "after": "Running"
  }
}
```

### Stopped — Quality Windows Audio Video Experience
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

### Stopped — Diagnostic Service Host
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

### Started — Microsoft Defender Antivirus Network Inspection Service
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Stopped",
    "after": "Running"
  }
}
```

### Started — Microsoft Defender Antivirus Service
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Stopped",
    "after": "Running"
  },
  "start_type": {
    "before": "Manual",
    "after": "Auto"
  }
}
```

### Started — Microsoft Account Sign-in Assistant
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Stopped",
    "after": "Running"
  }
}
```

### Started — Windows Update
- Category: services
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Stopped",
    "after": "Running"
  }
}
```

### Stopped — Microsoft Usage and Quality Insights
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

### Removed — EADM
- Category: startup_entries
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "source": "registry_run",
    "scope": "CurrentUser",
    "name": "EADM",
    "target": "\"C:\\Program Files\\Electronic Arts\\EA Desktop\\EA Desktop\\EALauncher.exe\" -silent",
    "enabled": true
  },
  "after": null
}
```

### Removed — WRSVC
- Category: startup_entries
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "source": "registry_run",
    "scope": "LocalMachine32",
    "name": "WRSVC",
    "target": "\"C:\\Program Files\\Webroot\\WRSA.exe\" -ul",
    "enabled": true
  },
  "after": null
}
```

### Changed — \Microsoft\Windows\WDI\ResolutionHost
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

### Changed — \Microsoft\Windows\WlanSvc\CDSSync
- Category: scheduled_tasks
- Classification: Review Suggested
- Evidence:
```json
{
  "state": {
    "before": "Ready",
    "after": "Running"
  }
}
```

### Added — 49705
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "protocol": "TCP",
    "local_address": "0.0.0.0",
    "local_port": 49705,
    "process_id": 1716,
    "process_name": "",
    "scope": "all_interfaces"
  }
}
```

### Added — 32401
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 32401,
    "process_id": 16940,
    "process_name": "",
    "scope": "localhost"
  }
}
```

### Added — 59786
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 59786,
    "process_id": 604,
    "process_name": "",
    "scope": "localhost"
  }
}
```

### Added — 59808
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 59808,
    "process_id": 22080,
    "process_name": "",
    "scope": "localhost"
  }
}
```

### Added — 59829
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 59829,
    "process_id": 21980,
    "process_name": "",
    "scope": "localhost"
  }
}
```

### Added — 32400
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "protocol": "TCP",
    "local_address": "::",
    "local_port": 32400,
    "process_id": 16940,
    "process_name": "",
    "scope": "all_interfaces"
  }
}
```

### Added — 49705
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": null,
  "after": {
    "protocol": "TCP",
    "local_address": "::",
    "local_port": 49705,
    "process_id": 1716,
    "process_name": "",
    "scope": "all_interfaces"
  }
}
```

### Removed — 49707
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "protocol": "TCP",
    "local_address": "0.0.0.0",
    "local_port": 49707,
    "process_id": 1628,
    "process_name": "",
    "scope": "all_interfaces"
  },
  "after": null
}
```

### Removed — 27019
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 27019,
    "process_id": 9832,
    "process_name": "",
    "scope": "localhost"
  },
  "after": null
}
```

### Removed — 32401
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 32401,
    "process_id": 21312,
    "process_name": "Plex Media Server.exe",
    "scope": "localhost"
  },
  "after": null
}
```

### Removed — 49351
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 49351,
    "process_id": 9128,
    "process_name": "",
    "scope": "localhost"
  },
  "after": null
}
```

### Removed — 50037
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 50037,
    "process_id": 18540,
    "process_name": "",
    "scope": "localhost"
  },
  "after": null
}
```

### Removed — 51784
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 51784,
    "process_id": 18628,
    "process_name": "",
    "scope": "localhost"
  },
  "after": null
}
```

### Removed — 8188
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "protocol": "TCP",
    "local_address": "127.0.0.1",
    "local_port": 8188,
    "process_id": 2852,
    "process_name": "python.exe",
    "scope": "localhost"
  },
  "after": null
}
```

### Removed — 42050
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "protocol": "TCP",
    "local_address": "::1",
    "local_port": 42050,
    "process_id": 28904,
    "process_name": "",
    "scope": "localhost"
  },
  "after": null
}
```

### Removed — 32400
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "protocol": "TCP",
    "local_address": "::",
    "local_port": 32400,
    "process_id": 21312,
    "process_name": "Plex Media Server.exe",
    "scope": "all_interfaces"
  },
  "after": null
}
```

### Removed — 49707
- Category: listeners
- Classification: Significant Change
- Evidence:
```json
{
  "before": {
    "protocol": "TCP",
    "local_address": "::",
    "local_port": 49707,
    "process_id": 1628,
    "process_name": "",
    "scope": "all_interfaces"
  },
  "after": null
}
```

### Added — Dell.Update.SubAgent.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "Dell.Update.SubAgent.exe",
    "process_id": 8580,
    "executable_path": "",
    "publisher": "",
    "signature_status": "",
    "working_set_bytes": 78340096,
    "private_bytes": 47992832,
    "cpu_time_seconds": 2.703,
    "start_time": "07/20/2026 15:10:54",
    "services": []
  }
}
```

### Added — IGCC.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "IGCC.exe",
    "process_id": 21588,
    "executable_path": "C:\\Program Files\\WindowsApps\\AppUp.IntelGraphicsExperience_1.100.5688.0_x64__8j3eq9eme6ctt\\IGCC.exe",
    "publisher": "",
    "signature_status": "NotSigned",
    "working_set_bytes": 84934656,
    "private_bytes": 45092864,
    "cpu_time_seconds": 0.203,
    "start_time": "07/20/2026 15:11:45",
    "services": []
  }
}
```

### Added — IGCCTray.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "IGCCTray.exe",
    "process_id": 20216,
    "executable_path": "C:\\Program Files\\WindowsApps\\AppUp.IntelGraphicsExperience_1.100.5688.0_x64__8j3eq9eme6ctt\\GCP.ML.BackgroundSysTray\\IGCCTray.exe",
    "publisher": "",
    "signature_status": "NotSigned",
    "working_set_bytes": 85884928,
    "private_bytes": 48480256,
    "cpu_time_seconds": 0.953,
    "start_time": "07/20/2026 15:11:43",
    "services": []
  }
}
```

### Added — LockApp.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "LockApp.exe",
    "process_id": 14716,
    "executable_path": "C:\\WINDOWS\\SystemApps\\Microsoft.LockApp_cw5n1h2txyewy\\LockApp.exe",
    "publisher": "CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 119558144,
    "private_bytes": 49688576,
    "cpu_time_seconds": 1.031,
    "start_time": "07/20/2026 15:11:01",
    "services": []
  }
}
```

### Added — MsMpEng.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "MsMpEng.exe",
    "process_id": 5684,
    "executable_path": "",
    "publisher": "",
    "signature_status": "",
    "working_set_bytes": 519073792,
    "private_bytes": 447971328,
    "cpu_time_seconds": 186.375,
    "start_time": "07/20/2026 15:10:53",
    "services": [
      "D",
      "W",
      "d",
      "e",
      "f",
      "i",
      "n"
    ]
  }
}
```

### Added — PowerToys.ColorPickerUI.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
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
  }
}
```

### Added — PowerToys.PowerLauncher.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
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
  }
}
```

### Added — WavesSvc64.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": null,
  "after": {
    "name": "WavesSvc64.exe",
    "process_id": 10368,
    "executable_path": "C:\\Windows\\System32\\DriverStore\\FileRepository\\wavesapo11de.inf_amd64_c6cd4cf632788a8e\\WavesSvc64.exe",
    "publisher": "CN=Microsoft Windows Hardware Compatibility Publisher, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 144117760,
    "private_bytes": 121905152,
    "cpu_time_seconds": 1.469,
    "start_time": "07/20/2026 15:11:39",
    "services": []
  }
}
```

### Removed — DellSupportAssistRemedationService.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "DellSupportAssistRemedationService.exe",
    "process_id": 15120,
    "executable_path": "",
    "publisher": "",
    "signature_status": "",
    "working_set_bytes": 87949312,
    "private_bytes": 80736256,
    "cpu_time_seconds": 22.953,
    "start_time": "07/19/2026 16:16:24",
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
  },
  "after": null
}
```

### Removed — Memory Compression
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "Memory Compression",
    "process_id": 3384,
    "executable_path": "",
    "publisher": "",
    "signature_status": "",
    "working_set_bytes": 662265856,
    "private_bytes": 4038656,
    "cpu_time_seconds": 78.188,
    "start_time": "07/19/2026 16:14:21",
    "services": []
  },
  "after": null
}
```

### Removed — Notepad.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "Notepad.exe",
    "process_id": 28396,
    "executable_path": "C:\\Program Files\\WindowsApps\\Microsoft.WindowsNotepad_11.2605.34.0_x64__8wekyb3d8bbwe\\Notepad\\Notepad.exe",
    "publisher": "CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 169480192,
    "private_bytes": 106983424,
    "cpu_time_seconds": 0.922,
    "start_time": "07/20/2026 14:41:19",
    "services": []
  },
  "after": null
}
```

### Removed — Plex Media Server.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "Plex Media Server.exe",
    "process_id": 21312,
    "executable_path": "C:\\Program Files\\Plex\\Plex Media Server\\Plex Media Server.exe",
    "publisher": "CN=\"Plex, Inc.\", O=\"Plex, Inc.\", L=Campbell, S=California, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 129200128,
    "private_bytes": 304754688,
    "cpu_time_seconds": 767.094,
    "start_time": "07/19/2026 16:15:28",
    "services": []
  },
  "after": null
}
```

### Removed — ShellExperienceHost.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "ShellExperienceHost.exe",
    "process_id": 16180,
    "executable_path": "C:\\WINDOWS\\SystemApps\\ShellExperienceHost_cw5n1h2txyewy\\ShellExperienceHost.exe",
    "publisher": "CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 93134848,
    "private_bytes": 69046272,
    "cpu_time_seconds": 3.188,
    "start_time": "07/19/2026 20:31:26",
    "services": []
  },
  "after": null
}
```

### Removed — ShellHost.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "ShellHost.exe",
    "process_id": 1824,
    "executable_path": "C:\\WINDOWS\\system32\\shellhost.exe",
    "publisher": "CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US",
    "signature_status": "Valid",
    "working_set_bytes": 148189184,
    "private_bytes": 84332544,
    "cpu_time_seconds": 0.609,
    "start_time": "07/20/2026 14:43:25",
    "services": []
  },
  "after": null
}
```

### Removed — SurSvc.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "SurSvc.exe",
    "process_id": 4736,
    "executable_path": "",
    "publisher": "",
    "signature_status": "",
    "working_set_bytes": 79495168,
    "private_bytes": 94613504,
    "cpu_time_seconds": 322.125,
    "start_time": "07/19/2026 16:14:21",
    "services": [
      "C",
      "E",
      "K",
      "N",
      "Q",
      "R",
      "S",
      "U",
      "_",
      "a",
      "c",
      "e",
      "g",
      "m",
      "o",
      "p",
      "r",
      "s",
      "t",
      "v",
      "y"
    ]
  },
  "after": null
}
```

### Removed — svchost.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "svchost.exe",
    "process_id": 4164,
    "executable_path": "",
    "publisher": "",
    "signature_status": "",
    "working_set_bytes": 78684160,
    "private_bytes": 39358464,
    "cpu_time_seconds": 497.609,
    "start_time": "07/19/2026 16:14:21",
    "services": [
      "D",
      "T",
      "a",
      "c",
      "g",
      "i",
      "k",
      "r"
    ]
  },
  "after": null
}
```

### Removed — WRSA.exe
- Category: processes
- Classification: Observation
- Evidence:
```json
{
  "before": {
    "name": "WRSA.exe",
    "process_id": 2644,
    "executable_path": "",
    "publisher": "",
    "signature_status": "",
    "working_set_bytes": 88338432,
    "private_bytes": 342478848,
    "cpu_time_seconds": 1667.547,
    "start_time": "07/19/2026 16:14:21",
    "services": [
      "C",
      "R",
      "S",
      "V",
      "W"
    ]
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
  "before": 36004773888,
  "after": 36569661440,
  "delta": 564887552
}
```

### Decreased — Committed Bytes
- Category: resources
- Classification: Runtime Noise
- Evidence:
```json
{
  "before": 21513629696,
  "after": 15802802176,
  "delta": -5710827520
}
```

### Decreased — Cached Bytes
- Category: resources
- Classification: Runtime Noise
- Evidence:
```json
{
  "before": 956989440,
  "after": 342167552,
  "delta": -614821888
}
```

### Increased — Free disk space C:\
- Category: resources
- Classification: Observation
- Evidence:
```json
{
  "before": 547555999744,
  "after": 559158300672,
  "delta": 11602300928
}
```

### Decreased — Free disk space Z:\
- Category: resources
- Classification: Observation
- Evidence:
```json
{
  "before": 786540789760,
  "after": 786540003328,
  "delta": -786432
}
```

---
Local read-only report. Secret-bearing fields were excluded. No network transmission occurred.
