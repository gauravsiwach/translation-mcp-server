"""Role and Permission definitions with mapping."""
from __future__ import annotations

from enum import Enum
from typing import Set


class Role(str, Enum):
    SUPER_ADMIN = "SuperAdmin"
    BU_ADMIN = "BUAdmin"
    VIEWER = "Viewer"


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

    # Admin
    APPROVE_TRANSLATION = "approve_translation"
    REJECT_TRANSLATION = "reject_translation"
    DELETE_TRANSLATION = "delete_translation"
    MANAGE_USERS = "manage_users"


# Role → Permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),  # All permissions
    Role.BU_ADMIN: {
        Permission.LIST_LANGUAGES,
        Permission.LIST_TRANSLATIONS,
        Permission.GET_TRANSLATION,
        Permission.GET_BATCH_STATUS,
        Permission.UPDATE_TRANSLATION,
        Permission.APPROVE_TRANSLATION,
        Permission.REJECT_TRANSLATION,
    },
    Role.VIEWER: {
        Permission.LIST_LANGUAGES,
        Permission.LIST_TRANSLATIONS,
        Permission.GET_TRANSLATION,
        Permission.GET_BATCH_STATUS,
    },
}


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())
