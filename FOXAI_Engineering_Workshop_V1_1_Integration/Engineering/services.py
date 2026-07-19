from __future__ import annotations

SERVICES = [
    {
        "id": "engineering_workshop",
        "name": "Engineering Workshop",
        "status": "v1_foundation",
        "capabilities": [
            "classify_mission",
            "locate_live_source",
            "preserve_mission_state",
            "snapshot",
            "preview_exact_diff",
            "apply_approved_patch",
            "run_approved_validation",
            "rollback",
            "produce_evidence_receipt",
        ],
        "safety": {
            "read_only_default": True,
            "delete_supported": False,
            "rename_supported": False,
            "shell_commands_supported": False,
            "exact_plan_hash_approval": True,
            "rollback_on_validation_failure": True,
        },
    },
    {
        "id": "repair_bay",
        "name": "Repair Bay",
        "status": "foundation",
        "capabilities": [
            "diagnose",
            "propose_patch",
            "snapshot",
            "preview_diff",
            "apply_approved_patch",
            "verify",
            "rollback",
            "produce_receipt",
        ],
    },
    {
        "id": "build_verification",
        "name": "Build Verification",
        "status": "foundation",
        "capabilities": ["lint", "format", "typecheck", "run_approved_tests"],
    },
    {
        "id": "architecture_inspection",
        "name": "Architecture Inspection",
        "status": "foundation",
        "capabilities": ["import_graph", "boundary_rules", "live_source_discovery"],
    },
    {
        "id": "security_inspection",
        "name": "Security Inspection",
        "status": "foundation",
        "capabilities": ["dependency_audit", "sbom"],
    },
]
