"""
MCP server for champi-stt.

Exposes champi-stt transcription capabilities over the Model Context
Protocol (MCP) stdio transport so that MCP-aware hosts (e.g. Claude
Desktop, Cursor) can call transcription tools directly.

Stdout MUST remain clean for JSON-RPC framing — all loguru output is
redirected to stderr before the server starts.
"""

from __future__ import annotations

import sys

try:
    from mcp.server.fastmcp import FastMCP

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

mcp: FastMCP | None = None

if MCP_AVAILABLE:
    mcp = FastMCP("champi-stt")

    # TODO(issue-53): register transcription tools here once tools.py is ready.


def _require_mcp() -> None:
    if not MCP_AVAILABLE:
        raise ImportError(
            "mcp is required for the MCP server. "
            "Install with: pip install 'champi-stt[mcp]'"
        )


def main() -> None:
    """Start the MCP server on the stdio transport.

    Redirects all loguru sinks to stderr so that stdout remains clean
    for JSON-RPC framing, then hands control to ``mcp.run()``.

    Raises:
        ImportError: If the ``mcp`` package is not installed.
    """
    _require_mcp()

    from loguru import logger

    logger.remove()
    logger.add(sys.stderr)

    assert mcp is not None
    mcp.run(transport="stdio")
