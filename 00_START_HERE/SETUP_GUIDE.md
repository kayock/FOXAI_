# Setup Guide

## What this ZIP contains

This package contains the structure and starter files for KayocktheOS. It does not include AI models.

## Recommended USB Layout

```text
USB_ROOT/
├── KayocktheOS/
└── FOXAI_USB/          optional old model source
```

## Model Strategy

Small files can be copied into KayocktheOS. Huge models should be referenced from your existing FOXAI folders until you decide they belong permanently in KayocktheOS.

Edit:

```text
System/Config/manifest.yaml
AI/Model_Links/FoxAI_Model_References.txt
```

## Launch

Double-click:

```text
Start_KayocktheOS.bat
```
