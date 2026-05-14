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

## Quick Start

> For the full developer setup guide (venv, migrations, MCP server, DB UI, Ollama): see **[docs/HELP_COMMANDS.md](docs/HELP_COMMANDS.md)**

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
| `POST` | `/translations` | Create a single translation key; triggers AI generation for all locales |
| `POST` | `/translations/bulk` | Bulk-create up to 50 keys (best-effort, returns per-key results) |
| `GET` | `/translations` | List translations grouped by key; filter by `market_code`, `market_id`, `locale_code`, `environment` |
| `PUT` | `/translations/{id}` | Partially update a translation (value, context, status); increments version |
| `POST` | `/translations/{id}/approve` | Approve a translation; creates version and audit log entry |
| `POST` | `/translations/{id}/reject` | Reject with optional corrected value; stored for AI feedback loop |

Interactive docs available at `http://localhost:8000/docs` when the server is running.

---

## MCP Tools

Connect via the MCP server (`python -m src.mcp.server`) and use these tools in natural language:

| Tool | Description |
|---|---|
| `ping` | Health check — verify the MCP server is reachable |
| `get_translations` | Fetch translations for a market/locale/environment |
| `add_translation` | Create a single key and trigger AI generation |
| `add_translations_bulk` | Create up to 50 keys at once |
| `update_translation` | Edit an existing translation by ID |
| `approve_translation` | Approve a translation |
| `reject_translation` | Reject with an optional corrected value |
| `prepare_translations` | Prepare items for the MCP direct translation flow |
| `save_translations` | Persist translations directly from the MCP host AI |

### VS Code MCP configuration

Add this to your VS Code MCP settings (`mcp_client/mcp_client_setup.json` for reference):

```json
{
  "mcpServers": {
    "translation-mcp-server": {
      "type": "stdio",
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/path/to/translation-mcp-server",
      "env": {
        "DB_URL": "postgresql+asyncpg://...",
        "OPENAI_API_KEY": "sk-..."
      }
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

