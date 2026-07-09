# Department Specification

A department is a self-contained subsystem discovered by manifest.

Example departments:

- Engineering
- Science
- Academy
- Creative Studio
- Iron Library
- Repair Bay
- Security
- Communications
- Browser
- Novel Forge

## Required Files

Each department should eventually contain:

- manifest.yaml or manifest.json
- officer.py
- services.py
- health.py
- startup.py
- ui/
- docs/
- tests/

## Manifest Fields

- id
- name
- officer
- startup_priority
- depends_on
- provides
- requires
- health_check
- services
- tools
- ui_panels
- version

## Commissioning Rule

A department is not commissioned until:

- Manifest validates
- Dependencies are available
- Health check passes
- Tests pass
- Dependency Arbiter is clean
- FOXKernel can boot with it enabled
