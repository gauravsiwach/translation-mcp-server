# Translation MCP Server

> **POC Status** — This is a proof-of-concept. It demonstrates the full workflow for AI-powered translation management with dual REST API and MCP interfaces.

---

## The Problem

Managing UI localizations across **17+ markets** (40+ planned) is expensive and error-prone:

- Every market has its own locale **plus** English — that's 35+ translation files today, 80+ tomorrow
- A single feature requires: adding keys → translating each locale → reviewing → promoting across environments (DEV → QA → PROD)
- This is done manually, market by market, key by key, through a shared admin board
- Coordination overhead grows linearly with each new market and each new feature
- There is no tooling to help reviewers, PMs, or market managers participate without deep technical context

---

## The Solution

This service is a **centralized translation backend** that tackles the problem on three levels:

| Layer | What it does |
|---|---|
| **AI Generation** | Automatically translates keys into all market locales on creation — no manual translation needed for first draft |
| **REST API** | Drop-in integration for the existing admin board — approve, reject, bulk-create, promote from the UI you already use |
| **MCP Interface** | Anyone (dev, PM, market manager) can manage translations through natural language in their IDE or AI assistant — no deep tech required |

---

## Key Features

- **AI-powered translation** — OpenAI (default) or Ollama (local) generate translations for all locales on key creation
- **Dual interface** — REST API for system integrations + MCP tools for conversational, natural-language management
- **Multi-market & multi-locale** — market-isolated with per-market locale configuration; supports `propagate_markets` to fan out a single key across markets at once
- **Environment isolation** — DEV / QA / PROD environments are separate; translations are explicitly promoted between them
- **Translation lifecycle** — `CREATED → AI_GENERATED → REVIEW_PENDING → APPROVED → PROMOTED`
- **Bulk operations** — create up to 50 keys in a single request
- **Full audit trail** — every state change is versioned and logged with who changed it and when
- **Confidence scoring** — AI translations are scored on length ratio, similarity to approved translations, and market context
- **Feedback loop** — human corrections are stored and surfaced as few-shot examples in future AI prompts

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Clients                               │
│                                                              │
│  IDE / AI Assistant          Admin Board / CI-CD             │
│  (VS Code, Claude, etc.)     (existing web app)              │
└────────────┬─────────────────────────┬───────────────────────┘
             │ MCP (stdio)             │ HTTP / REST
             ▼                         ▼
┌────────────────────┐     ┌──────────────────────┐
│   MCP Server       │     │   REST API           │
│   src/mcp/         │     │   src/api/           │
│   (FastMCP)        │     │   (FastAPI)          │
└────────────┬───────┘     └──────────┬───────────┘
             │                        │
             └──────────┬─────────────┘
                        ▼
             ┌──────────────────────┐
             │  Translation Service │
             │  src/services/       │
             └──────┬───────┬───────┘
                    │       │
          ┌─────────▼──┐  ┌─▼──────────────┐
          │ PostgreSQL  │  │  AI Provider   │
          │ (async ORM) │  │  OpenAI/Ollama │
          └─────────────┘  └────────────────┘
```

---

## Tech Stack

| Component | Technology |
|---|---|
| API framework | FastAPI + Uvicorn |
| Database | PostgreSQL via SQLAlchemy 2.0 (async) + asyncpg |
| Migrations | Alembic |
| AI providers | OpenAI API, Ollama (local) |
| MCP protocol | `mcp` SDK (FastMCP) |
| Validation | Pydantic v2 |
| Logging | Structlog (structured JSON) |
| Runtime | Python 3.11 |

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- OpenAI API key (or Ollama for local AI)
- Virtual environment (venv)

---

## Quick Start

> For the full developer setup guide (venv, migrations, MCP server, DB UI, Ollama): see **[docs/HELP_COMMANDS.md](docs/HELP_COMMANDS.md)**

---

## Authentication & RBAC

The server uses **Azure AD (MSAL) Bearer tokens** for authentication. Both the REST API and MCP SSE server require an `Authorization: Bearer <token>` header.

### Roles & Permissions

| Role | Create | Update | AI Translate | Approve/Reject | Delete |
|------|:------:|:------:|:------------:|:--------------:|:------:|
| **Super Admin** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Sustain Admin** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **BU Admin** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Customer Service Agent** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Sustain User** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **BDR Supervisor** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **BDR** | ❌ | ❌ | ❌ | ❌ | ❌ |

> All roles have read access (list languages, list/get translations, batch status).

### Dev Test Tokens (ENV=development)

In development mode, the following static tokens can be used without Azure AD:

| Token | Role |
|-------|------|
| `super-admin-test-token` | SuperAdmin |
| `sustain-admin-test-token` | SustainAdmin |
| `bu-admin-test-token` | BUAdmin |
| `cs-agent-test-token` | CustomerServiceAgent |
| `sustain-user-test-token` | SustainUser |
| `bdr-supervisor-test-token` | BDRSupervisor |
| `bdr-test-token` | BDR |

### REST API — Sample Requests with Token

```bash
# List languages (any role)
curl -H "Authorization: Bearer super-admin-test-token" \
  http://localhost:8000/api/v1/languages

# Create translation (requires SuperAdmin/SustainAdmin/BUAdmin)
curl -X POST \
  -H "Authorization: Bearer super-admin-test-token" \
  -H "Content-Type: application/json" \
  -d '{"translations": [{"label": "btn.submit", "language_code": "en", "translation": "Submit", "type": "ui"}]}' \
  http://localhost:8000/api/v1/translations/bulk

# AI Translate (requires SuperAdmin/SustainAdmin/BUAdmin)
curl -X POST \
  -H "Authorization: Bearer bu-admin-test-token" \
  -H "Content-Type: application/json" \
  -d '{"translations": [{"label": "btn.submit", "source_text": "Submit", "target_language_codes": ["hi", "ta"], "type": "ui"}]}' \
  http://localhost:8000/api/v1/translations/ai-translate

# Approve translation (requires SuperAdmin/SustainAdmin/BUAdmin)
curl -X POST \
  -H "Authorization: Bearer sustain-admin-test-token" \
  -H "Content-Type: application/json" \
  -d '{"performed_by": "admin@company.com"}' \
  http://localhost:8000/api/v1/translations/1/approve

# Read-only user attempt to create (will get 403)
curl -X POST \
  -H "Authorization: Bearer bdr-test-token" \
  -H "Content-Type: application/json" \
  -d '{"translations": [{"label": "test", "language_code": "en", "translation": "Test"}]}' \
  http://localhost:8000/api/v1/translations/bulk
# Response: {"detail": "Role 'BDR' lacks permission 'create_translation'"}
```

### MCP Server (SSE) — Client Configuration

```jsonc
// Add to your MCP client settings (VS Code, Claude Desktop, Cursor, etc.)
{
  "mcpServers": {
    "translation-mcp-server-sse": {
      "url": "http://localhost:8001/sse",
      "headers": {
        "Authorization": "Bearer super-admin-test-token"
      }
    }
  }
}
```

**Test with different roles:**

```jsonc
// BU Admin — can create, update, approve/reject but NOT delete
{
  "mcpServers": {
    "translation-mcp-server-sse": {
      "url": "http://localhost:8001/sse",
      "headers": {
        "Authorization": "Bearer bu-admin-test-token"
      }
    }
  }
}

// BDR — read-only, will get access_denied on create/update
{
  "mcpServers": {
    "translation-mcp-server-sse": {
      "url": "http://localhost:8001/sse",
      "headers": {
        "Authorization": "Bearer bdr-test-token"
      }
    }
  }
}
```

### Using Real MSAL Tokens

For production/staging with Azure AD:

```bash
# 1. Get token from Azure AD (client credentials or auth code flow)
TOKEN=$(curl -s -X POST \
  "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id={client_id}&scope={api_scope}/.default&client_secret={client_secret}&grant_type=client_credentials" \
  | jq -r '.access_token')

# 2. Use the token with REST API
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/translations

# 3. Or configure MCP client with the token
```

> The token's `roles` claim (Azure AD App Roles) determines the user's permission level. The server maps the first matching role from the token to the internal role hierarchy.

---

### Option 1 — Docker Compose (recommended)

Starts PostgreSQL and the API server together.

```bash
cp .env.example .env        # fill in OPENAI_API_KEY and DB_URL
docker-compose up --build
```

API will be available at `http://localhost:8000`.

### Option 2 — Local virtual environment

```bash
./scripts/bootstrap.sh
source .venv/bin/activate

# Run database migrations
alembic upgrade head

# Start API server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3 — MCP server (for IDE integration)

```bash
source .venv/bin/activate
python -m src.mcp.server
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_URL` | — | PostgreSQL connection string, e.g. `postgresql+asyncpg://user:pass@localhost/db` |
| `OPENAI_API_KEY` | — | API key for OpenAI (required if using the default provider) |
| `DEFAULT_AI_PROVIDER` | `openai` | AI provider: `openai` or `ollama` |
| `AI_MODEL` | — | Override the model name (e.g. `gpt-4o`, `qwen2.5`) |
| `APP_ENV` | `local` | Deployment environment label |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `AUTO_CREATE_DB` | `false` | Auto-create the database on startup |
| `MCP_TRANSLATION_MODE` | `api` | MCP backend mode: `api` (REST) or `tool` (direct service) |
| `OPENAI_TIMEOUT` | — | Timeout (seconds) for OpenAI requests |

---

## REST API Endpoints

Base path: `/api/v1`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/languages` | List all available locales |
| `GET` | `/translations` | List translations with optional filters (locale, type, label) |
| `POST` | `/translations` | Create a single translation (upsert) |
| `POST` | `/translations/bulk` | Bulk-create translations (up to 50 items) |
| `PUT` | `/translations/{id}` | Update a translation by ID |
| `PUT` | `/translations` | Update a translation by label + language_code |
| `POST` | `/ai-translate` | AI translate labels across target locales (sync/async) |
| `GET` | `/batch/{batch_id}/status` | Check async batch status |
| `POST` | `/translations/upload` | Upload CSV/JSON file for bulk import |
| `GET` | `/translations/download` | Download all translations as CSV or JSON |

Interactive docs available at `http://localhost:8000/docs` when the server is running.

---

## MCP Tools

The MCP server provides two workflow modes for managing translations:

### Mode A: AI API Mode
Uses REST API endpoints via `ai_translate` tool. AI generates translations and saves them automatically.

**Available capabilities:**
1. List languages
2. View translations
3. Add translations (AI generates for selected locales, sync ≤10 items, async >10 items)
4. Check batch status
5. Update translation

### Mode B: MCP Tool Mode
Uses IDE AI for translation generation. User reviews translations before saving via `create_translation` tool.

**Available capabilities:**
1. List languages
2. View translations
3. Add translations (IDE AI translates, user reviews, then saves)
4. Update translation
5. Process translation file (attach CSV/JSON, batch-by-batch review and save)
6. Download translations (export as CSV or JSON)

### MCP Tools Reference

| Tool | Description | Available In |
|---|---|---|
| `ping` | Health check — verify the MCP server is reachable | Both modes |
| `list_languages` | List all available locales (en, hi_IND, etc.) | Both modes |
| `get_translations` | Fetch translations with optional filters (locale, type, label) | Both modes |
| `create_translation` | Bulk upsert translations (array of {label, language_code, translation, type}) | Tool mode |
| `update_translation` | Update a translation by ID or by label + language_code | Both modes |
| `ai_translate` | AI translate labels across target locales (sync ≤10 items, async >10 items) | API mode |
| `get_batch_status` | Check async AI translation batch status | API mode |
| `download_translations` | Download all translations as CSV (default) or JSON | Tool mode |

### MCP Server Configuration

The MCP server runs on SSE transport at `http://localhost:8002/sse` by default.

For Windsurf/VS Code integration, see `mcp_client/.windsurfrules` for the complete workflow guide.

**Example configuration:**

```json
{
  "mcpServers": {
    "translation-mcp-server-sse": {
      "url": "http://localhost:8002/sse"
    }
  }
}
```

---

## Database Schema

| Table | Purpose |
|---|---|
| `markets` | Registry of markets (code, name, site_id, active flag) |
| `market_locales` | Locales supported per market; one is marked `is_default` |
| `translations` | Core store — unique per `(key, market_id, locale_code, environment)` |
| `translation_versions` | Full version history: every change stored with who made it and when |
| `audit_logs` | Immutable action log for all operations |
| `feedback_corrections` | Human corrections linked to AI output; feed back into future prompts |
| `promotion` | Snapshots of environment promotions (DEV → QA → PROD) |

---

## Translation Lifecycle

```
CREATED ──► AI_GENERATED ──► REVIEW_PENDING ──► APPROVED ──► PROMOTED
                                    │
                                    └──► REJECTED (with correction stored)
```

1. Key is created via API or MCP tool
2. AI generates translations for all market locales in the background
3. Status moves to `REVIEW_PENDING` — ready for human review
4. Reviewer approves or rejects (rejection stores a correction for the feedback loop)
5. Approved translations are promoted to the next environment

---

## Project Structure

```
src/
├── main.py                  # FastAPI app entry point, startup lifecycle
├── config.py                # Pydantic Settings — all env vars in one place
├── ai/
│   ├── agent.py             # AI translation pipeline orchestrator
│   ├── openai_client.py     # OpenAI provider
│   ├── ollama_client.py     # Ollama (local) provider
│   └── prompts.py           # Prompt templates
├── api/
│   ├── router.py            # Route registration
│   ├── translations.py      # REST endpoint handlers
│   └── schemas/             # Request/response Pydantic models
├── db/
│   ├── models.py            # SQLAlchemy ORM models
│   ├── session.py           # Async session factory
│   └── seed.py              # Default seed data (markets, locales)
├── mcp/
│   ├── server.py            # FastMCP server entry point
│   └── tools/
│       └── translation_tools.py  # All MCP tool definitions
├── services/
│   └── translation_service.py    # Core business logic
└── utils/
    └── logger.py            # Structlog setup
```

---

## Database Migrations

```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Apply all pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

---

## Roadmap

- [x] Core translation CRUD with AI generation (OpenAI + Ollama)
- [x] Multi-market, multi-locale, multi-environment support
- [x] Approval / rejection workflow with audit trail
- [x] Bulk create endpoint
- [x] MCP server with full tool coverage
- [x] Version history and feedback corrections
- [ ] Admin board integration (REST API ready — UI wiring pending)
- [ ] Environment promotion endpoint (`/promote`)
- [ ] Webhook / event publishing on status changes
- [ ] Rate limiting and API key auth
- [ ] Market onboarding flow (self-service locale configuration)
- [ ] Analytics dashboard (key coverage per market/locale)

