# Helper Commands — Translation MCP Server

---

## Step 1 — Set Up Virtual Environment (first time only)

```bash
# 1. Create the virtual environment
python3.11 -m venv .venv

# 2. Activate it
source .venv/bin/activate

# 3. Install all dependencies
./scripts/bootstrap.sh
```

> Every time you open a new terminal, just run step 2 (`source .venv/bin/activate`) before anything else.

---

## Step 2 — Run Migrations (first time or after model changes)

**Important:** Since `alembic.ini` is in the `alembic/` directory, use the `-c` flag:

```bash
# Generate a new migration file from model changes
alembic -c alembic/alembic.ini revision --autogenerate -m "description of change"

# Apply all pending migrations to the DB
alembic -c alembic/alembic.ini upgrade head
```

---

## Step 3 — Start the FastAPI App

> Make sure DB is running before this step (see Step 5 for DB options).
> Ensure `DB_URL` is set in `.env`.

```bash
# Start the API server (hot-reload enabled)
uvicorn main:app --app-dir src --reload --host 0.0.0.0 --port 8000

# Alternative: start app + DB together via Docker
docker-compose up --build
```

---

## Step 4 — Start the MCP Server

> The MCP server runs separately from the FastAPI app on port 8001 (SSE transport).

```bash
# Run the MCP server (from project root, with venv active)
python -m src.mcp.server
```

> Logs are written to `src/mcp/mcp.log`. Check there if tools are not loading.

---

## Step 5 — Connect to the Database (pgweb UI)

**Local Postgres:**
```bash
PGPASSWORD=admin pgweb --host=localhost --port=5432 --user=postgres --db=postgres
```

**Docker / Podman Postgres:**
```bash
PGPASSWORD=postgres pgweb --host=127.0.0.1 --port=5433 --user=postgres --db=translations
```

> Open `http://localhost:8081` in your browser after running either command.

---

## Step 6 — Start Ollama (Local AI Model)

```bash
# Start the Gemma model — serves on http://localhost:11434
ollama run gemma3:4b
```


