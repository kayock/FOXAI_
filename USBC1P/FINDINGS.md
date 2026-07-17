# FOXAI USB Commissioning Phase 1 — Exact Preview Findings

## Bundled Python

`env\python\python314._pth` enables `python314.zip`, the current directory, and `import site`. The embedded base runtime is configured correctly, but the current tree contains no `env\python\Lib\site-packages` directory. The commissioner therefore checks where each third-party module actually comes from and flags modules that resolve outside the USB.

## Alternate KayocktheOS shell

`System\Launchers\launch.py` is a real separate shell launcher. It starts the local API, writes `System\Logs\boot.log`, may update the operator profile on first boot, and opens the Bridge dashboard in Kayock Browser. It remains a supported alternate workflow, not the current FOXAI WebUI startup path.

## Exact proposed additions

- `COMMISSION_FOXAI_USB.bat`
- `System\Commissioning\commission_usb.py`
- `00_START_HERE\USB_COMMISSIONING_GUIDE.md`

No existing file is modified or deleted.

## Phase 1 behavior

- READY / READY_WITH_NOTES / NEEDS_ATTENTION results;
- local-versus-host dependency origin checks;
- WebUI, Desktop, Creative Studio, alternate shell, and Bridge profiles;
- separate language-model, vision-projector, and creative-checkpoint inventory;
- port and disk-space checks;
- timestamped JSON and Markdown reports during normal use;
- operator-selected launch of existing WebUI or Desktop launchers;
- no automatic install, repair, download, configuration rewrite, folder creation, or service start.

Safe recreation of missing empty ComfyUI folders remains a later guarded action.
