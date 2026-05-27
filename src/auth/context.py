"""Unified request-scoped auth context for both REST API and MCP server.

Uses Python contextvars so the current user identity is available
anywhere in the async call chain without passing it explicitly.
Both REST API middleware and MCP SSE middleware set this context.
"""
from __future__ import annotations

from contextvars import ContextVar

from auth.permissions import Role

# Stores the authenticated role for the current request/tool call
_current_role: ContextVar[str] = ContextVar("_current_role", default="Viewer")
_current_email: ContextVar[str] = ContextVar("_current_email", default="anonymous")
_current_token: ContextVar[str] = ContextVar("_current_token", default="")


def set_auth_context(role: str, email: str = "anonymous", token: str = "") -> None:
    """Set auth context for the current request (called by middleware)."""
    _current_role.set(role)
    _current_email.set(email)
    _current_token.set(token)


def get_current_role() -> str:
    """Get the role string for the current request context."""
    return _current_role.get()


def get_current_email() -> str:
    """Get the email for the current request context."""
    return _current_email.get()


def get_auth_context() -> dict:
    """Get full auth context as a dict."""
    return {
        "role": _current_role.get(),
        "email": _current_email.get(),
    }

