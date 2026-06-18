"""FastAPI dependencies for authentication and authorization.

Uses unified token_resolver and auth context (shared with MCP server).
"""
from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.token_resolver import resolve_token, resolve_role, DEV_TOKENS
from auth.context import set_auth_context
from auth.permissions import Role, Permission, has_permission
from auth.msal_auth import extract_role

security = HTTPBearer()


class CurrentUser:
    """Represents the authenticated user extracted from the JWT token."""

    def __init__(self, payload: dict, role: Role):
        self.payload = payload
        self.role = role
        self.email = payload.get("preferred_username") or payload.get("email", "")
        self.name = payload.get("name", "")
        self.oid = payload.get("oid", "")  # Azure object ID

    def __repr__(self) -> str:
        return f"CurrentUser(email={self.email!r}, role={self.role.value})"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """Extract and validate user from Bearer token.

    Uses unified token_resolver (same logic as MCP middleware).
    """
    token = credentials.credentials

    try:
        payload = resolve_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = extract_role(payload)

    # Set unified auth context (so @require decorator also works in REST handlers)
    set_auth_context(
        role=role.value,
        email=payload.get("preferred_username", ""),
        token=token,
    )

    return CurrentUser(payload=payload, role=role)


def require_permission(permission: Permission) -> Callable:
    """Dependency factory: raises 403 if user lacks the required permission.

    Usage:
        @router.post("/translations")
        async def create(user: CurrentUser = Depends(require_permission(Permission.CREATE_TRANSLATION))):
            ...
    """

    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' lacks permission '{permission.value}'",
            )
        return user

    return _check
