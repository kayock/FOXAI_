# Charter 0002 — Core Launcher

## Version
0.0.2

## Purpose
Create the first real executable heart of KayocktheOS.

## Department Owner
Core System

## Reason
KayocktheOS should launch as an operating environment, not as a loose collection of scripts.

## Design Decision
Use a Python launcher behind a simple Windows batch file.

## Why
Python is readable, cross-platform, automation-friendly, and can later be packaged as a standalone executable.

## Success Criteria

- Reads manifest
- Reads Operator Profile
- Creates boot logs
- Verifies folders
- Detects local models
- Displays Bridge status
- Exits gracefully

## Operator Language Rule
Documentation says Operator. Runtime uses the nickname chosen by the Operator.
