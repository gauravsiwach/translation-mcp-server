# RBAC Implementation — Unified Architecture

## Overview

Role-Based Access Control (RBAC) is implemented with a **unified architecture** that shares the same auth logic across both the REST API and MCP Server.

```
                    ┌──────────────────────────────────┐
                    │     auth/token_resolver.py        │
                    │  (dev tokens + MSAL decode)       │
                    └──────────────┬───────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
    ┌─────────▼─────────┐  ┌──────▼──────────┐  ┌──────▼──────┐
    │ REST API           │  │ MCP SSE         │  │ Direct Call │
    │ (dependencies.py)  │  │(mcp_middleware) │  │ (testing)   │
    └─────────┬─────────┘  └──────┬──────────┘  └──────┬──────┘
              │                    │                     │
              └────────────────────┼────────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │      auth/context.py              │
                    │  (contextvars: role, email)       │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │      auth/require.py              │
                    │  @require(Permission.X)           │
                    │  check_permission(Permission.X)   │
                    └──────────────────────────────────┘
```

---

## Module Responsibilities

| Module | Purpose |
|--------|---------|
| `auth/permissions.py` | Role enum, Permission enum, ROLE_PERMISSIONS mapping, `has_permission()` |
| `auth/token_resolver.py` | Single source of truth for token → payload resolution (dev + MSAL) |
| `auth/context.py` | Request-scoped contextvars (`role`, `email`) shared by REST & MCP |
| `auth/require.py` | Unified `@require(Permission)` decorator + `check_permission()` |
| `auth/msal_auth.py` | MSAL JWT decode (with/without signature verification) |
| `auth/dependencies.py` | FastAPI-specific `Depends()` wrappers (uses token_resolver) |
| `auth/mcp_middleware.py` | ASGI middleware for MCP SSE (uses token_resolver) |
| `auth/mcp_guard.py` | Backward-compat re-export of `require` as `mcp_require` |

---

## Roles & Permissions

### Three Roles (Hierarchy: Super > BU > Viewer)

| Role | Value | Description |
|------|-------|-------------|
| `SUPER_ADMIN` | `"SuperAdmin"` | Full system access |
| `BU_ADMIN` | `"BUAdmin"` | Read + Update + Approve/Reject |
| `VIEWER` | `"Viewer"` | Read-only access |

### Permissions

| Permission | SuperAdmin | BUAdmin | Viewer |
|-----------|:---:|:---:|:---:|
| `LIST_LANGUAGES` | ✅ | ✅ | ✅ |
| `LIST_TRANSLATIONS` | ✅ | ✅ | ✅ |
| `GET_TRANSLATION` | ✅ | ✅ | ✅ |
| `GET_BATCH_STATUS` | ✅ | ✅ | ✅ |
| `CREATE_TRANSLATION` | ✅ | ❌ | ❌ |
| `UPDATE_TRANSLATION` | ✅ | ✅ | ❌ |
| `AI_TRANSLATE` | ✅ | ❌ | ❌ |
| `APPROVE_TRANSLATION` | ✅ | ✅ | ❌ |
| `REJECT_TRANSLATION` | ✅ | ✅ | ❌ |
| `DELETE_TRANSLATION` | ✅ | ❌ | ❌ |
| `MANAGE_USERS` | ✅ | ❌ | ❌ |

---

## Token Resolution Flow

```python
# auth/token_resolver.py — single source of truth

def resolve_token(token: str) -> dict:
    # 1. Dev mode: check mock tokens
    if ENV == "development" and token in DEV_TOKENS:
        return DEV_TOKENS[token]
    # 2. Real MSAL token: decode (with/without signature verification)
    return decode_token(token)
```

### Dev Mode (ENV=development)

| Token | Role | Email |
|-------|------|-------|
| `super-admin-test-token` | SuperAdmin | superadmin@test.com |
| `bu-admin-test-token` | BUAdmin | buadmin@test.com |
| `viewer-test-token` | Viewer | viewer@test.com |

### Production Mode (ENV=production)

- Requires `AZURE_TENANT_ID` and `AZURE_CLIENT_ID`
- Validates JWT signature via Azure AD JWKS endpoint
- Extracts roles from `roles` claim in token

### Dev Mode with Real MSAL Token (No Azure Creds)

- Set `ENV=development` with empty `AZURE_TENANT_ID` / `AZURE_CLIENT_ID`
- Token is decoded **without** signature verification
- Roles read directly from the `roles` claim
- ⚠️ **Never use in production** — anyone can forge a token

---

## How It Works

### REST API Flow

```
Client → HTTP Header (Authorization: Bearer <token>)
       → dependencies.py::get_current_user()
       → token_resolver.resolve_token(token) → payload
       → extract_role(payload) → Role
       → set_auth_context(role, email)
       → require_permission(Permission.X) → 403 or pass
```

### MCP Server Flow

```
Client → SSE Header (Authorization: Bearer <token>)
       → MCPAuthMiddleware.__call__()
       → token_resolver.resolve_token(token) → payload
       → resolve_role(token) → Role
       → set_auth_context(role, email)
       → @require(Permission.X) on tool → error dict or execute
```

### Key Insight

Both flows use the **exact same** `token_resolver.py` and `context.py`. The only difference is the entry point (FastAPI Depends vs ASGI Middleware).

---

## Usage Examples

### MCP Tool with RBAC

```python
from auth.require import require
from auth.permissions import Permission

@mcp.tool()
@require(Permission.CREATE_TRANSLATION)
async def create_translation(translations: List[dict]) -> dict:
    ...
```

### REST API Endpoint with RBAC

```python
from auth.dependencies import require_permission
from auth.permissions import Permission

@router.post("/translations")
async def create(user = Depends(require_permission(Permission.CREATE_TRANSLATION))):
    ...
```

### Imperative Permission Check

```python
from auth.require import check_permission, AccessDeniedError
from auth.permissions import Permission

try:
    check_permission(Permission.MANAGE_USERS)
except AccessDeniedError:
    return {"error": "not allowed"}
```

---

## Configuration

### .env

```env
# Environment (controls dev token + decode behavior)
ENV=development

# Azure AD (required for production, optional for dev)
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
```

| ENV | AZURE_CLIENT_ID | Behavior |
|-----|-----------------|----------|
| `development` | Empty | Dev tokens + MSAL decode without signature verification |
| `development` | Set | Dev tokens + full MSAL validation |
| `production` | Set | Full MSAL validation only (no dev tokens) |
| `production` | Empty | ❌ All tokens fail |

---

## Testing

### Run all RBAC tests

```bash
python -m pytest tests/test_rbac_permissions.py tests/test_rbac_dependencies.py tests/test_rbac_mcp_guard.py tests/test_rbac_integration.py -v
```

### Manual testing with curl (REST API)

```bash
# SuperAdmin — full access
curl -H "Authorization: Bearer super-admin-test-token" http://localhost:8000/api/v1/translations

# Viewer — denied on POST
curl -X POST -H "Authorization: Bearer viewer-test-token" http://localhost:8000/api/v1/translations
# → 403 "Role 'Viewer' lacks permission 'create_translation'"
```

### MCP client config with auth

```json
{
  "translation-mcp-server-sse": {
    "url": "http://localhost:8001/sse",
    "headers": {
      "Authorization": "Bearer super-admin-test-token"
    }
  }
}
```

---

## File Summary

```
src/auth/
├── __init__.py
├── permissions.py        # Role, Permission enums + ROLE_PERMISSIONS mapping
├── token_resolver.py     # Unified token → payload (dev tokens + MSAL)
├── context.py            # Request-scoped contextvars (role, email)
├── require.py            # @require() decorator + check_permission()
├── msal_auth.py          # JWT decode (with/without verification)
├── dependencies.py       # FastAPI Depends wrappers
├── mcp_middleware.py     # ASGI middleware for MCP SSE
└── mcp_guard.py          # Backward-compat alias for require
```
