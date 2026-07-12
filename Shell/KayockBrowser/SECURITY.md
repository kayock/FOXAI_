# Kayock Browser 2.5.1 RC Security Notes

This release candidate freezes new browser features and focuses on hardening the foundation before installer distribution.

## Hardened in 2.5.1 RC

- Main app window uses `nodeIntegration: false` and `contextIsolation: true`.
- Browser webviews are created with `nodeIntegration=no`, `contextIsolation=yes`, `webSecurity=yes`, and `allowRunningInsecureContent=no`.
- Raw webview popups are not granted directly; popups are routed into Kayock tabs by browser handlers.
- Permission requests for geolocation, notifications, media, MIDI SysEx, and clipboard-read are blocked by default.
- External URL launching is limited to `http://` and `https://` URLs.
- Local shell actions are restricted to the Kayock Trophy Room / download folder.
- DevTools and Inspect Element are disabled unless launched with `KAYOCK_DEVTOOLS=1`.
- The local application shell has a Content Security Policy.
- Installer config uses ASAR packaging for normal release builds.

## Still needs real-world testing

- Login and OAuth popups on major sites.
- YouTube fullscreen and pointer lock behavior.
- Download flows for PDFs, ZIPs, model files, and images.
- Windows installer build/signing on a Windows machine.
- Code-signing certificate before public distribution.

## Security philosophy

Kayock should be useful without being reckless. New powers should live behind clear user intent, clear UI, and narrow permissions.
