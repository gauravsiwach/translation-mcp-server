"""MSAL / Azure AD token validation."""
from __future__ import annotations

import jwt
from jwt import PyJWKClient
from functools import lru_cache

from config import settings
from auth.permissions import Role
from utils.logger import get_logger

logger = get_logger("msal_auth")


@lru_cache()
def _get_jwks_client() -> PyJWKClient:
    """Cache the JWKS client for token verification."""
    jwks_url = (
        f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/discovery/v2.0/keys"
    )
    return PyJWKClient(jwks_url)


def decode_token(token: str) -> dict:
    """Decode and validate an MSAL JWT token.

    In development mode without Azure credentials, decodes without verification.
    In production, fully validates signature, audience, and issuer.
    """
    # Dev mode: decode without validation if Azure credentials are missing
    if settings.ENV == "development" and (
        not settings.AZURE_TENANT_ID or not settings.AZURE_CLIENT_ID
    ):
        logger.warning("Decoding token WITHOUT signature verification (dev mode)")
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload

    # Production: full validation
    jwks_client = _get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.AZURE_CLIENT_ID,
        issuer=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/v2.0",
    )
    return payload


def extract_role(token_payload: dict) -> Role:
    """Extract the highest-privilege role from token claims.

    Azure AD puts roles in the 'roles' claim (App Roles).
    Falls back to Viewer if no recognized role is found.
    """
    roles = token_payload.get("roles", [])

    if Role.SUPER_ADMIN.value in roles:
        return Role.SUPER_ADMIN
    if Role.BU_ADMIN.value in roles:
        return Role.BU_ADMIN
    return Role.VIEWER
