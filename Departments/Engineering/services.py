from __future__ import annotations

SERVICES = [
    {
        "id": "repair_bay",
        "name": "Repair Bay",
        "status": "foundation",
        "capabilities": ["diagnose", "propose_patch", "verify"],
    },
    {
        "id": "build_verification",
        "name": "Build Verification",
        "status": "foundation",
        "capabilities": ["lint", "format", "typecheck"],
    },
    {
        "id": "architecture_inspection",
        "name": "Architecture Inspection",
        "status": "foundation",
        "capabilities": ["import_graph", "boundary_rules"],
    },
    {
        "id": "security_inspection",
        "name": "Security Inspection",
        "status": "foundation",
        "capabilities": ["dependency_audit", "sbom"],
    },
]
