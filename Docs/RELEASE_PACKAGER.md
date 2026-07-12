# Release Packager

v0.9.0 adds a Foundry release packager.

## Run

```bat
Foundry\package_release.bat
```

## Output

```text
Foundry/Releases/KayocktheOS_<version>_<codename>_<timestamp>.zip
Foundry/Reports/last_release_package.json
```

## Excludes

- `.git`
- `node_modules`
- `dist`
- `out`
- `Backups`
- logs
- temp files
- large model files
