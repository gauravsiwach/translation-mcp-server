# AI Translation Workflow Agent with Market-Aware MCP Server — System Design

Comprehensive system design for an AI-powered, market-aware translation workflow agent using Python/FastAPI, local LLMs (Qwen/Gemma), PostgreSQL, and MCP protocol — spanning a new standalone backend service, the existing `b2b-profile-admin-ui` admin portal, and consumer-side integration in `b2b-portal`.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DEVELOPER IDE                            │
│  (Windsurf/Cursor/VS Code with MCP client)                     │
│  ┌──────────────────────────────────┐                           │
│  │  MCP Client (stdio/SSE)         │                           │
│  │  • add_translation()            │                           │
│  │  • get_translation()            │                           │
│  │  • validate_translations()      │                           │
│  │  • suggest_translation()        │                           │
│  │  • promote_translations()       │                           │
│  └──────────┬───────────────────────┘                           │
└─────────────┼───────────────────────────────────────────────────┘
              │ MCP Protocol (stdio / SSE)
              ▼
┌─────────────────────────────────────────────────────────────────┐
│         TRANSLATION MCP SERVER (New Standalone Service)         │
│         Python + FastAPI + MCP SDK                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │  MCP Tool     │  │  REST API    │  │  AI Translation Agent │ │
│  │  Layer        │  │  Layer       │  │  (Qwen / Gemma local) │ │
│  │  (stdio/SSE)  │  │  (FastAPI)   │  │  via Ollama           │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘ │
│         │                 │                       │             │
│  ┌──────▼─────────────────▼───────────────────────▼───────────┐ │
│  │              Core Translation Service                      │ │
│  │  • Lifecycle Engine (CREATED→AI_GENERATED→...→PROMOTED)    │ │
│  │  • Market-Aware Key Registry                               │ │
│  │  • Cross-Market Sync Engine                                │ │
│  │  • Validation Engine                                       │ │
│  │  • Environment Promotion Engine                            │ │
│  │  • Feedback Learning Loop                                  │ │
│  └──────────────────────┬─────────────────────────────────────┘ │
│                         │                                       │
│  ┌──────────────────────▼─────────────────────────────────────┐ │
│  │              PostgreSQL                                    │ │
│  │  • translations, translation_versions, audit_logs          │ │
│  │  • markets, market_locales, lifecycle_states               │ │
│  │  • ai_suggestions, feedback_corrections                    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
              │ REST API
              ▼
┌───────────────────────────┐    ┌────────────────────────────────┐
│  b2b-profile-admin-ui     │    │  b2b-portal (this repo)        │
│  (React Admin Portal)     │    │  (Consumer: Web + Mobile)      │
│  • Translation dashboard  │    │  • Fetches translations via    │
│  • Visual UI preview      │    │    existing Pimcore API or     │
│  • Review & approve flow  │    │    new MCP-backed REST API     │
│  • Missing key alerts     │    │  • Build-time validation       │
└───────────────────────────┘    └────────────────────────────────┘
```

### Three Repositories

| Repo | Role | Changes |
|------|------|---------|
| **translation-mcp-server** (new) | MCP server + AI agent + REST API + DB | Full new service |
| **b2b-profile-admin-ui** (existing) | Admin portal UI for translation management | New microfrontend pages |
| **b2b-portal** (this repo) | Consumer of translations | Build-time validation, optional MCP client |

---

## 2. MCP Server Design

### 2.1 Technology Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.11+ |
| Framework | FastAPI (REST) + `mcp` Python SDK (MCP protocol) |
| AI Models | Qwen2.5 / Gemma 2 via **Ollama** (local, offline) |
| Database | PostgreSQL (existing) |
| ORM | SQLAlchemy 2.0 + Alembic (migrations) |
| Async | asyncio + asyncpg |
| Transport | stdio (IDE integration) + SSE (remote) |

### 2.2 MCP Tool Definitions

All tools take `market` as a first-class parameter.

#### `add_translation`
```python
@mcp.tool()
async def add_translation(
    key: str,              # e.g. "checkout.pay_now"
    default_text: str,     # e.g. "Pay Now"
    market: str,           # e.g. "IN", "MX", "SA"
    locales: list[str] = [],  # override; defaults to all market locales
    context: str = "",     # e.g. "CTA button on checkout page"
    screen_id: str = "",   # e.g. "Checkout" (Figma screen mapping)
    propagate_markets: list[str] = []  # optionally propagate to other markets
) -> dict:
```
**Behavior:**
1. Register key in `translations` table for the given market
2. Auto-resolve locales from `market_locales` if not specified
3. Trigger AI translation generation for each locale
4. Set lifecycle state → `AI_GENERATED` → `REVIEW_PENDING`
5. If `propagate_markets` specified, create entries for those markets too
6. If `screen_id` provided, store Figma context mapping
7. Check for similar existing keys across markets and suggest reuse

#### `update_translation`
```python
@mcp.tool()
async def update_translation(
    key: str,
    market: str,
    locale: str,
    new_value: str,
    reason: str = ""       # audit log reason
) -> dict:
```
**Behavior:** Creates new version, updates value, logs audit entry.

#### `get_translation`
```python
@mcp.tool()
async def get_translation(
    key: str,
    market: str,
    locale: str = ""       # if empty, returns all locales for this market
) -> dict:
```

#### `sync_translation_across_markets`
```python
@mcp.tool()
async def sync_translation_across_markets(
    key: str,
    source_market: str,
    target_markets: list[str]
) -> dict:
```
**Behavior:** Copies translations from source market, re-generates AI translations for target market locales, marks as `REVIEW_PENDING`.

#### `validate_translations`
```python
@mcp.tool()
async def validate_translations(
    market: str = "",          # if empty, validates all markets
    check_missing: bool = True,
    check_inconsistent: bool = True
) -> dict:
```
**Returns:** `{ missing_keys: [...], inconsistent_keys: [...], coverage_pct: ... }`

#### `preview_translation`
```python
@mcp.tool()
async def preview_translation(
    key: str,
    market: str,
    screen_id: str = ""
) -> dict:
```
**Returns:** Translation values + Figma screen context (node ID, screenshot URL if available).

#### `promote_translations`
```python
@mcp.tool()
async def promote_translations(
    market: str,
    env_from: str,       # "QA"
    env_to: str,         # "PROD"
    keys: list[str] = [] # if empty, promotes all APPROVED keys
) -> dict:
```
**Behavior:** Computes delta, promotes only `APPROVED` translations, creates audit log, supports rollback.

#### `suggest_translation`
```python
@mcp.tool()
async def suggest_translation(
    key: str,
    market: str,
    source_locale: str,
    target_locale: str
) -> dict:
```
**Returns:** `{ suggestion: "...", confidence: 0.92, similar_keys: [...] }`

### 2.3 REST API Layer (FastAPI)

The same core service is exposed as REST endpoints for the admin UI and CI/CD:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/translations` | Create translation |
| PUT | `/api/v1/translations/{id}` | Update translation |
| GET | `/api/v1/translations` | List/search translations (filterable by market, locale, status) |
| GET | `/api/v1/translations/{key}` | Get specific translation |
| POST | `/api/v1/translations/sync` | Cross-market sync |
| POST | `/api/v1/translations/validate` | Validation check |
| POST | `/api/v1/translations/promote` | Environment promotion |
| GET | `/api/v1/translations/{key}/history` | Version history |
| POST | `/api/v1/translations/{id}/approve` | Approve translation |
| POST | `/api/v1/translations/{id}/reject` | Reject with feedback |
| GET | `/api/v1/markets` | List markets + locales |
| GET | `/api/v1/analytics/hotspots` | Low-confidence translation hotspots |
| GET | `/api/v1/analytics/most-edited` | Most edited translations per market |

### 2.4 Dual Transport

```python
# main.py
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

app = FastAPI(title="Translation MCP Server")
mcp_server = FastMCP("translation-agent")

# Register MCP tools (see 2.2 above)
# Register REST routes (see 2.3 above)
# Both share the same core TranslationService

# Entry points:
# - `python main.py serve`     → FastAPI on port 8000 (REST + SSE)
# - `python main.py mcp-stdio` → stdio transport for IDE integration
```

---

## 3. AI Translation Agent Architecture

### 3.1 Model Setup

```
Ollama (local)
├── qwen2.5:7b          # Primary translation model (multilingual)
├── gemma2:9b            # Fallback / comparison model
└── nomic-embed-text     # Embeddings for similar key lookup
```

**Why Qwen2.5:** Best multilingual performance among local models; supports all PepsiConnect locales (es, pt, tr, ru, ro, th, pl, ar, hi, zh, en).

### 3.2 Translation Generation Pipeline

```
Input: key="checkout.pay_now", default_text="Pay Now", market="IN", context="CTA button"
                            │
                            ▼
                ┌───────────────────────┐
                │  1. Context Assembly  │
                │  • Key name analysis  │
                │  • UI context string  │
                │  • Market metadata    │
                │  • Similar keys from  │
                │    vector search      │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  2. Prompt Assembly   │
                │  System: You are a    │
                │  professional UI      │
                │  translator for       │
                │  PepsiCo B2B...       │
                │  Market: India        │
                │  Tone: Formal B2B     │
                │  Context: CTA button  │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  3. LLM Generation    │
                │  Qwen2.5 via Ollama   │
                │  → "अभी भुगतान करें"    │
                │  → confidence: 0.88   │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  4. Post-Processing   │
                │  • Length validation   │
                │  • Character set check│
                │  • Confidence scoring  │
                │  • Flag if low conf.  │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  5. Store & Queue     │
                │  • Save to DB         │
                │  • State: AI_GENERATED│
                │  • Queue for review   │
                └───────────────────────┘
```

### 3.3 Feedback Learning Loop

When a business user corrects an AI-generated translation:
1. Store correction pair in `feedback_corrections` table: `(original_ai_output, corrected_value, key, market, locale)`
2. On next generation for same market+locale, include relevant corrections as few-shot examples in the prompt
3. Track correction rate per market+locale to identify weak areas

### 3.4 Confidence Scoring

```python
def compute_confidence(
    ai_output: str,
    source_text: str,
    locale: str,
    similar_translations: list
) -> float:
    score = 1.0
    # Penalize if output is same as source (untranslated)
    if ai_output.lower() == source_text.lower():
        score -= 0.5
    # Penalize if length ratio is unusual
    ratio = len(ai_output) / max(len(source_text), 1)
    if ratio > 3.0 or ratio < 0.2:
        score -= 0.3
    # Boost if similar to approved translations for same locale
    for sim in similar_translations:
        if similarity(ai_output, sim) > 0.8:
            score += 0.1
    return max(0.0, min(1.0, score))
```

---

## 4. Data Model (PostgreSQL)

### 4.1 Core Tables

```sql
-- Markets and their supported locales
CREATE TABLE markets (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10) UNIQUE NOT NULL,  -- "IN", "MX", "SA"
    name        VARCHAR(100) NOT NULL,        -- "India", "Mexico"
    site_id     INTEGER UNIQUE,               -- maps to CountrySiteId (34, 21, etc.)
    is_active   BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE market_locales (
    id          SERIAL PRIMARY KEY,
    market_id   INTEGER REFERENCES markets(id),
    locale_code VARCHAR(10) NOT NULL,         -- "en", "hi_IND", "es_MX"
    is_default  BOOLEAN DEFAULT false,
    UNIQUE(market_id, locale_code)
);

-- Core translation entries
CREATE TABLE translations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key             VARCHAR(500) NOT NULL,         -- "checkout.pay_now"
    market_id       INTEGER REFERENCES markets(id),
    locale_code     VARCHAR(10) NOT NULL,
    value           TEXT NOT NULL,
    default_text    TEXT,                           -- English source text
    context         TEXT DEFAULT '',                -- UI context description
    screen_id       VARCHAR(200) DEFAULT '',        -- Figma screen mapping
    figma_node_id   VARCHAR(100) DEFAULT '',        -- Figma node ID
    status          VARCHAR(30) NOT NULL DEFAULT 'CREATED',
    -- CREATED | AI_GENERATED | REVIEW_PENDING | APPROVED | PROMOTED
    environment     VARCHAR(10) NOT NULL DEFAULT 'QA',
    -- QA | STAGING | PROD
    confidence      FLOAT DEFAULT 0.0,
    version         INTEGER DEFAULT 1,
    created_by      VARCHAR(100) DEFAULT 'system',
    updated_by      VARCHAR(100) DEFAULT 'system',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(key, market_id, locale_code, environment)
);

CREATE INDEX idx_translations_key_market ON translations(key, market_id);
CREATE INDEX idx_translations_status ON translations(status);
CREATE INDEX idx_translations_env ON translations(environment);

-- Version history
CREATE TABLE translation_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    translation_id  UUID REFERENCES translations(id),
    version         INTEGER NOT NULL,
    value           TEXT NOT NULL,
    status          VARCHAR(30) NOT NULL,
    changed_by      VARCHAR(100),
    change_reason   TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Audit log for all operations
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action          VARCHAR(50) NOT NULL,
    -- CREATE | UPDATE | APPROVE | REJECT | PROMOTE | ROLLBACK | SYNC
    entity_type     VARCHAR(50) NOT NULL,          -- "translation"
    entity_id       UUID,
    market_code     VARCHAR(10),
    details         JSONB DEFAULT '{}',
    performed_by    VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- AI feedback corrections for learning loop
CREATE TABLE feedback_corrections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    translation_id      UUID REFERENCES translations(id),
    key                 VARCHAR(500),
    market_code         VARCHAR(10),
    locale_code         VARCHAR(10),
    ai_original_value   TEXT,
    corrected_value     TEXT,
    corrected_by        VARCHAR(100),
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_feedback_market_locale ON feedback_corrections(market_code, locale_code);

-- Environment promotions
CREATE TABLE promotions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_code     VARCHAR(10) NOT NULL,
    env_from        VARCHAR(10) NOT NULL,
    env_to          VARCHAR(10) NOT NULL,
    keys_promoted   INTEGER DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'COMPLETED',  -- COMPLETED | ROLLED_BACK
    promoted_by     VARCHAR(100),
    snapshot        JSONB DEFAULT '{}',  -- for rollback
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

### 4.2 Mapping to Existing b2b-portal Constants

| b2b-portal `CountrySiteId` | `markets.code` | `markets.site_id` | `market_locales` |
|---|---|---|---|
| India: 34 | IN | 34 | en, hi_IND |
| Mexico: 21 | MX | 21 | es_MX, en |
| SaudiArabia: 29 | SA | 29 | ar_SA, en |
| Egypt: 30 | EG | 30 | ar_EG, en |
| Turkey: 14 | TR | 14 | tr, en |
| Spain: 13 | ES | 13 | es, en, zh |
| Brazil: 11 | BR | 11 | pt_BR, en |
| Poland: 25 | PL | 25 | pl_PL, en |
| Thailand: 24 | TH | 24 | th_TH, en |
| Romania: 18 | RO | 18 | ro, en |
| Russia: 15 | RU | 15 | ru, en |
| Portugal: 16 | PT | 16 | pt, en |
| Colombia: 7 | CO | 7 | es, en |
| Chile: 22 | CL | 22 | es_CL, en |
| Argentina: 28 | AR | 28 | es_AR, en |
| DominicanRepublic: 20 | DO | 20 | es_DO, en |
| Peru: 32 | PE | 32 | es_PE, en |
| Ecuador: 33 | EC | 33 | es_EC, en |
| NewZealand: 17 | NZ | 17 | en |
| MexicoWholesaler: 26 | MXW | 26 | es_MX, en |

---

## 5. Translation Lifecycle Engine

### 5.1 State Machine

```
  CREATED ──► AI_GENERATED ──► REVIEW_PENDING ──► APPROVED ──► PROMOTED
     │              │                 │                │            │
     │              │                 ▼                │            ▼
     │              │             REJECTED ────►  (re-generate)  ROLLED_BACK
     │              │                                              │
     │              ▼                                              ▼
     └──────── (manual entry skips AI)                       (restore prev)
```

### 5.2 State Tracked Per

Each state is tracked per: **key + market + locale + environment**

### 5.3 Promotion Flow

```
promote_translations("IN", "QA", "PROD")
  │
  ├─ 1. Query all translations WHERE market="IN" AND environment="QA" AND status="APPROVED"
  ├─ 2. Compute delta vs current PROD translations
  ├─ 3. Snapshot current PROD state (for rollback)
  ├─ 4. Upsert into PROD environment
  ├─ 5. Update status → PROMOTED
  ├─ 6. Create audit log entry
  └─ 7. Return summary: { promoted: 42, unchanged: 180, new: 5 }
```

---

## 6. Figma Integration Strategy

### 6.1 Screen-to-Key Mapping

Store mapping in DB via `translations.screen_id` and `translations.figma_node_id`.

When `add_translation()` is called with a `screen_id`:
1. Store the screen_id association
2. If a Figma file key is configured, the admin UI can use the Figma MCP tools (`get_screenshot`, `get_design_context`) to show visual previews

### 6.2 Admin UI Integration

The `b2b-profile-admin-ui` will:
- Call `preview_translation(key, market, screen_id)` → returns translation + Figma metadata
- Use the Figma MCP server's `get_screenshot` tool to render the visual context
- Display translated text overlaid on the UI screenshot for business reviewers

### 6.3 Phased Approach

| Phase | Capability |
|-------|-----------|
| Phase 1 | Manual `screen_id` tagging by developers during `add_translation()` |
| Phase 2 | Auto-detect screen context from codebase (grep for key usage → map to component → map to Figma) |
| Phase 3 | Full Figma overlay preview with translation swap |

---

## 7. Admin Portal Integration (b2b-profile-admin-ui)

### 7.1 New Pages/Views

| Page | Description |
|------|------------|
| **Translation Dashboard** | Unified multi-market view with filters (market, locale, status, environment) |
| **Translation Detail** | Edit translation, view version history, AI suggestions with confidence |
| **Review Queue** | Business user review flow: translation + UI preview + approve/reject |
| **Validation Report** | Missing/inconsistent key alerts per market |
| **Promotion Manager** | Select market + env → preview delta → promote with one click |
| **Analytics** | Most edited translations, low-confidence hotspots, coverage metrics |

### 7.2 Integration Pattern

The admin UI consumes the REST API layer of the MCP server (Section 2.3). No direct DB access.

---

## 8. Consumer-Side Changes (b2b-portal)

### 8.1 Build-Time Translation Validation (Phase 1)

Add a script to `b2b-portal-shared` that:
1. Reads all keys from `translationConstants.js`
2. Calls `validate_translations` endpoint for configured market
3. Reports missing/inconsistent keys in CI output
4. Can block builds if critical keys are missing

```json
// package.json script
"validate:translations": "node scripts/validate-translations.js --market=IN"
```

### 8.2 Auto-Detection of Missing Keys (Phase 2)

A lint rule or build plugin that:
- Scans usage of `getTranslationValue()` and `Translate()` calls
- Extracts placeholder strings
- Cross-references with known keys in the MCP server
- Flags any unregistered keys

### 8.3 Developer MCP Client Integration (Phase 3)

Developers using Windsurf/Cursor with the MCP server configured can:
- `add_translation("checkout.pay_now", "Pay Now", market="IN")` directly from IDE
- Get auto-suggestions for translation keys during development
- Run validation without leaving the IDE

---

## 9. Project Structure (translation-mcp-server)

```
translation-mcp-server/
├── pyproject.toml              # Dependencies (fastapi, mcp, sqlalchemy, ollama, etc.)
├── alembic/                    # DB migrations
│   ├── alembic.ini
│   └── versions/
├── src/
│   ├── main.py                 # Entry point (FastAPI + MCP server)
│   ├── config.py               # Settings (DB URL, Ollama URL, model names)
│   ├── db/
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── session.py          # DB session management
│   │   └── seed.py             # Seed markets + locales from b2b-portal constants
│   ├── mcp/
│   │   ├── server.py           # MCP tool registrations
│   │   └── tools/
│   │       ├── add_translation.py
│   │       ├── update_translation.py
│   │       ├── get_translation.py
│   │       ├── sync_markets.py
│   │       ├── validate.py
│   │       ├── promote.py
│   │       ├── suggest.py
│   │       └── preview.py
│   ├── api/
│   │   ├── router.py           # FastAPI REST routes
│   │   ├── schemas.py          # Pydantic request/response models
│   │   └── deps.py             # Dependencies (auth, DB session)
│   ├── services/
│   │   ├── translation_service.py   # Core business logic
│   │   ├── lifecycle_engine.py      # State machine management
│   │   ├── promotion_engine.py      # Environment promotion
│   │   ├── validation_engine.py     # Missing/inconsistent key checks
│   │   └── sync_engine.py          # Cross-market sync
│   ├── ai/
│   │   ├── agent.py            # AI translation agent orchestration
│   │   ├── ollama_client.py    # Ollama API client (Qwen/Gemma)
│   │   ├── prompts.py          # Prompt templates per locale/market
│   │   ├── confidence.py       # Confidence scoring
│   │   └── feedback.py         # Learning loop from corrections
│   └── utils/
│       ├── market_config.py    # Market/locale configuration
│       └── pimcore_sync.py     # Optional: sync with existing Pimcore data
├── tests/
│   ├── test_mcp_tools.py
│   ├── test_api.py
│   ├── test_ai_agent.py
│   └── test_lifecycle.py
├── docker-compose.yml          # PostgreSQL + Ollama + app
├── Dockerfile
└── README.md
```

---

## 10. Key Dependencies

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "mcp>=1.0.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "ollama>=0.3.0",
    "pydantic>=2.0.0",
    "httpx>=0.27.0",
    "numpy>=1.26.0",         # for similarity/confidence
]
```

---

## 11. Multi-Market Scaling Strategy

### 11.1 Market Isolation

- Each translation is scoped to a market + locale + environment
- No implicit sharing — cross-market sync is explicit via `sync_translation_across_markets()`
- Markets can have independent review cycles

### 11.2 Market Groups (Optional)

For markets with shared languages (e.g., all LATAM Spanish markets), define market groups:
```python
MARKET_GROUPS = {
    "LATAM_ES": ["MX", "CO", "CL", "AR", "PE", "EC", "DO"],
    "ARABIC": ["SA", "EG"],
    "IBERIAN": ["ES", "PT"],
}
```
When a translation is approved in one group member, suggest reuse to others.

### 11.3 Fallback Strategy

```
Lookup order: market-specific key → market-group fallback → English default
Example: MX.checkout.pay_now → LATAM_ES.checkout.pay_now → checkout.pay_now (en)
```

---

## 12. CI/CD Integration

### 12.1 Pipeline Steps

```yaml
# Azure DevOps pipeline addition for b2b-portal
- task: Script@1
  displayName: 'Validate Translations'
  inputs:
    script: |
      curl -X POST $(TRANSLATION_MCP_URL)/api/v1/translations/validate \
        -H "Content-Type: application/json" \
        -d '{"market": "$(MARKET_CODE)", "check_missing": true}'
    # Fail build if missing critical keys
```

### 12.2 Auto-Promotion on Release

```yaml
# On merge to release branch
- task: Script@1
  displayName: 'Promote Translations QA → PROD'
  inputs:
    script: |
      curl -X POST $(TRANSLATION_MCP_URL)/api/v1/translations/promote \
        -d '{"market": "$(MARKET_CODE)", "env_from": "QA", "env_to": "PROD"}'
```

---

## 13. Implementation Phases

### Phase 1: Foundation (Weeks 1-3)
- [ ] Set up `translation-mcp-server` project with FastAPI + PostgreSQL
- [ ] Implement DB models + Alembic migrations
- [ ] Seed markets/locales from b2b-portal constants
- [ ] Implement core MCP tools: `add_translation`, `get_translation`, `update_translation`
- [ ] Implement lifecycle engine (state machine)
- [ ] Basic REST API layer

### Phase 2: AI Agent (Weeks 3-5)
- [ ] Ollama integration with Qwen2.5
- [ ] Translation generation pipeline with context-aware prompts
- [ ] Confidence scoring
- [ ] `suggest_translation` tool
- [ ] Feedback correction storage

### Phase 3: Multi-Market & Validation (Weeks 5-7)
- [ ] `sync_translation_across_markets` tool
- [ ] `validate_translations` tool
- [ ] Cross-market consistency checks
- [ ] Market groups + fallback strategy
- [ ] `promote_translations` tool with rollback

### Phase 4: Admin UI Integration (Weeks 7-9)
- [ ] Translation dashboard in `b2b-profile-admin-ui`
- [ ] Review queue with approve/reject flow
- [ ] Version history view
- [ ] Analytics pages

### Phase 5: Consumer Integration & CI/CD (Weeks 9-11)
- [ ] Build-time validation script for `b2b-portal`
- [ ] CI/CD pipeline integration
- [ ] IDE MCP client configuration
- [ ] Auto-detection of missing keys
- [ ] Figma preview integration (basic)

### Phase 6: Polish & Advanced Features (Weeks 11-13)
- [ ] Feedback learning loop (few-shot correction examples)
- [ ] Pimcore data migration/sync
- [ ] Analytics: most-edited, low-confidence hotspots
- [ ] Market group auto-suggestions
- [ ] Full Figma overlay preview

---

## 14. MCP Server Configuration (for IDE)

```json
// .windsurf/mcp_config.json or equivalent
{
  "mcpServers": {
    "translation-agent": {
      "command": "python",
      "args": ["-m", "src.main", "mcp-stdio"],
      "cwd": "/path/to/translation-mcp-server",
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/translations",
        "OLLAMA_BASE_URL": "http://localhost:11434"
      }
    }
  }
}
```

---

## 15. Bonus: Analytics Queries

```sql
-- Most edited translations per market
SELECT t.key, m.code as market, t.locale_code, t.version,
       COUNT(fc.id) as correction_count
FROM translations t
JOIN markets m ON t.market_id = m.id
LEFT JOIN feedback_corrections fc ON fc.translation_id = t.id
GROUP BY t.key, m.code, t.locale_code, t.version
ORDER BY correction_count DESC
LIMIT 20;

-- Low-confidence hotspots
SELECT t.key, m.code as market, t.locale_code, t.confidence
FROM translations t
JOIN markets m ON t.market_id = m.id
WHERE t.confidence < 0.7 AND t.status = 'AI_GENERATED'
ORDER BY t.confidence ASC;

-- Translation coverage per market
SELECT m.code,
       COUNT(CASE WHEN t.status = 'APPROVED' THEN 1 END) as approved,
       COUNT(CASE WHEN t.status = 'REVIEW_PENDING' THEN 1 END) as pending,
       COUNT(*) as total,
       ROUND(COUNT(CASE WHEN t.status = 'APPROVED' THEN 1 END)::numeric / COUNT(*)::numeric * 100, 1) as coverage_pct
FROM markets m
LEFT JOIN translations t ON t.market_id = m.id
GROUP BY m.code
ORDER BY coverage_pct ASC;
```
