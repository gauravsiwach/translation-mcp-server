"""
Test suite for RBAC permissions module.
Tests the core permission and role definitions.
"""

import sys
from pathlib import Path

# Ensure src is in path (conftest does this but be explicit for clarity)
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import pytest
from auth.permissions import (
    Role,
    Permission,
    ROLE_PERMISSIONS,
    has_permission,
)


class TestRoles:
    """Test role enum and values."""
    
    def test_role_enum_exists(self):
        """Test that Role enum is defined."""
        assert Role is not None
        
    def test_role_super_admin_exists(self):
        """Test SuperAdmin role exists."""
        assert Role.SUPER_ADMIN in Role
        
    def test_role_bu_admin_exists(self):
        """Test BUAdmin role exists."""
        assert Role.BU_ADMIN in Role
        
    def test_role_viewer_exists(self):
        """Test BDR role exists."""
        assert Role.BDR in Role
        
    def test_role_values_are_strings(self):
        """Test that role values are strings."""
        assert isinstance(Role.SUPER_ADMIN.value, str)
        assert isinstance(Role.BU_ADMIN.value, str)
        assert isinstance(Role.BDR.value, str)


class TestPermissions:
    """Test permission enum and definitions."""
    
    def test_permission_enum_exists(self):
        """Test that Permission enum is defined."""
        assert Permission is not None
        
    def test_all_permissions_defined(self):
        """Test all required permissions are defined."""
        required_permissions = [
            'LIST_LANGUAGES',
            'LIST_TRANSLATIONS',
            'GET_TRANSLATION',
            'GET_BATCH_STATUS',
            'CREATE_TRANSLATION',
            'UPDATE_TRANSLATION',
            'AI_TRANSLATE',
            'APPROVE_TRANSLATION',
            'REJECT_TRANSLATION',
            'DELETE_TRANSLATION',
            'MANAGE_USERS',
        ]
        for perm_name in required_permissions:
            assert hasattr(Permission, perm_name), f"Permission {perm_name} not found"


class TestRolePermissionsMapping:
    """Test ROLE_PERMISSIONS mapping."""
    
    def test_role_permissions_mapping_exists(self):
        """Test that ROLE_PERMISSIONS mapping is defined."""
        assert ROLE_PERMISSIONS is not None
        assert isinstance(ROLE_PERMISSIONS, dict)
        
    def test_all_roles_in_mapping(self):
        """Test all roles are in ROLE_PERMISSIONS."""
        assert Role.SUPER_ADMIN in ROLE_PERMISSIONS
        assert Role.BU_ADMIN in ROLE_PERMISSIONS
        assert Role.BDR in ROLE_PERMISSIONS
        
    def test_super_admin_has_all_permissions(self):
        """Test SuperAdmin has all permissions."""
        super_admin_perms = ROLE_PERMISSIONS[Role.SUPER_ADMIN]
        all_permissions = set(Permission)
        # SuperAdmin should have all permissions
        assert super_admin_perms == all_permissions
        
    def test_bu_admin_permissions(self):
        """Test BUAdmin has appropriate permissions."""
        bu_admin_perms = ROLE_PERMISSIONS[Role.BU_ADMIN]
        # BUAdmin should have read and update permissions
        assert Permission.LIST_TRANSLATIONS in bu_admin_perms
        assert Permission.UPDATE_TRANSLATION in bu_admin_perms
        assert Permission.APPROVE_TRANSLATION in bu_admin_perms
        
    def test_viewer_read_only_permissions(self):
        """Test BDR has read-only permissions."""
        viewer_perms = ROLE_PERMISSIONS[Role.BDR]
        # BDR should have only read permissions
        assert Permission.LIST_TRANSLATIONS in viewer_perms
        assert Permission.GET_TRANSLATION in viewer_perms
        # BDR should NOT have write permissions
        assert Permission.CREATE_TRANSLATION not in viewer_perms
        assert Permission.UPDATE_TRANSLATION not in viewer_perms
        assert Permission.DELETE_TRANSLATION not in viewer_perms
        assert Permission.APPROVE_TRANSLATION not in viewer_perms
        assert Permission.REJECT_TRANSLATION not in viewer_perms
        
    def test_permission_values_are_sets(self):
        """Test that permission values are sets."""
        for role, perms in ROLE_PERMISSIONS.items():
            assert isinstance(perms, set), f"Permissions for {role} should be a set"


class TestHasPermissionFunction:
    """Test has_permission utility function."""
    
    def test_super_admin_all_permissions(self):
        """Test SuperAdmin has all permissions."""
        for perm in Permission:
            assert has_permission(Role.SUPER_ADMIN, perm) is True
            
    def test_viewer_has_read_permission(self):
        """Test BDR has read permission."""
        assert has_permission(Role.BDR, Permission.LIST_TRANSLATIONS) is True
        
    def test_viewer_lacks_create_permission(self):
        """Test BDR lacks create permission."""
        assert has_permission(Role.BDR, Permission.CREATE_TRANSLATION) is False
        
    def test_viewer_lacks_approve_permission(self):
        """Test BDR lacks approve permission."""
        assert has_permission(Role.BDR, Permission.APPROVE_TRANSLATION) is False
        
    def test_bu_admin_has_approve_permission(self):
        """Test BUAdmin has approve permission."""
        assert has_permission(Role.BU_ADMIN, Permission.APPROVE_TRANSLATION) is True
        
    def test_bu_admin_has_list_permissions(self):
        """Test BUAdmin has list permissions."""
        assert has_permission(Role.BU_ADMIN, Permission.LIST_TRANSLATIONS) is True
        
    def test_bu_admin_lacks_manage_users(self):
        """Test BUAdmin lacks user management permission."""
        assert has_permission(Role.BU_ADMIN, Permission.MANAGE_USERS) is False
        
    def test_function_with_invalid_permission(self):
        """Test has_permission handles invalid role gracefully."""
        # Invalid role gets read-only (fallback to _READ_PERMISSIONS)
        result = has_permission("invalid_role", Permission.LIST_TRANSLATIONS)
        assert result is True  # read-only access granted
        # But write permissions should be denied
        result = has_permission("invalid_role", Permission.CREATE_TRANSLATION)
        assert result is False

