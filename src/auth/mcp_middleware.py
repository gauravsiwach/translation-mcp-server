"""ASGI middleware for MCP SSE — extracts Bearer token and sets auth context.

Uses unified token_resolver and auth context (shared with REST API).
Stores auth per session_id to bridge the GET/POST task boundary in SSE transport.
"""
from __future__ import annotations

from urllib.parse import parse_qs
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse

from auth.context import set_auth_context
from auth.token_resolver import resolve_token, resolve_role
from utils.logger import get_logger

logger = get_logger("mcp_auth_middleware")

# Session-based auth store: bridges GET /sse and POST /messages/ tasks.
# Key: session_id, Value: {"role": str, "email": str, "token": str}
_session_auth: dict[str, dict] = {}


def get_session_role(session_id: str | None = None) -> str | None:
    """Look up stored role for a session. Used by require decorator as fallback."""
    if session_id and session_id in _session_auth:
        return _session_auth[session_id]["role"]
    # Fallback: return the most recently stored auth (single-client scenario)
    if _session_auth:
        return next(reversed(_session_auth.values()))["role"]
    return None


def get_latest_session_auth() -> dict | None:
    """Get the most recent session auth (for single-client fallback)."""
    if _session_auth:
        return next(reversed(_session_auth.values()))
    return None


class MCPAuthMiddleware:
    """Extracts Authorization header from SSE connection and sets auth context.

    Works with both dev tokens (ENV=development) and real MSAL tokens.
    Rejects requests without a valid Authorization header (401).
    Stores auth per session_id so tool execution can access it.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    def _extract_session_id(self, scope: Scope) -> str | None:
        """Extract session_id from query string (POST /messages/?session_id=X)."""
        qs = scope.get("query_string", b"").decode()
        params = parse_qs(qs)
        session_ids = params.get("session_id", [])
        return session_ids[0] if session_ids else None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()

            if not auth_header.lower().startswith("bearer "):
                logger.warning("request_rejected", reason="missing Authorization header")
                response = JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "message": "Authorization header required. Use 'Bearer <token>'"},
                )
                await response(scope, receive, send)
                return

            token = auth_header[7:]
            try:
                payload = resolve_token(token)
                role = resolve_role(token)
                email = payload.get("preferred_username", "anonymous")

                # Set contextvar (works for same-task tool execution)
                set_auth_context(role=role.value, email=email, token=token)

                # Store auth per session_id (bridges GET/POST task boundary)
                session_id = self._extract_session_id(scope)
                if session_id:
                    _session_auth[session_id] = {
                        "role": role.value,
                        "email": email,
                        "token": token,
                    }
                else:
                    # GET /sse — store with a placeholder key
                    _session_auth["__latest__"] = {
                        "role": role.value,
                        "email": email,
                        "token": token,
                    }

                logger.info("auth_context_set", role=role.value, session_id=session_id)
            except Exception as exc:
                logger.warning("token_resolution_failed", error=str(exc))
                response = JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "message": f"Invalid token: {exc}"},
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
