# MCP Server Setup Guide

Two transport options are available. Use **stdio** for local development, **SSE** for containerised / shared / demo deployments.

---

## Transport 1 — stdio (local only)

### How it works
The IDE spawns the Python process directly and communicates via stdin/stdout pipes.
No HTTP server is needed. The IDE manages the process lifecycle.

### When to use
- Local development on the same machine as the IDE
- Quickest setup — no manual server start required

### Server config (`src/mcp/server.py`)
```python
def main() -> None:
    log(f"MCP server starting... log: {LOG_FILE}")
    # mcp.settings.host = "0.0.0.0"
    # mcp.settings.port = 8001
    mcp.run(transport="stdio")                  # ← active
    # mcp.run(transport="sse")                  # ← commented out
```

### IDE config (`mcp_client/mcp_client_setup.json`)
```json
{
  "mcpServers": {
    "translation-mcp-server-stdio": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/src/mcp/server.py"],
      "disabled": false
    },
    "translation-mcp-server-sse": {
      "url": "http://localhost:8001/sse",
      "disabled": true
    }
  }
}
```

### Start
Nothing to start manually — the IDE spawns the process when the MCP panel loads.

---

## Transport 2 — SSE (HTTP, network-accessible)

### How it works
The MCP server runs as a standalone HTTP server.
The IDE connects to it via `GET /sse` (Server-Sent Events) over the network.
**You must start the server manually** before the IDE can connect.

### When to use
- Containerised / Docker deployments
- Demo environments accessible from multiple clients
- CI/CD or remote server scenarios
- When the MCP server and IDE are on different machines

### Server config (`src/mcp/server.py`)
```python
def main() -> None:
    log(f"MCP server starting... log: {LOG_FILE}")
    mcp.settings.host = "0.0.0.0"              # ← listen on all interfaces
    mcp.settings.port = 8001                   # ← port (avoid 8000 used by FastAPI)
    # mcp.run(transport="stdio")               # ← commented out
    mcp.run(transport="sse")                   # ← active
```

### IDE config (`mcp_client/mcp_client_setup.json`)
```json
{
  "mcpServers": {
    "translation-mcp-server-stdio": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/src/mcp/server.py"],
      "disabled": true
    },
    "translation-mcp-server-sse": {
      "url": "http://localhost:8001/sse",
      "disabled": false
    }
  }
}
```

For a remote/Docker host, replace `localhost` with the container IP or hostname:
```json
"url": "http://<docker-host-ip>:8001/sse"
```

### Start (local)
```bash
cd /path/to/translation-mcp-server
source .venv/bin/activate
PYTHONPATH=src python src/mcp/server.py
```

Expected output:
```
2026-04-21 10:00:00 MCP server starting... log: .../mcp.log
2026-04-21 10:00:00 registered src.mcp.tools.translation_tools
INFO:     Started server process [XXXXX]
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to stop)
```

### Start (Docker Compose)
Add an `mcp` service to `docker-compose.yml`:
```yaml
mcp:
  build: .
  command: ["python", "src/mcp/server.py"]
  environment:
    - DB_URL=postgresql+asyncpg://postgres:postgres@db:5432/translations
    - PYTHONPATH=/app/src
  ports:
    - "8001:8001"
  depends_on:
    - db
```

Then the IDE config points to:
```json
"url": "http://localhost:8001/sse"
```

---

## Switching Between Transports

| Step | stdio → SSE | SSE → stdio |
|------|-------------|-------------|
| `server.py` | Comment `mcp.run(transport="stdio")`, uncomment `mcp.settings.*` + `mcp.run(transport="sse")` | Reverse |
| `mcp_client_setup.json` | Set `stdio` entry `disabled: true`, `sse` entry `disabled: false` | Reverse |
| Start server | Start manually: `PYTHONPATH=src python src/mcp/server.py` | Nothing — IDE handles it |
| Reload IDE | Restart Windsurf / reload MCP config | Same |

---

## SSE Endpoints (when running)

| Endpoint | Purpose |
|----------|---------|
| `GET http://localhost:8001/sse` | SSE stream — IDE connects here |
| `POST http://localhost:8001/messages/` | Tool call messages |

---

## Verify Connection

After starting the SSE server, test from terminal:
```bash
curl -N http://localhost:8001/sse
# Should stream SSE events — confirms server is reachable
```

Then in Windsurf — open the MCP panel and call `ping` tool:
```
→ {"status": "ok"}
```
