"""MCP tools package initializer.

Import tool modules here so that `src.mcp.server` can import the package
and have all tools registered on the `mcp` instance.
"""

from . import translation_tools  # noqa: F401

__all__ = ["translation_tools"]
