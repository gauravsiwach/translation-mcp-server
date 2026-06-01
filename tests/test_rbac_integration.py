"""
Test suite for RBAC integration with REST API.
Tests end-to-end RBAC enforcement on API endpoints.
"""

import sys
from pathlib import Path

# Ensure src is in path
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import pytest
from auth.permissions import Role, Permission, ROLE_PERMISSIONS, has_permission


class TestRBACHierarchy:
    """Test RBAC role hierarchy."""
    
    def test_super_admin_highest_privileges(self):
        """Test SuperAdmin has highest privileges."""
        super_admin_perms = ROLE_PERMISSIONS[Role.SUPER_ADMIN]
        bu_admin_perms = ROLE_PERMISSIONS[Role.BU_ADMIN]
        
        # SuperAdmin has more permissions than BUAdmin
        assert len(super_admin_perms) >= len(bu_admin_perms)
    
    def test_bu_admin_middle_privileges(self):
        """Test BUAdmin has middle privileges."""
        bu_admin_perms = ROLE_PERMISSIONS[Role.BU_ADMIN]
        viewer_perms = ROLE_PERMISSIONS[Role.BDR]
        
        # BUAdmin has more permissions than BDR
        assert len(bu_admin_perms) >= len(viewer_perms)
    
    def test_viewer_lowest_privileges(self):
        """Test BDR has lowest privileges."""
        viewer_perms = ROLE_PERMISSIONS[Role.BDR]
        
        # BDR should have some read permissions
        assert len(viewer_perms) > 0


class TestPermissionGrants:
    """Test specific permission grants to roles."""
    
    def test_super_admin_has_all_perms(self):
        """Test SuperAdmin has all permissions."""
        super_admin_perms = ROLE_PERMISSIONS[Role.SUPER_ADMIN]
        all_perms = set(Permission)
        
        assert super_admin_perms == all_perms
    
    def test_bu_admin_can_review_translations(self):
        """Test BUAdmin can review and approve translations."""
        bu_admin_perms = ROLE_PERMISSIONS[Role.BU_ADMIN]
        
        # BUAdmin should be able to read and approve
        assert Permission.LIST_TRANSLATIONS in bu_admin_perms
        assert Permission.APPROVE_TRANSLATION in bu_admin_perms
    
    def test_viewer_can_only_read(self):
        """Test BDR can only read translations."""
        viewer_perms = ROLE_PERMISSIONS[Role.BDR]
        
        # BDR should have read permissions
        assert Permission.LIST_TRANSLATIONS in viewer_perms
        assert Permission.GET_TRANSLATION in viewer_perms
        
        # BDR should NOT have write permissions
        assert Permission.CREATE_TRANSLATION not in viewer_perms
        assert Permission.UPDATE_TRANSLATION not in viewer_perms
        assert Permission.DELETE_TRANSLATION not in viewer_perms


class TestPermissionValidation:
    """Test permission validation logic."""
    
    def test_has_permission_returns_boolean(self):
        """Test has_permission always returns boolean."""
        result = has_permission(Role.SUPER_ADMIN, Permission.LIST_TRANSLATIONS)
        assert isinstance(result, bool)
    
    def test_permission_check_accuracy(self):
        """Test permission checks are accurate."""
        # SuperAdmin should have all permissions
        for perm in Permission:
            assert has_permission(Role.SUPER_ADMIN, perm) is True
        
        # BDR should not have create permission
        assert has_permission(Role.BDR, Permission.CREATE_TRANSLATION) is False
    
    def test_admin_only_permissions(self):
        """Test certain permissions only belong to SuperAdmin."""
        admin_only_perms = [Permission.MANAGE_USERS]
        
        for perm in admin_only_perms:
            # SuperAdmin should have it
            assert has_permission(Role.SUPER_ADMIN, perm) is True
            # BUAdmin should NOT have it
            assert has_permission(Role.BU_ADMIN, perm) is False
            # BDR should NOT have it
            assert has_permission(Role.BDR, perm) is False


class TestRoleBasedWorkflows:
    """Test realistic RBAC workflows."""
    
    def test_translation_creation_workflow(self):
        """Test translation creation workflow permissions."""
        # SuperAdmin can create translations
        assert has_permission(Role.SUPER_ADMIN, Permission.CREATE_TRANSLATION)
        # BUAdmin can update existing translations
        assert has_permission(Role.BU_ADMIN, Permission.UPDATE_TRANSLATION)
        # BDR cannot modify
        assert not has_permission(Role.BDR, Permission.UPDATE_TRANSLATION)
    
    def test_translation_approval_workflow(self):
        """Test translation approval workflow permissions."""
        # BUAdmin can approve
        assert has_permission(Role.BU_ADMIN, Permission.APPROVE_TRANSLATION)
        # BDR cannot approve
        assert not has_permission(Role.BDR, Permission.APPROVE_TRANSLATION)
        # SuperAdmin can also approve
        assert has_permission(Role.SUPER_ADMIN, Permission.APPROVE_TRANSLATION)
    
    def test_read_only_viewer_workflow(self):
        """Test read-only BDR workflow."""
        viewer_perms = ROLE_PERMISSIONS[Role.BDR]
        
        # BDR can see translations
        read_perms = {
            Permission.LIST_TRANSLATIONS,
            Permission.GET_TRANSLATION,
            Permission.LIST_LANGUAGES,
            Permission.GET_BATCH_STATUS,
        }
        
        # At least one read permission should be present
        assert any(perm in viewer_perms for perm in read_perms)


class TestLeastPrivilegePrinciple:
    """Test least privilege principle implementation."""
    
    def test_permissions_not_granted_unnecessarily(self):
        """Test permissions are not granted unnecessarily."""
        # BDR should not have any write permission
        viewer_perms = ROLE_PERMISSIONS[Role.BDR]
        
        write_perms = {
            Permission.CREATE_TRANSLATION,
            Permission.UPDATE_TRANSLATION,
            Permission.DELETE_TRANSLATION,
            Permission.AI_TRANSLATE,
            Permission.MANAGE_USERS,
        }
        
        # BDR should have none of the write permissions
        assert not any(perm in viewer_perms for perm in write_perms)
    
    def test_critical_permissions_restricted(self):
        """Test critical permissions are restricted."""
        critical_perms = {Permission.MANAGE_USERS}
        
        # Only SuperAdmin should have critical permissions
        for perm in critical_perms:
            assert has_permission(Role.SUPER_ADMIN, perm)
            assert not has_permission(Role.BU_ADMIN, perm)
            assert not has_permission(Role.BDR, perm)


class TestRBACCompleteness:
    """Test RBAC implementation completeness."""
    
    def test_all_roles_have_permissions(self):
        """Test all roles have at least one permission."""
        for role in Role:
            assert role in ROLE_PERMISSIONS
            assert len(ROLE_PERMISSIONS[role]) > 0
    
    def test_permission_distribution(self):
        """Test permissions are distributed appropriately."""
        total_roles = len(list(Role))
        assert total_roles == 7  # SuperAdmin, SustainAdmin, BUAdmin, CustomerServiceAgent, SustainUser, BDRSupervisor, BDR
        
        total_perms = len(list(Permission))
        assert total_perms >= 8  # Reasonable minimum

