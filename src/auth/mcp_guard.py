"""RBAC decorator for MCP tool functions.

This module now delegates to the unified `auth.require` module.
Kept for backward compatibility — new code should import from auth.require.
"""
from auth.require import require as mcp_require  # noqa: F401
