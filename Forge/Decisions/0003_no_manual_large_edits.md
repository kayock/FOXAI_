# Decision 0003 - No Large Manual Edits

## Decision

KayocktheOS will avoid large indentation-sensitive manual edits.

## Reason

Manual placement errors are one of the easiest ways to break JavaScript, Python, and Electron projects.

## Standard

For significant changes, use one of:

- patch scripts
- complete replacement files
- small clearly-labeled edits
- Git commits with rollback
