FOXAI USB C3A — ComfyUI Dependency Closure and Binary Compatibility Preflight

PURPOSE
This package gathers exact read-only evidence needed before planning an isolated
ComfyUI dependency stack at:

  Z:\FOXAI\Runtime\ComfyUI\site-packages

SAFETY BOUNDARY
Running the preflight does NOT:
- install or uninstall any package
- download anything
- copy torch or any dependency
- create the preferred isolated target
- edit Desktop, WebUI, ComfyUI, or launcher files
- launch FOXAI, Desktop, WebUI, or ComfyUI
- access the network

The only writes are NEW evidence files inside this package's own:

  PREFLIGHT_OUTPUT\<UTC timestamp>\

PLACEMENT
Extract the whole folder directly inside the verified FOXAI root so the layout is:

  Z:\FOXAI\FOXAI_USBC3A_COMFYUI_DEPENDENCY_PREFLIGHT\

RUN
Double-click:

  RUN_USB_C3A_PREFLIGHT.bat

Then upload the newest timestamped folder under PREFLIGHT_OUTPUT for exact review.

WHAT C3A CHECKS
- exact portable Python version, ABI, extension suffix, and wheel tags
- ComfyUI and custom-node dependency manifests
- static third-party import candidates
- existing distributions in Desktop/Core/isolated target paths
- wheelhouse metadata and cp314/win_amd64 compatibility
- host torch/torchvision/torchaudio metadata and version pins
- portable-Python loading of the host stack, with a tiny CPU tensor smoke test
- PE architecture and imported DLL names for candidate binary paths

IMPORTANT
A successful preflight is evidence only. It does not authorize an install, copy,
launcher change, or ComfyUI launch.
