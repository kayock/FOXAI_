# Kayock Browser 2.5.1 RC — Foundation Release Candidate

Kayock Browser 2.5.1 RC is the hardened foundation build based on the 2.4 Hunter Workspaces polish release.

## What this build is for

- Final browser-base security pass.
- Installer and portable `.exe` packaging setup.
- Release-candidate smoke testing.
- Keeping AI features out of the stable browser foundation.

## Run from source

```bat
npm install
npm start
```

## Run with DevTools enabled

```bat
set KAYOCK_DEVTOOLS=1
npm start
```

## Build installer / portable EXE on Windows

```bat
npm install
npm run dist:win
```

Output will be created in `dist/`.

## Release direction

- 2.5.1 RC: secure and package the browser foundation.
- 2.5.x: bug fixes only.
- AI Edition: separate experimental branch based on this codebase later.
