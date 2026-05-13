# Translation MCP Server — Architecture Design

## 1. Architecture Summary

The service uses a straightforward production architecture with clear boundaries:

- **Layered architecture** for separation of concerns
- **Dual transport** for IDE MCP clients and REST consumers
- **State machine** for translation lifecycle control
- **Pipeline pattern** for AI translation generation
- **Market-isolated multi-tenancy** for translation scoping
- **Partial event sourcing** for version history and rollback support
- **Repository/service split** to keep API and MCP layers thin

---

## 2. Architecture Style

### Layered Architecture
MCP tools and REST APIs call services, services call repositories or DB models, and AI logic stays isolated in the AI layer.

### Dual Transport
The same core service is exposed through:
- `stdio` for IDE MCP clients
- HTTP/SSE for REST consumers

### State Machine
Translation records move through:
`CREATED → AI_GENERATED → REVIEW_PENDING → APPROVED → PROMOTED`

Invalid transitions are rejected by the lifecycle engine.

### Pipeline Pattern
AI translation generation follows a small pipeline:
`context assembly → prompt creation → model call → post-processing → confidence scoring`

### Market-Isolated Multi-Tenancy
Each translation is scoped to:
`key + market + locale + environment`

Cross-market sharing happens only through explicit sync.

### Partial Event Sourcing
Translation versions and audit logs preserve change history.
Promotion snapshots enable rollback.

### Repository/Service Split
Database access stays inside translation service or repository code so the API and MCP layers remain thin and maintainable.

---

## 3. Fit in the System

### Entry Points
- **MCP tools**: developer-facing commands for add, get, update, sync, validate, promote, suggest, and preview
- **REST API**: consumer endpoints for CI/CD, admin workflows, and analytics
- **Future UI**: admin portal can consume the REST API without direct DB access

### Core Services
- **Translation service**: create/read/update operations
- **Lifecycle engine**: state validation and transitions
- **AI agent**: translation generation and suggestion
- **Validation engine**: missing and inconsistent translation detection
- **Promotion engine**: environment promotion and rollback
- **Sync engine**: cross-market reuse and propagation

### Data Boundaries
- **PostgreSQL** stores translations, versions, audit logs, feedback corrections, and promotions
- **OpenAI API** handles translation generation and suggestion
- **No auth** in the first iteration; this stays an internal service

---

## 4. Why This Architecture Fits

- Keeps the first version simple enough to ship quickly
- Supports both developer workflows and API-driven automation
- Preserves history for review, rollback, and analytics
- Allows market-specific behavior without coupling markets together
- Leaves room for future auth, admin UI, Pimcore sync, and Figma integration without reworking the core
