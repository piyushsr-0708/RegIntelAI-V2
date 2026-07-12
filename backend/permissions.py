"""
permissions.py — RegIntel AI V2
Defines the full permission set and canonical role-permission mappings.
All permission checks flow through this module.
"""

# ─── Permission Catalog ─────────────────────────────────────────────────────────
class Perm:
    # Global
    WILDCARD = "*"

    # MAP permissions
    MAP_READ       = "map:read"
    MAP_WRITE      = "map:write"
    MAP_APPROVE    = "map:approve"
    MAP_DELETE     = "map:delete"

    # Assignment permissions
    ASSIGN_READ    = "assign:read"
    ASSIGN_WRITE   = "assign:write"
    ASSIGN_COMPLETE= "assign:complete"

    # Department permissions
    DEPT_READ      = "dept:read"
    DEPT_WRITE     = "dept:write"

    # User / role management
    USER_READ      = "user:read"
    USER_WRITE     = "user:write"

    # Audit log
    AUDIT_READ     = "audit:read"

    # Pipeline
    PIPELINE_READ  = "pipeline:read"
    PIPELINE_RUN   = "pipeline:run"

    # Evidence
    EVIDENCE_UPLOAD = "evidence:upload"
    EVIDENCE_READ   = "evidence:read"


# ─── Canonical Role → Permission Mapping ────────────────────────────────────────
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Super Admin": [Perm.WILDCARD],
    "Admin": [
        Perm.MAP_READ, Perm.MAP_WRITE, Perm.MAP_APPROVE, Perm.MAP_DELETE,
        Perm.ASSIGN_READ, Perm.ASSIGN_WRITE,
        Perm.DEPT_READ, Perm.DEPT_WRITE,
        Perm.USER_READ, Perm.USER_WRITE,
        Perm.AUDIT_READ,
        Perm.PIPELINE_READ, Perm.PIPELINE_RUN,
        Perm.EVIDENCE_READ,
    ],
    "Compliance Head": [
        Perm.MAP_READ, Perm.MAP_WRITE, Perm.MAP_APPROVE,
        Perm.ASSIGN_READ, Perm.ASSIGN_WRITE, Perm.ASSIGN_COMPLETE,
        Perm.DEPT_READ,
        Perm.AUDIT_READ,
        Perm.PIPELINE_READ,
        Perm.EVIDENCE_UPLOAD, Perm.EVIDENCE_READ,
    ],
    "Risk Head": [
        Perm.MAP_READ,
        Perm.ASSIGN_READ, Perm.ASSIGN_COMPLETE,
        Perm.DEPT_READ,
        Perm.PIPELINE_READ,
        Perm.EVIDENCE_UPLOAD, Perm.EVIDENCE_READ,
    ],
    "Audit Head": [
        Perm.MAP_READ,
        Perm.ASSIGN_READ,
        Perm.AUDIT_READ,
        Perm.PIPELINE_READ,
        Perm.EVIDENCE_READ,
    ],
    "IT Head": [
        Perm.MAP_READ,
        Perm.ASSIGN_READ, Perm.ASSIGN_COMPLETE,
        Perm.DEPT_READ,
        Perm.EVIDENCE_UPLOAD, Perm.EVIDENCE_READ,
    ],
    "Operations Head": [
        Perm.MAP_READ,
        Perm.ASSIGN_READ, Perm.ASSIGN_COMPLETE,
        Perm.DEPT_READ,
        Perm.EVIDENCE_UPLOAD, Perm.EVIDENCE_READ,
    ],
    "Viewer": [
        Perm.MAP_READ,
        Perm.ASSIGN_READ,
        Perm.DEPT_READ,
        Perm.PIPELINE_READ,
        Perm.EVIDENCE_READ,
    ],
}


def has_permission(role_permissions: list[str], required: str) -> bool:
    """Returns True if the role_permissions list grants the required permission."""
    if Perm.WILDCARD in role_permissions:
        return True
    return required in role_permissions
