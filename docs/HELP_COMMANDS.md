# Helper Commands — Translation MCP Server

Quick commands to set up the environment, run the app, and run tests.

## Check Python
```bash
python3 --version
which python3
python3 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
```

## Create and activate virtualenv (macOS / Linux)
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

## Deactivate virtualenv
```bash
deactivate
```

## Install dependencies
Option A — recommended (bootstrap script):
```bash
./scripts/bootstrap.sh
source .venv/bin/activate
```

Option B — manual install:
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip freeze > requirements.txt
```

## Run the FastAPI app (local)
Requires DB running (use Docker Compose or local Postgres).

```bash

# start app from root folder
uvicorn main:app --app-dir src --reload --host 0.0.0.0 --port 8000

# or (use docker-compose to run DB + app)
docker-compose up --build
```

## Run tests
```bash
pytest -q
```

## Alembic migrations
```bash
# generate first migration after models are stable
alembic revision --autogenerate -m "initial"
# apply migrations
alembic upgrade head
```

## Check outdated packages
```bash
pip list --outdated --format=columns
```

## Helpful notes
- Use `docker-compose` if you don't have a local Postgres available.
- Ensure `DB_URL` is set in `.env` or environment before running the app.
- If you change dependencies, regenerate `requirements.txt` with:
```bash
pip freeze | sed '/^-e /d' > requirements.txt
```

## Inspect DB via pgweb

If you have `pgweb` installed you can launch a lightweight web UI for Postgres:

```bash
PGPASSWORD=admin pgweb --host=localhost --port=5432 --user=postgres --db=postgres
```

## Start Ollama (local model)

If you have Ollama installed locally, run a model instance (serves HTTP API on port 11434):

```bash
# start the Gemma model on the local Ollama runtime
ollama run gemma3:4b
```


