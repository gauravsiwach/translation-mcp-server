"""Role and Permission definitions with mapping."""
from __future__ import annotations

from enum import Enum
from typing import Set


class Role(str, Enum):
    SUPER_ADMIN = "SuperAdmin"
    SUSTAIN_ADMIN = "SustainAdmin"
    BU_ADMIN = "BUAdmin"
    CUSTOMER_SERVICE_AGENT = "CustomerServiceAgent"
    SUSTAIN_USER = "SustainUser"
    BDR_SUPERVISOR = "BDRSupervisor"
    BDR = "BDR"


class Permission(str, Enum):
    # Read
    LIST_LANGUAGES = "list_languages"
    LIST_TRANSLATIONS = "list_translations"
    GET_TRANSLATION = "get_translation"
    GET_BATCH_STATUS = "get_batch_status"

    # Write
    CREATE_TRANSLATION = "create_translation"
    UPDATE_TRANSLATION = "update_translation"
    AI_TRANSLATE = "ai_translate"

    # Review
    APPROVE_TRANSLATION = "approve_translation"
    REJECT_TRANSLATION = "reject_translation"

    # Admin
    DELETE_TRANSLATION = "delete_translation"
    MANAGE_USERS = "manage_users"


# Read-only permissions (shared by all roles)
_READ_PERMISSIONS: Set[Permission] = {
    Permission.LIST_LANGUAGES,
    Permission.LIST_TRANSLATIONS,
    Permission.GET_TRANSLATION,
    Permission.GET_BATCH_STATUS,
}

# Write permissions (CRUD without delete)
_WRITE_PERMISSIONS: Set[Permission] = _READ_PERMISSIONS | {
    Permission.CREATE_TRANSLATION,
    Permission.UPDATE_TRANSLATION,
    Permission.AI_TRANSLATE,
    Permission.APPROVE_TRANSLATION,
    Permission.REJECT_TRANSLATION,
}

# Role → Permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    # Super Admin: full access (CRUD + Review + Delete + Manage)
    Role.SUPER_ADMIN: set(Permission),

    # Sustain Admin & BU Admin: CRUD + Review (no delete)
    Role.SUSTAIN_ADMIN: _WRITE_PERMISSIONS,
    Role.BU_ADMIN: _WRITE_PERMISSIONS,

    # All others: Read-only
    Role.CUSTOMER_SERVICE_AGENT: _READ_PERMISSIONS,
    Role.SUSTAIN_USER: _READ_PERMISSIONS,
    Role.BDR_SUPERVISOR: _READ_PERMISSIONS,
    Role.BDR: _READ_PERMISSIONS,
}


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, _READ_PERMISSIONS)
