# Translation MCP Server — Progress Tracker & Next Steps

Last updated: 2026-04-21 (async bulk done, feedback→AI context done, MCP tools updated)

---

## Current Status vs. System Design

### Phase 1 — Foundation (system design §13)

| Task | Status | Notes |
|------|--------|-------|
| Project scaffold (pyproject, Dockerfile, docker-compose) | ✅ Done | All present |
| `src/config.py` — pydantic-settings | ✅ Done | v2 — `DB_URL`, `OPENAI_API_KEY`, `APP_ENV`, `LOG_LEVEL`, `AUTO_CREATE_DB`, `DEFAULT_AI_PROVIDER` |
| `src/utils/logger.py` — structlog (JSON prod / pretty dev) | ✅ Done | Request middleware in `main.py` |
| `src/db/session.py` — async engine + guarded startup | ✅ Done | `AUTO_CREATE_DB` guard, `maybe_create_database_if_missing()` |
| `src/db/models.py` — all 7 tables | ✅ Done | markets, market_locales, translations, translation_versions, audit_logs, feedback_corrections, promotions |
| `src/db/seed.py` — 20 markets + locales | ✅ Done | Seeded on startup |
| Alembic skeleton | ✅ Done | `alembic/env.py` + `alembic/versions/` present; migration not yet generated |
| `src/main.py` — FastAPI + health + middleware + startup | ✅ Done | |
| Alembic `revision --autogenerate` + `upgrade head` | ⏳ Not run | Tables created via `create_all` on startup |

---

### Phase 2 — Core CRUD (system design §13)

| Task | Status | Notes |
|------|--------|-------|
| `src/api/schemas.py` — all Pydantic models | ✅ Done | Add, Bulk, Update, Approve, Reject, List, Response |
| `POST /api/v1/translations` — create single | ✅ Done | Multi-locale, propagate_markets, AI generation |
| `POST /api/v1/translations/bulk` — create bulk (207) | ✅ Done | Batch DB (~7 RT for 50 keys), batch AI persist |
| `POST /api/v1/translations/bulk/async` — async bulk (202) | ✅ Done | DB-only insert → 202 + `batch_id`; AI runs in BackgroundTask |
| `GET /api/v1/translations/batch/{batch_id}/status` — batch poll | ✅ Done | Returns pending/completed/failed counts + per-item statuses |
| `GET /api/v1/translations` — list/filter | ✅ Done | Filter by market, locale, environment; grouped by key |
| `PUT /api/v1/translations/{id}` — update | ✅ Done | Partial-update, version++, audit log, feedback correction |
| `POST /api/v1/translations/{id}/approve` | ✅ Done | Stamps APPROVED, version + audit |
| `POST /api/v1/translations/{id}/reject` | ✅ Done | Stamps REJECTED, optional corrected_value → FeedbackCorrection |
| `FeedbackCorrection` capture in update + reject | ✅ Done | Fires when AI-generated translation is corrected by human |
| Feedback → AI context (`feedback_service.py`) | ✅ Done | Corrections injected as few-shot examples into AI system prompt at all 3 call sites |
| Bulk DB batch optimization (3 phases) | ✅ Done | Pre-fetch markets/locales, batch uniqueness check, `add_all` + flush |
| Timing logs on bulk flow | ✅ Done | `bulk_db_create_timing`, `bulk_ai_call_timing`, `ai_bulk_persist_completed` |
| `src/services/lifecycle_engine.py` | ❌ Not started | State machine: CREATED→AI_GENERATED→REVIEW_PENDING→APPROVED→PROMOTED |
| `GET /api/v1/translations/{key}` | ❌ Not started | |
| `GET /api/v1/markets` | ❌ Not started | |

---

### Phase 3 — AI Agent (system design §13)

| Task | Status | Notes |
|------|--------|-------|
| Ollama integration (gemma3:4b) | ✅ Done | `src/ai/ollama_client.py` — JSON extraction + fallback |
| OpenAI async wrapper | ✅ Done | `src/ai/openai_client.py` |
| Translation agent pipeline | ✅ Done | `src/ai/agent.py` — single + bulk, chunked, normalized |
| Unified system prompt (single + bulk) | ✅ Done | `src/ai/prompts.py` — TRANSLATION_SYSTEM_PROMPT |
| Feedback context injection | ✅ Done | `feedback_context` param on both agent functions; appended to system prompt when corrections exist |
| `src/ai/confidence.py` — confidence scoring | ❌ Not started | |
| `src/ai/metrics.py` — AI call telemetry | ❌ Not started | |
| `suggest_translation` tool + endpoint | ❌ Not started | |
| Wire AI into lifecycle | ❌ Not started | Requires lifecycle engine |

---

### Phase 4 — Multi-Market, Validation & Promotion

| Task | Status |
|------|--------|
| `src/services/sync_engine.py` | ❌ Not started |
| `src/services/validation_engine.py` | ❌ Not started |
| `src/services/promotion_engine.py` | ❌ Not started |
| `GET /api/v1/translations/{key}/history` | ❌ Not started |
| `POST /api/v1/translations/sync` | ❌ Not started |
| `POST /api/v1/translations/validate` | ❌ Not started |
| `POST /api/v1/translations/promote` | ❌ Not started |

---

### Phases 5–7 (Analytics, IDE Config, Hardening)

Not yet started.

---

### MCP Server (next milestone)

| Task | Status | Notes |
|------|--------|-------|
| Install MCP Python SDK `mcp==1.27.0` | ✅ Done | Added to `requirements.txt` |
| Rewrite `src/mcp/server.py` — FastMCP + logging + `ping` + stdio | ✅ Done | |
| `src/mcp/tools/__init__.py` — imports tools package | ✅ Done | |
| `src/mcp/tools/translation_tools.py` — translation tools registered incrementally | ✅ Done | See below |
| `get_translations` tool | ✅ Done | Wraps `list_translations` |
| `add_translation` tool | ✅ Done | Wraps `create_translation` |
| `add_translations_bulk` tool | ✅ Done | Wraps `create_translations_bulk` (sync, 207) |
| `add_translations_bulk_async` tool | ✅ Done | Returns `batch_id` immediately; AI runs in background |
| `get_batch_status` tool | ✅ Done | Returns live pending/completed/failed for a batch |
| `update_translation` tool | ✅ Done | Wraps `update_translation` (alias required) — registered |
| `approve_translation` tool | ✅ Done | Wraps `approve_translation` (alias required) — registered |
| `reject_translation` tool | ✅ Done | Wraps `reject_translation` (alias required) — registered |
| IDE config (`mcp_client/mcp_client_setup.json`) | ✅ Done | Windsurf stdio transport — in active use |

---

## What Exists in `src/` Right Now

```
src/
├── main.py                        ✅ FastAPI + health + middleware + startup
├── config.py                      ✅ pydantic-settings v2
├── db/
│   ├── models.py                  ✅ 7 tables
│   ├── session.py                 ✅ async engine + auto-create helper
│   └── seed.py                    ✅ 20 markets + locales
├── api/
│   ├── router.py                  ✅ registers api/translations router
│   ├── schemas.py                 ✅ All schemas (Add, Bulk, Update, Approve, Reject, List)
│   └── translations.py            ✅ 8 endpoints (POST, POST/bulk, POST/bulk/async, GET/batch/status, GET, PUT, POST/approve, POST/reject)
├── services/
│   ├── translation_service.py     ✅ All service fns + async bulk + batch status + timing logs
│   └── feedback_service.py        ✅ get_recent_corrections, build_feedback_section, get_feedback_context
├── ai/
│   ├── agent.py                   ✅ single + bulk generation; feedback_context injected into system prompt
│   ├── ollama_client.py           ✅ JSON extraction + fallback
│   ├── openai_client.py           ✅ async wrapper
│   └── prompts.py                 ✅ unified system prompt (TRANSLATION_SYSTEM_PROMPT)
├── mcp/
│   ├── server.py                  ✅ FastMCP skeleton, logging, `ping` tool, stdio transport
│   └── tools/
│       ├── __init__.py            ✅ imports translation_tools
│       └── translation_tools.py   ✅ 9 tools: ping, get_translations, add_translation, add_translations_bulk, add_translations_bulk_async, get_batch_status, update_translation, approve_translation, reject_translation
└── utils/
    └── logger.py                  ✅ structlog
```

---

## Performance Benchmarks (Bulk Create)

| Keys | DB batch | AI call | AI persist | Total |
|------|----------|---------|------------|-------|
| 3 | 90 ms | 7,320 ms | 21 ms | 7,455 ms |
| 10 | 29 ms | 12,560 ms | 25 ms | 12,622 ms |

- DB + persist < 0.5% of total time
- AI (Ollama gemma3:4b) = ~99.5% — bottleneck is model inference speed

---

## MCP Tools — 1 Tool at a Time

### Design Rules

1. **Thin wrapper only** — tool calls the existing service function, zero duplicate logic
2. **Sync tool, async inside** — `def tool_name(...)` wraps async service via `asyncio.run(_run())`
3. **Alias imports** — when the tool name matches the service function name, alias the import to avoid recursion: `from services.translation_service import update_translation as svc_update_translation`
4. **Return dict** — `.model_dump()` on Pydantic result; errors as `{"error": str(exc)}`
5. **Verify after each tool** — `PYTHONPATH=src mcp dev src/mcp/server.py`, call in inspector, confirm → then move to next

### Tool ↔ API Mapping

| # | MCP Tool | Alias needed? | Wraps service fn | REST equivalent |
|---|----------|--------------|------------------|-----------------|
| — | `ping` | No | — | `GET /health` |
| 2 | `get_translations` | No | `list_translations` | `GET /translations` |
| 3 | `add_translation` | No | `create_translation` | `POST /translations` |
| 4 | `add_translations_bulk` | No | `create_translations_bulk` | `POST /translations/bulk` |
| 5 | `add_translations_bulk_async` | No | `create_translations_bulk_db_only` + `run_bulk_ai_generation` | `POST /translations/bulk/async` |
| 6 | `get_batch_status` | **Yes** → `svc_get_batch_status` | `get_batch_status` | `GET /translations/batch/{id}/status` |
| 7 | `update_translation` | **Yes** → `svc_update_translation` | `update_translation` | `PUT /translations/{id}` |
| 8 | `approve_translation` | **Yes** → `svc_approve_translation` | `approve_translation` | `POST /translations/{id}/approve` |
| 9 | `reject_translation` | **Yes** → `svc_reject_translation` | `reject_translation` | `POST /translations/{id}/reject` |

### Current File State

| File | Status |
|------|--------|
| `requirements.txt` | ✅ `mcp==1.27.0` |
| `src/mcp/server.py` | ✅ FastMCP, logging, `ping`, `mcp.run(transport="stdio")` |
| `src/mcp/tools/__init__.py` | ✅ imports `translation_tools` |
| `src/mcp/tools/translation_tools.py` | ✅ 9 tools registered (ping + 8 translation tools) |

---

### ✅ Step 1 — SDK + skeleton + `ping` (DONE)

`server.py` has: FastMCP instance, `LOG_FILE`/`logger`/`log()`, `ping` tool, `main()` with `mcp.run(transport="stdio")`.

**Verify:**
```bash
PYTHONPATH=src mcp dev src/mcp/server.py
# call ping → {"status": "ok"}
```

---

### ⏳ Step 2 — `get_translations` tool (CURRENT — implement this next)

Add to `src/mcp/tools/translation_tools.py`:

```python
import asyncio
import sys
import os
from typing import List, Optional

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(PROJ_ROOT, "src"))

from src.mcp.server import mcp, log
from db.session import get_session
from services.translation_service import list_translations


@mcp.tool()
def get_translations(
    market_code: Optional[str] = None,
    locale_code: Optional[str] = None,
    environment: str = "DEV",
) -> list:
    """List translations grouped by key for a market."""
    log(f"get_translations called market={market_code} locale={locale_code} env={environment}")

    async def _run():
        async for session in get_session():
            return await list_translations(
                session,
                market_code=market_code,
                locale_code=locale_code,
                environment=environment,
            )

    try:
        return asyncio.run(_run())
    except Exception as exc:
        log(f"get_translations_error: {exc}")
        return [{"error": str(exc)}]
```

**Verify:** call `get_translations(market_code="IN")` → same data as `GET /api/v1/translations?market_code=IN`.
Confirm → Step 3.

---

### ⏳ Step 3 — `add_translation` tool

Add to `translation_tools.py` (after `get_translations`):

```python
from api.schemas import AddTranslationRequest
from services.translation_service import create_translation


@mcp.tool()
def add_translation(
    key: str,
    market_code: str,
    default_text: str,
    context: str = "",
    locale_codes: Optional[List[str]] = None,
    environment: str = "DEV",
    propagate_markets: Optional[List[str]] = None,
) -> dict:
    """Create a translation key and trigger AI generation."""
    log(f"add_translation called key={key} market={market_code}")

    async def _run():
        async for session in get_session():
            payload = AddTranslationRequest(
                key=key, market_code=market_code, default_text=default_text,
                context=context, locale_codes=locale_codes,
                propagate_markets=propagate_markets or [],
            )
            result = await create_translation(session, payload)
            return result.model_dump()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        log(f"add_translation_error: {exc}")
        return {"error": str(exc)}
```

**Verify:** call tool → DB row created + AI triggered. Confirm → Step 4.

---

### ⏳ Step 4 — `add_translations_bulk` tool

```python
from api.schemas import BulkCreateRequest
from services.translation_service import create_translations_bulk


@mcp.tool()
def add_translations_bulk(translations: List[dict]) -> dict:
    """Bulk-create translations (max 50). Each item matches BulkTranslationItem fields."""
    log(f"add_translations_bulk called items={len(translations)}")

    async def _run():
        async for session in get_session():
            payload = BulkCreateRequest(translations=translations)
            result = await create_translations_bulk(session, payload)
            return result.model_dump()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        log(f"add_translations_bulk_error: {exc}")
        return {"error": str(exc)}
```

**Verify:** call with 2–3 items → result has `total_requested`, `total_created`. Confirm → Step 5.

---

### ✅ Step 5 — `update_translation` tool (DONE)

⚠️ **Alias required** — function name matches the service import. Registered and verified.

```python
from api.schemas import UpdateTranslationRequest
from services.translation_service import update_translation as svc_update_translation


@mcp.tool()
def update_translation(translation_id: int, updates: dict) -> dict:
    """Update a translation by ID. `updates` fields: value, status, context, performed_by, change_reason."""
    log(f"update_translation called id={translation_id}")

    async def _run():
        async for session in get_session():
            payload = UpdateTranslationRequest(**updates)
            result = await svc_update_translation(session, translation_id, payload)
            return result.model_dump()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        log(f"update_translation_error: {exc}")
        return {"error": str(exc)}
```

**Verify:** Confirmed — DB version increments and audit row written.

---

### ✅ Step 6 — `approve_translation` tool (DONE)

⚠️ **Alias required.** Registered and verified.

```python
from api.schemas import ApproveTranslationRequest
from services.translation_service import approve_translation as svc_approve_translation


@mcp.tool()
def approve_translation(
    translation_id: int,
    performed_by: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict:
    """Approve a translation by ID."""
    log(f"approve_translation called id={translation_id} by={performed_by}")

    async def _run():
        async for session in get_session():
            payload = ApproveTranslationRequest(performed_by=performed_by, reason=reason)
            result = await svc_approve_translation(session, translation_id, payload)
            return result.model_dump()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        log(f"approve_translation_error: {exc}")
        return {"error": str(exc)}
```

**Verify:** Confirmed — status set to `APPROVED` in DB.

---

### ✅ Step 7 — `reject_translation` tool (DONE)

⚠️ **Alias required.** Registered and verified.

```python
from api.schemas import RejectTranslationRequest
from services.translation_service import reject_translation as svc_reject_translation


@mcp.tool()
def reject_translation(
    translation_id: int,
    performed_by: Optional[str] = None,
    reason: Optional[str] = None,
    corrected_value: Optional[str] = None,
) -> dict:
    """Reject a translation by ID. Provide reason and/or corrected_value."""
    log(f"reject_translation called id={translation_id} by={performed_by}")

    async def _run():
        async for session in get_session():
            payload = RejectTranslationRequest(
                performed_by=performed_by, reason=reason, corrected_value=corrected_value
            )
            result = await svc_reject_translation(session, translation_id, payload)
            return result.model_dump()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        log(f"reject_translation_error: {exc}")
        return {"error": str(exc)}
```

**Verify:** Confirmed — status set to `REJECTED`; `feedback_corrections` written when provided.

Please verify the MCP tools via Windsurf.

---

### ✅ Step 8 — IDE Config (DONE)

`mcp_client/mcp_client_setup.json` is in active use with Windsurf:

```json
{
  "mcpServers": {
    "translation-mcp-server": {
      "command": "/Users/gaurav.siwach/Work/Gaurav/translation-mcp-server/.venv/bin/python",
      "args": ["/Users/gaurav.siwach/Work/Gaurav/translation-mcp-server/src/mcp/server.py"]
    }
  }
}
```

Windsurf rules: `mcp_client/.windsurfrules` — AI assistant scoped to MCP tools only.

**Verified:** All 9 tools listed in Windsurf MCP panel (ping + 8 translation tools).

---

## Upcoming

1. **Alembic migration** — autogenerate + `upgrade head` (needed for `batch_id` column on deployed DBs)
2. **Lifecycle engine** (`src/services/lifecycle_engine.py`) — guard rules on state transitions: `CREATED→AI_GENERATED→REVIEW_PENDING→APPROVED→PROMOTED`
3. **Concurrent update guard** — optimistic locking / version conflict detection on `PUT /translations/{id}`
4. **`GET /api/v1/translations/{key}`** — fetch single translation by key across all markets/locales
5. **`GET /api/v1/markets`** — list markets + locales
6. **`src/ai/confidence.py`** and **`src/ai/metrics.py`**
7. **Advanced MCP tools** — `sync_translation_across_markets`, `validate_translations`, `promote_translations`, `suggest_translation`
8. **Tests** — Smoke test: In progress; proper test suite: TODO
