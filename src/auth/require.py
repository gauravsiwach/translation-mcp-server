"""Unified permission enforcement — works for both REST API and MCP tools.

Provides:
  - @require(Permission.X) decorator (for MCP tools and any async function)
  - check_permission(Permission.X) function (imperative style)
  - AccessDeniedError exception

Both REST API and MCP server use this same module for permission checks.
"""
from __future__ import annotations

from typing import Callable, Any
from functools import wraps

from auth.permissions import Role, Permission, has_permission
from auth.context import get_current_role
from utils.logger import get_logger

logger = get_logger("rbac")


class AccessDeniedError(Exception):
    """Raised when a user lacks the required permission."""

    def __init__(self, role: str, permission: str):
        self.role = role
        self.permission = permission
        super().__init__(f"Role '{role}' lacks permission '{permission}'")


def check_permission(permission: Permission) -> str:
    """Check if the current context has the required permission.

    Returns the role string if allowed.
    Raises AccessDeniedError if denied.

    Usage (imperative style):
        role = check_permission(Permission.CREATE_TRANSLATION)
    """
    role_str = get_current_role()
    try:
        role = Role(role_str)
    except ValueError:
        role = Role.BDR

    if not has_permission(role, permission):
        logger.warning("access_denied", role=role.value, permission=permission.value)
        raise AccessDeniedError(role.value, permission.value)

    logger.info("access_allowed", role=role.value, permission=permission.value)
    return role.value


def require(permission: Permission):
    """Unified RBAC decorator for both MCP tools and REST helper functions.

    Reads role from the auth context (set by middleware).
    Falls back to explicit `user_role` kwarg for testing/stdio transport.

    Usage:
        @mcp.tool()
        @require(Permission.CREATE_TRANSLATION)
        async def create_translation(...) -> dict:
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Priority 1: explicit user_role kwarg (testing only)
            user_role_str = kwargs.pop("user_role", None)

            if user_role_str:
                try:
                    role = Role(user_role_str)
                except ValueError:
                    role = Role.BDR
            else:
                # Priority 2: session auth store (SSE transport — bridges GET/POST task boundary)
                role_str = None
                try:
                    from auth.mcp_middleware import get_latest_session_auth
                    session_auth = get_latest_session_auth()
                    if session_auth:
                        role_str = session_auth["role"]
                except ImportError:
                    pass

                # Priority 3: request-scoped contextvar
                if not role_str or role_str == "Viewer":
                    from auth.context import get_current_role
                    ctx_role = get_current_role()
                    if ctx_role != "Viewer":
                        role_str = ctx_role

                if not role_str:
                    role_str = "Viewer"

                try:
                    role = Role(role_str)
                except ValueError:
                    role = Role.BDR

            if not has_permission(role, permission):
                logger.warning("access_denied", func=func.__name__, role=role.value, permission=permission.value)
                return {
                    "error": "access_denied",
                    "message": f"Role '{role.value}' lacks permission '{permission.value}'",
                }

            logger.info("access_allowed", func=func.__name__, role=role.value, permission=permission.value)
            return await func(*args, **kwargs)

        return wrapper

    return decorator
