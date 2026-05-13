# Manual Podman Build & Deploy Guide

All commands are run manually from the repo root. No automation — copy-paste each step.

---

## Prerequisites

- Podman installed and running
- PostgreSQL accessible (or Podman container below)
- Ollama running locally on port `11434` (for Ollama provider)
- Your `.env` file ready with secrets (see **Environment Variables** section)

---

## 1. Build the Image

```bash
podman build -t translation-mcp-server:latest .
```

To tag with a version:

```bash
podman build -t translation-mcp-server:1.0.0 .
```

---

## 2. Create a Podman Network (shared by all containers)

```bash
podman network create translation-net
```

---

## 3. Start PostgreSQL

> **If port 5432 is already in use** (e.g. a local Postgres is running), choose one of:
> - **Option A** — map to a different host port (`5433:5432`) as shown below. The `DB_URL` inside the network still uses `translation-db:5432`.
> - **Option B** — skip this step and point `DB_URL` at your existing local Postgres: `postgresql+asyncpg://postgres:postgres@host.containers.internal:5432/translations`

```bash
# Option A: container Postgres on host port 5433 (avoids conflict)
podman run -d \
  --name translation-db \
  --network translation-net \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=translations \
  -p 5433:5432 \
  postgres:16

Wait a few seconds for Postgres to be ready, then verify:

```bash
podman exec -it translation-db pg_isready -U postgres
```

---

## 4. Run the FastAPI App

```bash
podman run -d \
  --name translation-app \
  --network translation-net \
  -p 8000:8000 \
  --env-file .env \
  translation-mcp-server:latest
```

---

## 5. Run the MCP SSE Server

```bash
podman run -d \
  --name translation-mcp \
  --network translation-net \
  -p 8001:8001 \
  --env-file .env \
  -e PYTHONPATH=/app \
  translation-mcp-server:latest \
  python -m src.mcp.server
```

---

<!-- ## 6. Run Database Migrations (Alembic)

Run migrations against the running app container:

```bash
podman exec -it translation-app \
  bash -c "cd /app && alembic upgrade head"
```

Or seed the DB:

```bash
podman exec -it translation-app \
  bash -c "cd /app && python src/db/seed.py"
``` -->

---

## 7. Verify Everything is Running

```bash
# List running containers
podman ps

# Check FastAPI health
curl http://localhost:8000/health

# Check MCP SSE endpoint
curl http://localhost:8001/sse
```

---

## 8. View Logs

```bash
# App logs
podman logs -f translation-app

# MCP logs
podman logs -f translation-mcp

# DB logs
podman logs -f translation-db
```

---

## 9. Stop and Remove Containers

```bash
podman stop translation-app translation-mcp translation-db
podman rm translation-app translation-mcp translation-db
```

Remove the network when done:

```bash
podman network rm translation-net
```

---

## Environment Variables Reference

| Variable | Description | Default (baked in image) |
|---|---|---|
| `DB_URL` | Async PostgreSQL URL | — (required) |
| `APP_ENV` | Environment name | `local` |
| `AUTO_CREATE_DB` | Auto-create schema on start | `false` |
| `DEFAULT_AI_PROVIDER` | `openai` or `ollama` | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `AI_MODEL` | Model name (e.g. `gpt-4o`) | — |
| `OLLAMA_URL` | Ollama base URL | `http://host.containers.internal:11434` |

> On **Podman (Mac/Linux)** use `host.containers.internal` to reach local Ollama.  
> On **Docker Desktop (Mac)** use `host.docker.internal`.

---

## MCP Client Config (IDE)

After the MCP container is up, point your IDE MCP client to:

```
http://localhost:8001/sse
```

See `mcp_client/MCP_SETUP.md` for the full Windsurf/VS Code configuration.
