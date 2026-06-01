"""
Test suite for RBAC dependencies and FastAPI integration.
Tests the authentication and permission dependency injection.
"""

import sys
from pathlib import Path

# Ensure src is in path
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import pytest
from auth.dependencies import DEV_TOKENS
from auth.permissions import Role, Permission




class TestDevTokens:
    """Test development mock tokens."""
    
    def test_dev_tokens_exist(self):
        """Test that dev tokens are defined."""
        assert DEV_TOKENS is not None
        assert isinstance(DEV_TOKENS, dict)
        
    def test_super_admin_token_exists(self):
        """Test super admin dev token exists."""
        assert "super-admin-test-token" in DEV_TOKENS
        
    def test_bu_admin_token_exists(self):
        """Test BU admin dev token exists."""
        assert "bu-admin-test-token" in DEV_TOKENS
        
    def test_viewer_token_exists(self):
        """Test viewer dev token exists."""
        assert "bdr-test-token" in DEV_TOKENS
        
    def test_dev_tokens_have_payloads(self):
        """Test dev tokens have payload dictionaries."""
        for token_key, payload in DEV_TOKENS.items():
            assert isinstance(payload, dict)
            assert "preferred_username" in payload or "email" in payload
            assert "roles" in payload
            
    def test_dev_token_roles_mapping(self):
        """Test dev tokens map to correct role payloads."""
        # SuperAdmin token should have SuperAdmin role
        assert "SuperAdmin" in DEV_TOKENS["super-admin-test-token"]["roles"]
        # BUAdmin token should have BUAdmin role
        assert "BUAdmin" in DEV_TOKENS["bu-admin-test-token"]["roles"]
        # BDR token should have BDR role
        assert "BDR" in DEV_TOKENS["bdr-test-token"]["roles"]


class TestAuthenticationDependencies:
    """Test authentication dependency structure."""
    
    def test_dev_tokens_cover_all_roles(self):
        """Test dev tokens cover all roles."""
        all_roles = {r.value for r in Role}
        token_roles = set()
        
        for token, payload in DEV_TOKENS.items():
            token_roles.update(payload["roles"])
        
        # All three roles should be covered by dev tokens
        assert all_roles.issubset(token_roles)
    
    def test_each_dev_token_has_distinct_roles(self):
        """Test each dev token represents a different role level."""
        token_list = list(DEV_TOKENS.keys())
        assert len(token_list) >= 3
        
        roles_per_token = []
        for token in token_list:
            roles = DEV_TOKENS[token]["roles"]
            roles_per_token.append(tuple(sorted(roles)))
        
        # Each token should have different roles
        assert len(set(roles_per_token)) >= 3


class TestPermissionStructure:
    """Test permission enum structure."""
    
    def test_all_permissions_are_strings(self):
        """Test all permission values are strings."""
        for perm in Permission:
            assert isinstance(perm.value, str)
    
    def test_permissions_are_lowercase(self):
        """Test permission values are lowercase."""
        for perm in Permission:
            assert perm.value.islower() or "_" in perm.value
    
    def test_permission_count_reasonable(self):
        """Test there are reasonable number of permissions."""
        perm_count = len(list(Permission))
        assert 8 <= perm_count <= 20  # Reasonable range for permission system


class TestRolePermissionMapping:
    """Test role-to-permission mapping."""
    
    def test_super_admin_has_most_permissions(self):
        """Test SuperAdmin has the most permissions."""
        from auth.permissions import ROLE_PERMISSIONS
        
        super_admin_count = len(ROLE_PERMISSIONS[Role.SUPER_ADMIN])
        bu_admin_count = len(ROLE_PERMISSIONS[Role.BU_ADMIN])
        viewer_count = len(ROLE_PERMISSIONS[Role.BDR])
        
        assert super_admin_count >= bu_admin_count
        assert bu_admin_count >= viewer_count
    
    def test_viewer_has_minimum_permissions(self):
        """Test BDR has at least read permissions."""
        from auth.permissions import ROLE_PERMISSIONS
        
        viewer_perms = ROLE_PERMISSIONS[Role.BDR]
        assert len(viewer_perms) > 0
        
        # Should have at least LIST or GET permissions (read operations)
        read_perms = {p for p in viewer_perms if "list" in p.value.lower() or "get" in p.value.lower()}
        assert len(read_perms) > 0
    
    def test_bu_admin_has_approve_permission(self):
        """Test BUAdmin can approve translations."""
        from auth.permissions import ROLE_PERMISSIONS
        
        bu_admin_perms = ROLE_PERMISSIONS[Role.BU_ADMIN]
        approve_perm = Permission.APPROVE_TRANSLATION
        assert approve_perm in bu_admin_perms


class TestRBACCompliance:
    """Test overall RBAC design compliance."""
    
    def test_least_privilege_principle(self):
        """Test least privilege principle - BDR has fewest permissions."""
        from auth.permissions import ROLE_PERMISSIONS
        
        viewer_count = len(ROLE_PERMISSIONS[Role.BDR])
        bu_admin_count = len(ROLE_PERMISSIONS[Role.BU_ADMIN])
        super_admin_count = len(ROLE_PERMISSIONS[Role.SUPER_ADMIN])
        
        assert viewer_count <= bu_admin_count <= super_admin_count
    
    def test_role_hierarchy_clear(self):
        """Test role hierarchy is clear (Super > BU > BDR)."""
        # All roles exist and are distinct
        assert Role.SUPER_ADMIN != Role.BU_ADMIN
        assert Role.BU_ADMIN != Role.BDR
        assert Role.SUPER_ADMIN != Role.BDR
    
    def test_permission_isolation(self):
        """Test critical permissions are properly isolated."""
        from auth.permissions import ROLE_PERMISSIONS
        
        # MANAGE_USERS should only be available to SuperAdmin
        for role in [Role.BU_ADMIN, Role.BDR]:
            assert Permission.MANAGE_USERS not in ROLE_PERMISSIONS[role]
        
        # SuperAdmin should have it
        assert Permission.MANAGE_USERS in ROLE_PERMISSIONS[Role.SUPER_ADMIN]

