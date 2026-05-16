"""MCP server: registers tools and runs FastMCP with stdio transport.

Run with: `python -m src.mcp.server`
"""
import sys
import os
import logging

from mcp.server.fastmcp import FastMCP

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_root_dir = os.path.dirname(_src_dir)

# Add both src/ (for db.session, services etc.) and project root (for src.mcp.tools imports).
for _p in (_src_dir, _root_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Load .env from project root so pydantic-settings picks up DB_URL and other vars.
try:
    from dotenv import load_dotenv

    _env_file = os.path.join(_root_dir, ".env")
    if os.path.exists(_env_file):
        load_dotenv(_env_file, override=False)
except ImportError:
    # dotenv not installed — that's fine in some environments
    pass

LOG_FILE = os.path.join(os.path.dirname(__file__), "mcp.log")

logger = logging.getLogger("mcp")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)
    logger.addHandler(sh)


def log(msg: str) -> None:
    logger.info(msg)


mcp = FastMCP("translation-mcp-server")


@mcp.tool()
def ping() -> dict:
    """Simple health check for IDEs.

    Returns: {"status": "ok"}
    """
    log("ping called")
    return {"status": "ok"}


# Import tools package to ensure tools are registered (may be empty during step 1)
# Register tools via their `register(mcp, log)` entrypoint to avoid circular
# imports (tools should not import `mcp` at module import time).
try:
    from src.mcp.tools.translation_tools import register as _register_translation_tools

    _register_translation_tools(mcp, log)
    log("registered src.mcp.tools.translation_tools")
except Exception as exc:  # pragma: no cover - safe import
    log(f"translation_tools registration failed: {exc}")


def main() -> None:
    log(f"MCP server starting... log: {LOG_FILE}")
    # mcp.run(transport="stdio")
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8002
    mcp.run(transport="sse")
   


if __name__ == "__main__":
    main()


# cmd to run the mcp server
#python src/mcp/server.py

# Example mcp launch configuration
# "translation-mcp-server": {
#     "args": [
#       "/Users/gaurav.siwach/Work/Gaurav/translation-mcp-server/src/mcp/server.py"
#     ],
#     "command": "/Users/gaurav.siwach/Work/Gaurav/translation-mcp-server/.venv/bin/python",
#     "disabled": false
#   }

#  "translation-mcp-server-sse": {
#       "url": "http://localhost:8001/sse"
#     },