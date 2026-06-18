"""Unified token resolution — single source of truth for both REST and MCP.

All token-to-payload and token-to-role resolution flows through here.
This ensures dev mock tokens, MSAL decoding, and fallback logic is
consistent across the REST API and MCP server.
"""
from __future__ import annotations

from auth.msal_auth import decode_token, extract_role
from auth.permissions import Role
from config import settings
from utils.logger import get_logger

logger = get_logger("token_resolver")

# Dev mock tokens (shared across REST and MCP)
DEV_TOKENS: dict[str, dict] = {
    "super-admin-test-token": {
        "preferred_username": "superadmin@test.com",
        "name": "Test SuperAdmin",
        "oid": "test-oid-001",
        "roles": ["SuperAdmin"],
    },
    "sustain-admin-test-token": {
        "preferred_username": "sustainadmin@test.com",
        "name": "Test SustainAdmin",
        "oid": "test-oid-002",
        "roles": ["SustainAdmin"],
    },
    "bu-admin-test-token": {
        "preferred_username": "buadmin@test.com",
        "name": "Test BUAdmin",
        "oid": "test-oid-003",
        "roles": ["BUAdmin"],
    },
    "cs-agent-test-token": {
        "preferred_username": "csagent@test.com",
        "name": "Test CustomerServiceAgent",
        "oid": "test-oid-004",
        "roles": ["CustomerServiceAgent"],
    },
    "sustain-user-test-token": {
        "preferred_username": "sustainuser@test.com",
        "name": "Test SustainUser",
        "oid": "test-oid-005",
        "roles": ["SustainUser"],
    },
    "bdr-supervisor-test-token": {
        "preferred_username": "bdrsupervisor@test.com",
        "name": "Test BDRSupervisor",
        "oid": "test-oid-006",
        "roles": ["BDRSupervisor"],
    },
    "bdr-test-token": {
        "preferred_username": "bdr@test.com",
        "name": "Test BDR",
        "oid": "test-oid-007",
        "roles": ["BDR"],
    },
}


def resolve_token(token: str) -> dict:
    """Resolve a Bearer token to a payload dict.

    Works for both dev mock tokens and real MSAL tokens.
    Used by both REST API dependencies and MCP middleware.

    Returns:
        Token payload dict with at least 'roles' and 'preferred_username' keys.

    Raises:
        Exception if token is invalid (not a dev token and MSAL decode fails).
    """
    # Dev mock tokens (only in development mode)
    if settings.ENV == "development" and token in DEV_TOKENS:
        logger.info("resolved_dev_token", token_prefix=token[:20])
        return DEV_TOKENS[token]

    # Real MSAL token (decode with or without verification based on config)
    payload = decode_token(token)
    logger.info("resolved_msal_token", user=payload.get("preferred_username", "unknown"))
    return payload


def resolve_role(token: str) -> Role:
    """Resolve a Bearer token directly to a Role enum.

    Returns Role.VIEWER on any failure (least privilege fallback).
    """
    try:
        payload = resolve_token(token)
        return extract_role(payload)
    except Exception as exc:
        logger.warning("token_resolution_failed", error=str(exc))
        return Role.VIEWER
