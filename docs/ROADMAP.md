# Translation MCP Server Roadmap

## Goal
Build the translation API in small steps, starting with a working FastAPI app, then add PostgreSQL, ORM models, and migrations.

## Phase 1 - Foundation
- Verify the FastAPI app starts
- Keep the health endpoint working
- Use one Python virtual environment only
- Fix dependency setup for the active Pydantic version
- Add basic logging

## Phase 2 - Database Basics
- Learn PostgreSQL basics: database, schema, table, row, column, primary key, foreign key
- Learn basic SQL: SELECT, INSERT, UPDATE, DELETE, WHERE, JOIN
- Set up local PostgreSQL
- Configure `DB_URL` in `.env`
- Connect app to PostgreSQL

## Phase 3 - SQLAlchemy ORM
- Learn SQLAlchemy ORM concepts
- Understand `Base`, models, sessions, and queries
- Map Python classes to tables
- Use async session with `asyncpg`
- Test simple CRUD operations

## Phase 4 - Migrations
- Learn Alembic basics
- Create first migration from models
- Apply migration to Postgres
- Verify tables are created correctly

## Phase 5 - Core CRUD APIs
- Add translation models
- Build create, read, update, list APIs
- Add validation and error handling
- Return proper API responses

## Phase 6 - AI Layer
- Add OpenAI client
- Generate translation suggestions
- Add confidence scoring
- Store feedback corrections

## Phase 7 - Multi-Market and Promotion
- Add sync across markets
- Add validation checks
- Add promotion and rollback flow
- Keep audit logs

## Phase 8 - Cleanup and Docs
- Add tests
- Improve logging
- Add setup docs
- Finalize IDE config

## Quick Learning Order
1. FastAPI health endpoint
2. PostgreSQL basics
3. SQLAlchemy ORM
4. Alembic migrations
5. CRUD APIs
6. AI integration

## First Practical Check
- Run the app
- Open `/health`
- Then start DB setup
- Then add models and migrations


## postgresql detail
-Tool
-PostgreSQL → Database
-pgweb → Web UI

# Start pgweb
PGPASSWORD=admin pgweb --host=localhost --port=5432 --user=postgres --db=postgres
