"""MCP (Model Context Protocol) server for champi-stt."""

from champi_stt.mcp.server import main, mcp

__all__ = ["main", "mcp"]
"""
MCP server for champi-stt.

Exposes speech-to-text capabilities as MCP tools for use by LLM clients
(Claude, etc.). Install the mcp extra to use this module:

    pip install 'champi-stt[mcp]'

Entry point (Phase 2):
    champi-stt mcp serve
"""
