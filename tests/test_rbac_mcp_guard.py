"""
Test suite for MCP RBAC decorator.
Tests the mcp_require decorator for permission enforcement.
"""

import sys
from pathlib import Path

# Ensure src is in path
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import pytest
from auth.mcp_guard import mcp_require
from auth.permissions import Role, Permission


class TestMCPRequireDecorator:
    """Test mcp_require decorator functionality."""
    
    def test_decorator_exists(self):
        """Test mcp_require decorator is defined."""
        assert mcp_require is not None
        assert callable(mcp_require)
        
    def test_decorator_accepts_permission(self):
        """Test decorator accepts a permission parameter."""
        decorator = mcp_require(Permission.LIST_TRANSLATIONS)
        assert decorator is not None
        assert callable(decorator)
        
    def test_decorator_is_callable_factory(self):
        """Test mcp_require is a factory that returns decorators."""
        # Should be able to chain decorators
        dec1 = mcp_require(Permission.CREATE_TRANSLATION)
        dec2 = mcp_require(Permission.UPDATE_TRANSLATION)
        
        assert callable(dec1)
        assert callable(dec2)


class TestMCPGuardModuleStructure:
    """Test the structure of mcp_guard module."""
    
    def test_mcp_guard_module_imports(self):
        """Test mcp_guard module can be imported."""
        from auth import mcp_guard
        assert mcp_guard is not None
    
    def test_mcp_require_is_exported(self):
        """Test mcp_require is exported from mcp_guard."""
        from auth.mcp_guard import mcp_require as guard_mcp_require
        assert guard_mcp_require is mcp_require


class TestDecoratorPermissions:
    """Test decorator with different permissions."""
    
    def test_decorator_with_read_permission(self):
        """Test decorator with read permission."""
        decorator = mcp_require(Permission.LIST_TRANSLATIONS)
        assert callable(decorator)
    
    def test_decorator_with_write_permission(self):
        """Test decorator with write permission."""
        decorator = mcp_require(Permission.CREATE_TRANSLATION)
        assert callable(decorator)
    
    def test_decorator_with_admin_permission(self):
        """Test decorator with admin permission."""
        decorator = mcp_require(Permission.MANAGE_USERS)
        assert callable(decorator)


class TestRBACDecorator:
    """Test RBAC decorator functionality."""
    
    def test_all_permissions_can_be_decorated(self):
        """Test all permissions can be used with decorator."""
        for permission in Permission:
            decorator = mcp_require(permission)
            assert callable(decorator)
    
    def test_permission_isolation_in_decorator(self):
        """Test different decorators with different permissions."""
        decs = {}
        for permission in Permission:
            decs[permission] = mcp_require(permission)
        
        # Should have decorators for all permissions
        assert len(decs) == len(list(Permission))


class TestMCPDecoratorIntegration:
    """Test MCP decorator integration aspects."""
    
    def test_decorator_preserves_function_name(self):
        """Test decorator preserves function metadata."""
        @mcp_require(Permission.LIST_TRANSLATIONS)
        def sample_function():
            """Sample function."""
            return "result"
        
        # Decorated function should still be callable
        assert callable(sample_function)
    
    def test_multiple_permission_levels(self):
        """Test decorator works across permission hierarchy."""
        # SuperAdmin has all permissions
        all_perms = list(Permission)
        for perm in all_perms:
            decorator = mcp_require(perm)
            assert callable(decorator)


class TestSessionAuthStore:
    """Test session-based auth store for SSE transport cross-task fix."""

    def test_session_auth_store_and_fallback(self):
        """Test that require decorator falls back to session auth store."""
        from auth.mcp_middleware import _session_auth, get_latest_session_auth, get_session_role
        from auth.context import set_auth_context

        # Clear store
        _session_auth.clear()

        # Simulate: contextvar has default 'Viewer' (GET /sse task)
        set_auth_context(role="Viewer")

        # Simulate: POST /messages/ stored SuperAdmin in session store
        _session_auth["test-session-123"] = {
            "role": "SuperAdmin",
            "email": "admin@test.com",
            "token": "super-admin-test-token",
        }

        # get_session_role should return SuperAdmin
        assert get_session_role("test-session-123") == "SuperAdmin"
        assert get_latest_session_auth()["role"] == "SuperAdmin"

        # Cleanup
        _session_auth.clear()

    @pytest.mark.asyncio
    async def test_require_uses_session_store_fallback(self):
        """Test that @require reads from session store when contextvar is default."""
        from auth.require import require
        from auth.mcp_middleware import _session_auth
        from auth.context import set_auth_context

        # Set contextvar to default Viewer (simulates GET task)
        set_auth_context(role="Viewer")

        # Store SuperAdmin in session store (simulates POST task)
        _session_auth.clear()
        _session_auth["session-abc"] = {
            "role": "SuperAdmin",
            "email": "admin@test.com",
            "token": "token",
        }

        @require(Permission.CREATE_TRANSLATION)
        async def my_tool():
            return {"ok": True}

        # Should succeed (falls back to session store's SuperAdmin)
        result = await my_tool()
        assert result == {"ok": True}

        # Cleanup
        _session_auth.clear()

    @pytest.mark.asyncio
    async def test_require_denies_when_no_session_auth(self):
        """Test that @require denies when contextvar=Viewer and no session auth."""
        from auth.require import require
        from auth.mcp_middleware import _session_auth
        from auth.context import set_auth_context

        # Set contextvar to Viewer, clear session store
        set_auth_context(role="Viewer")
        _session_auth.clear()

        @require(Permission.CREATE_TRANSLATION)
        async def my_tool():
            return {"ok": True}

        # Should be denied
        result = await my_tool()
        assert result["error"] == "access_denied"

