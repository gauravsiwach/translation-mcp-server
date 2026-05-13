# Translation MCP Server — Implementation Plan

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Framework | FastAPI + MCP Python SDK |
| AI | OpenAI API (gpt-4o-mini, configurable) |
| Database | PostgreSQL — SQLAlchemy 2.0 async + Alembic |
| Transport | stdio (IDE) + SSE/REST (remote) |
| Logging | `structlog` — structured JSON logs, log level configurable via `LOG_LEVEL` env var |

---

## Out of Scope (for now)

- Admin MFE (b2b-profile-admin-ui)
- Pimcore migration / sync
- Authentication (OAuth2 planned for later)
- Figma deep integration (basic `screen_id` tagging only)
- b2b-portal CI/CD consumer integration

---

## Key Design Decisions

- **Uniqueness constraint**: `(key + market_id + locale_code + environment)` per row
- **Lifecycle state** lives on the translation row itself — no separate state table
- **Promotion** = delta upsert QA → PROD + JSONB snapshot stored in `promotions` table for rollback
- **Market groups** (LATAM_ES, ARABIC, etc.) defined in config file — not in DB
- **Feedback corrections** stored in DB now; full few-shot learning loop deferred to later
- **No auth** for now — clean internal service; OAuth2 integration planned later
- **Two logging layers**: structured app logs (`structlog`) for operations/debugging + audit logs (DB table) for business events

---

## Phase 1 — Project Scaffold

> Bundle: config files + folder structure in one task, then sequential DB setup.

| # | Task | Outcome |
|---|------|---------|
| 1 | `pyproject.toml` + `docker-compose.yml` + `Dockerfile` + folder structure | Installable, runnable project skeleton |
| 2 | `src/config.py` — pydantic-settings (`DB_URL`, `OPENAI_API_KEY`, `APP_ENV`, `LOG_LEVEL`) | Central config |
| 3 | `src/utils/logger.py` — `structlog` setup: JSON output in prod, pretty in dev, log level from `LOG_LEVEL`, request context binding | Structured logging ready for all layers |
| 4 | `src/db/session.py` — async SQLAlchemy engine + session factory | DB connectivity |
| 5 | `src/db/models.py` — all 7 tables (see Data Model section below) | Schema defined in code |
| 6 | `src/db/seed.py` — 20 markets + locales seeded from b2b-portal `CountrySiteId` mapping | Market data ready |
| 7 | Alembic init + first migration | DB schema created via migration |
| 8 | `src/main.py` — FastAPI app + `GET /health` + request/response logging middleware + MCP server skeleton | Running service, all requests logged |

---

## Phase 2 — Core CRUD

| # | Task | MCP Tool | REST Endpoint |
|---|------|----------|---------------|
| 9 | `src/api/schemas.py` — all Pydantic request/response models | — | — |
| 10 | `src/services/translation_service.py` — DB CRUD operations (log every write with key + market context) | — | — |
| 11 | `src/services/lifecycle_engine.py` — state machine transitions (log every state change: old → new state per key+market) | — | — |
| 12 | Add translation | `add_translation` | `POST /api/v1/translations` |
| 13 | Get translation | `get_translation` | `GET /api/v1/translations/{key}` |
| 14 | Update translation | `update_translation` | `PUT /api/v1/translations/{id}` |
| 15 | List markets + locales | — | `GET /api/v1/markets` |
| 16 | List/search translations | — | `GET /api/v1/translations` (filter: market, locale, status, env) |

---

## Phase 3 — AI Layer

| # | Task |
|---|------|
| 17 | `src/ai/openai_client.py` — async OpenAI wrapper (rate limit handling, retries; log every call with model, token usage, latency, and errors). Keep `src/ai/client.py` as a local/mock helper for dev. |
| 18 | `src/ai/ollama_client.py` — local-model client (Ollama) to support on-prem/local LLMs; same surface as `openai_client.py`. |
| 19 | `src/ai/prompts.py` — market + locale-aware system prompt templates (tone, cultural nuance per market) and reusable prompt builders. |
| 20 | `src/ai/agent.py` — orchestration pipeline: provider selection (OpenAI vs Ollama), context assembly, prompt build, call client, post-process, compute confidence, and return structured result. |
| 21 | `src/ai/confidence.py` — confidence scoring (length ratio, untranslated detection, similarity boost, heuristics). |
| 22 | `src/ai/feedback.py` — store feedback corrections to `feedback_corrections` table and expose helper to fetch few-shot examples for prompts. |
| 23 | `src/ai/metrics.py` — ai_call telemetry: model, latency, token usage, errors (for observability and alerting). |
| 24 | Wire AI into `add_translation` — auto-generate all locales on creation → status: `AI_GENERATED` → `REVIEW_PENDING` (dev: in-process task; prod: queue-based worker). |
| 25 | `suggest_translation` MCP tool + `POST /api/v1/translations/suggest` — return suggestion, confidence, and similar keys. |

---

## Phase 4 — Multi-Market, Validation & Promotion

| # | Task | MCP Tool | REST Endpoint |
|---|------|----------|---------------|
| 24 | `src/services/sync_engine.py` — cross-market copy + re-generate AI | — | — |
| 25 | Cross-market sync | `sync_translation_across_markets` | `POST /api/v1/translations/sync` |
| 26 | `src/services/validation_engine.py` — missing + inconsistent key checks | — | — |
| 27 | Validate translations | `validate_translations` | `POST /api/v1/translations/validate` |
| 28 | `src/services/promotion_engine.py` — delta compute + snapshot + upsert + rollback (log delta summary: keys promoted, unchanged, new) | — | — |
| 29 | Promote translations | `promote_translations` | `POST /api/v1/translations/promote` |
| 30 | Version history | — | `GET /api/v1/translations/{key}/history` |
| 31 | Approve translation | — | `POST /api/v1/translations/{id}/approve` |
| 32 | Reject translation | — | `POST /api/v1/translations/{id}/reject` |

---

## Phase 5 — Analytics

| # | Task | REST Endpoint |
|---|------|---------------|
| 33 | Most edited translations per market | `GET /api/v1/analytics/most-edited` |
| 34 | Low-confidence translation hotspots | `GET /api/v1/analytics/hotspots` |
| 35 | Translation coverage per market | `GET /api/v1/analytics/coverage` |

---

## Phase 6 — IDE Config + Docs

| # | Task |
|---|------|
| 36 | `.cursor/mcp.json` + `.windsurf/mcp_config.json` — stdio transport config for IDE integration |
| 37 | `README.md` — local setup guide (Docker, env vars, Alembic, IDE MCP config, log level config) |

---

## Phase 7 — Hardening (Security + Observability)

> Non-blocking — add after core functionality is stable.

| # | Task | Why |
|---|------|-----|
| 38 | CORS middleware — configurable `ALLOWED_ORIGINS` via env var | Required before any UI or CI/CD consumer calls this API |
| 39 | Global exception handler — catch all unhandled errors, return structured JSON error response, log at `ERROR` level | Prevents stack trace leakage in production responses |
| 40 | Request/Correlation ID middleware — attach `X-Request-ID` to every request + response, bind to log context | Enables log tracing across services and MCP tool calls |
| 41 | Deep health check — `GET /health` verifies DB connectivity + OpenAI reachability, returns per-dependency status | Needed for load balancer and alerting integration |
| 42 | Rate limiting on AI endpoints (`/suggest`, `POST /translations`) — `slowapi` or equivalent | Prevents runaway OpenAI costs from bulk/accidental calls |
| 43 | Replace in-process AI tasks (`asyncio.create_task`) with durable job queue (Redis + RQ/Celery) for production; add worker process, retry/backoff, and dead-letter handling | Ensures reliability, retries, and scale for AI generation |
| 44 | AI telemetry & quotas — `src/ai/metrics.py` + alerting for high error/latency/token usage; configure quotas to prevent cost spikes | Observability and cost control for AI calls |

---

## Logging Strategy

### Two Layers

| Layer | Tool | Purpose |
|-------|------|---------|
| **Application logs** | `structlog` (JSON) | Request tracing, AI call latency, state transitions, errors |
| **Audit logs** | `audit_logs` DB table | Business events: who approved, promoted, rejected, synced |

### What Gets Logged

| Location | Events |
|----------|---------|
| FastAPI middleware | Every request: method, path, status code, duration |
| `lifecycle_engine.py` | Every state transition: key + market + old state → new state |
| `openai_client.py` | Every AI call: model, token usage, latency, errors |
| `ai/agent.py` | Confidence score per translation + low-confidence flags |
| `promotion_engine.py` | Promotion summary: keys promoted, unchanged, new, rollbacks |
| All services | Errors at `ERROR` level with full context |

### Log Levels by Environment

| `APP_ENV` | Log Level | Format |
|-----------|-----------|--------|
| `development` | `DEBUG` | Human-readable (pretty) |
| `production` | `INFO` | JSON (machine-readable) |

---

## Data Model — 7 Tables

```
markets               → code, name, site_id, is_active
market_locales        → market_id, locale_code, is_default
translations          → key, market_id, locale_code, value, default_text, context,
                        screen_id, figma_node_id, status, environment, confidence,
                        version, created_by, updated_by
translation_versions  → translation_id, version, value, status, changed_by, change_reason
audit_logs            → action, entity_type, entity_id, market_code, details (JSONB), performed_by
feedback_corrections  → translation_id, key, market_code, locale_code,
                        ai_original_value, corrected_value, corrected_by
promotions            → market_code, env_from, env_to, keys_promoted,
                        status, promoted_by, snapshot (JSONB)
```

---

## Translation Lifecycle State Machine

```
CREATED → AI_GENERATED → REVIEW_PENDING → APPROVED → PROMOTED
                               ↓                         ↓
                           REJECTED              ROLLED_BACK
                               ↓
                        (re-generate)
```

State tracked per: **key + market + locale + environment**

---

## MCP Tools Summary (8 tools)

| Tool | Purpose |
|------|---------|
| `add_translation` | Register key for a market, auto-generate AI translations |
| `get_translation` | Fetch translation(s) for key + market (optionally per locale) |
| `update_translation` | Update value, creates new version + audit log |
| `sync_translation_across_markets` | Copy from source market, re-generate for target markets |
| `validate_translations` | Report missing + inconsistent keys per market |
| `preview_translation` | Return translation + Figma screen context metadata |
| `promote_translations` | Delta promote APPROVED translations QA → PROD with rollback |
| `suggest_translation` | AI suggestion with confidence score + similar key references |

---

## Folder Structure

```
translation-mcp-server/
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── session.py
│   │   └── seed.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── add_translation.py
│   │       ├── get_translation.py
│   │       ├── update_translation.py
│   │       ├── sync_markets.py
│   │       ├── validate.py
│   │       ├── promote.py
│   │       ├── suggest.py
│   │       └── preview.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   └── deps.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── translation_service.py
│   │   ├── lifecycle_engine.py
│   │   ├── promotion_engine.py
│   │   ├── validation_engine.py
│   │   └── sync_engine.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── openai_client.py
│   │   ├── prompts.py
│   │   ├── confidence.py
│   │   └── feedback.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── market_config.py
├── tests/
│   ├── __init__.py
│   ├── test_mcp_tools.py
│   ├── test_api.py
│   ├── test_ai_agent.py
│   └── test_lifecycle.py
├── .cursor/
│   └── mcp.json
└── .windsurf/
    └── mcp_config.json
```

---

## Market Seed Data (20 markets)

| Market Code | Name | site_id | Locales |
|-------------|------|---------|---------|
| IN | India | 34 | en, hi_IND |
| MX | Mexico | 21 | es_MX, en |
| SA | Saudi Arabia | 29 | ar_SA, en |
| EG | Egypt | 30 | ar_EG, en |
| TR | Turkey | 14 | tr, en |
| ES | Spain | 13 | es, en, zh |
| BR | Brazil | 11 | pt_BR, en |
| PL | Poland | 25 | pl_PL, en |
| TH | Thailand | 24 | th_TH, en |
| RO | Romania | 18 | ro, en |
| RU | Russia | 15 | ru, en |
| PT | Portugal | 16 | pt, en |
| CO | Colombia | 7 | es, en |
| CL | Chile | 22 | es_CL, en |
| AR | Argentina | 28 | es_AR, en |
| DO | Dominican Republic | 20 | es_DO, en |
| PE | Peru | 32 | es_PE, en |
| EC | Ecuador | 33 | es_EC, en |
| NZ | New Zealand | 17 | en |
| MXW | Mexico Wholesaler | 26 | es_MX, en |
