# Changelog

## 2.5.1-rc.1 — Foundation Release Candidate

### 2.5.1 polish additions

- Fixed Windows launcher title and banner text.
- Hardened first-run dependency install to use the public npm registry.
- Added automatic Electron repair install if the first npm install is incomplete.
- Pinned Electron instead of using `latest` for more repeatable testing.
- Removed bundled package-lock file to avoid stale/internal registry URLs on tester machines.
- Added startup lazy-loading for heavy panels so tabs and the browser shell appear first.
- Updated Vault export metadata to 2.5.1 RC.


- Updated package version and app title to 2.5.1 RC.
- Added Electron Builder installer and portable EXE configuration.
- Added Windows icon asset (`assets/kayock.ico`).
- Added ASAR packaging configuration.
- Added security release notes.
- Added release checklist.
- Hardened external URL opening to http/https only.
- Disabled raw webview popup privilege; popups route through Kayock tab handling.
- Hardened webview preferences: no Node integration, context isolation, web security enabled, insecure content disabled.
- Added shell Content Security Policy.
- Disabled Inspect Element/DevTools in normal RC mode.
- Preserved Hunter Workspaces, Tracks sidebar polish, Eagle Eye spell check, Trophy Room, Shield, Journal, and browser UI.
