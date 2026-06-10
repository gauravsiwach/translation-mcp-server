# Deployment Guide

This guide covers two deployment methods for the translation MCP server:
1. **Manual Podman** - Step-by-step manual deployment (full control)
2. **Docker Compose** - Automated deployment (recommended for simplicity)

Both methods work with Podman and Docker.

---

## Prerequisites

- Podman or Docker installed and running
- `.env` file in the project root with your environment variables
- PostgreSQL accessible (or use the containerized PostgreSQL)

---

## Method 1: Manual Podman Deployment

This method gives you full control over each step. Useful for debugging or custom configurations.

### Step 1: Build the Image

```bash
podman build -t translation-mcp-server:latest .
```

### Step 2: Create a Podman Network

```bash
podman network create translation-net
```

### Step 3: Start PostgreSQL

```bash
# Uses port 5433 to avoid conflict with local Postgres
podman run -d \
  --name translation-db \
  --network translation-net \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=translations \
  -p 5433:5432 \
  postgres:16
```

Wait a few seconds for Postgres to be ready, then verify:

```bash
podman exec -it translation-db pg_isready -U postgres
```

### Step 4: Run the FastAPI App

```bash
podman run -d \
  --name translation-app \
  --network translation-net \
  -p 8000:8000 \
  --env-file .env \
  translation-mcp-server:latest
```

### Step 5: Run the MCP SSE Server

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

### Step 6: Verify Everything is Running

```bash
# List running containers
podman ps

# Check FastAPI health
curl http://localhost:8000/health

# Check MCP SSE endpoint
curl http://localhost:8001/sse
```

### Step 7: View Logs

```bash
# App logs
podman logs -f translation-app

# MCP logs
podman logs -f translation-mcp

# DB logs
podman logs -f translation-db
```

### Step 8: Stop and Remove Containers

```bash
podman stop translation-app translation-mcp translation-db
podman rm translation-app translation-mcp translation-db
```

Remove the network when done:

```bash
podman network rm translation-net
```

---

## Method 2: Docker Compose Deployment (Recommended)

Automated deployment using docker-compose. Single command to start/stop everything.

### Quick Start

#### Start all services

```bash
# Using Podman
podman compose up -d

# Using Docker
docker compose up -d
```

This will:
1. Build the Docker image automatically (if needed)
2. Start PostgreSQL database
3. Wait for database to be healthy
4. Start FastAPI app on port 8000
5. Start MCP SSE server on port 8001

#### View logs

```bash
# Follow all logs
podman compose logs -f

# Follow specific service logs
podman compose logs -f app
podman compose logs -f mcp
podman compose logs -f translation-db
```

#### Stop all services

```bash
podman compose down
```

#### Stop and remove volumes (clean slate)

```bash
podman compose down -v
```

#### Rebuild and start

```bash
podman compose up -d --build
```

---

## Common Verification Steps (Both Methods)

Check that all services are running:

```bash
# For manual Podman
podman ps

# For docker-compose
podman compose ps
```

Test the endpoints:

```bash
# Check FastAPI health
curl http://localhost:8000/health

# Check MCP SSE endpoint
curl http://localhost:8001/sse
```

---

## Service Details

### Services

| Service | Port | Description |
|---------|------|-------------|
| translation-db | 5433 | PostgreSQL database |
| app | 8000 | FastAPI application |
| mcp | 8001 | MCP SSE server |

### Database Access

- **Host:** `localhost:5433`
- **Database:** `translations`
- **Username:** `postgres`
- **Password:** `postgres`

### MCP Client Config

Point your IDE MCP client to:
```
http://localhost:8001/sse
```

See `mcp_client/MCP_SETUP.md` for full Windsurf/VS Code configuration.

---

## Environment Variables

All environment variables are loaded from `.env` file in the project root.

Required variables in `.env`:
```
DB_URL=postgresql+asyncpg://postgres:postgres@translation-db:5432/translations
DEFAULT_AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
AI_MODEL=gpt-4o
```

Optional variables:
```
APP_ENV=local
AUTO_CREATE_DB=false
OLLAMA_URL=http://host.containers.internal:11434
```

---

## Troubleshooting

### Services not starting

**Manual Podman:**
```bash
podman logs translation-app
podman logs translation-mcp
podman logs translation-db
```

**Docker Compose:**
```bash
podman compose logs
```

### Database connection issues

Ensure DB_URL in `.env` uses `translation-db` as the hostname:
```
DB_URL=postgresql+asyncpg://postgres:postgres@translation-db:5432/translations
```

### Port conflicts

If port 5433 is already in use:

**Manual Podman:** Change the port mapping in Step 3
**Docker Compose:** Edit `docker-compose.yml` and change:
```yaml
ports:
  - "5434:5432"  # Change 5433 to another port
```

### Rebuild from scratch

**Manual Podman:**
```bash
podman stop translation-app translation-mcp translation-db
podman rm translation-app translation-mcp translation-db
podman network rm translation-net
podman build -t translation-mcp-server:latest .
# Then follow steps 2-5 again
```

**Docker Compose:**
```bash
podman compose down -v
podman compose up -d --build
```

---

## Comparison: Manual Podman vs Docker Compose

| Feature | Manual Podman | Docker Compose |
|---------|---------------|---------------|
| **Setup complexity** | High (8 steps) | Low (1 command) |
| **Build step** | Manual (`podman build`) | Automatic |
| **Network** | Manual creation | Automatic |
| **Container naming** | Manual (`--name`) | Automatic |
| **Health checks** | Manual verification | Built-in |
| **Startup order** | Manual (wait for DB) | Automatic (`depends_on`) |
| **Logs** | Individual commands | Single command |
| **Cleanup** | Multiple commands | Single command |
| **Best for** | Debugging, custom configs | Daily use, simplicity |

**Recommendation:** Use Docker Compose for daily development and deployment. Use Manual Podman when you need fine-grained control or debugging.
