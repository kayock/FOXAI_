# Kayock Browser 2.5.1 RC Release Checklist

## Build

1. Run `npm install`.
2. Run `npm start` and smoke test the browser.
3. Run `npm run dist:win` on Windows to create:
   - `Kayock Browser Setup.exe`
   - `Kayock-Browser-2.5.1-rc.1-Portable.exe`
4. Confirm files appear in `dist/`.

## Smoke tests

- Launch app.
- Open new tab.
- Browse to Google, YouTube, Gmail, ChatGPT.
- Test back/forward/reload/home.
- Test zoom controls.
- Test Eagle Eye spell check and right-click suggestions.
- Test Tracks sidebar hover/pin behavior.
- Rename a Track.
- Move a tab to a Track.
- Save a screenshot to Trophy Room.
- Download a PDF or ZIP.
- Open download folder from Kayock.
- Confirm blocked permission events appear in Shield/Diagnostics.

## Release rule

No new features in this RC unless they fix security, packaging, or a launch-blocking bug.
