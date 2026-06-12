# Phase 2: MCP Server Implementation

## Goal
A fully working MCP server that exposes champi-stt transcription capabilities as MCP tools, startable via `champi-stt mcp serve` and configurable in Claude Desktop / other MCP clients.

## Deliverables

### Backend
- [ ] Implement `src/champi_stt/mcp/server.py` -- FastMCP server with stdio transport
- [ ] Implement `src/champi_stt/mcp/tools.py` -- MCP tool definitions:
  - `transcribe_audio(audio_path: str, language: str | None, provider: str) -> str`
  - `list_providers() -> list[str]`
  - `get_provider_status(provider: str) -> dict`
  - `detect_language(audio_path: str) -> dict`
- [ ] Export MCP server from `src/champi_stt/mcp/__init__.py`
- [ ] Add `champi-stt-mcp = "champi_stt.mcp.server:main"` entry point in `pyproject.toml` `[project.scripts]`
- [ ] Add `mcp serve` subcommand to CLI (`cli.py`) that starts the MCP server
- [ ] Handle provider lifecycle (lazy init on first tool call, graceful shutdown)
- [ ] Support provider selection via environment variable (`CHAMPI_STT_PROVIDER`) or tool argument
- [ ] Add SSE transport option behind `--transport sse` flag (optional, stdio is default)

### Infrastructure
- [ ] Add example `claude_desktop_config.json` snippet to `docs/` showing how to register the MCP server
- [ ] Verify MCP server starts and responds to `initialize` handshake via stdio

## Done Definition
- `champi-stt mcp serve` starts without error and responds to MCP `initialize`
- `champi-stt-mcp` entry point works as a standalone command
- All four MCP tools return valid responses when called with test inputs
- MCP server can be registered in Claude Desktop config and tools appear in tool list
- Provider initializes lazily on first transcription request

## Parallel work
- Tool definitions (`tools.py`) can be written while server scaffold (`server.py`) is built
- Claude Desktop config docs can be written independently of implementation

## Phase dependencies
- Requires: Phase 1 (MCP dependency in pyproject.toml, empty mcp module scaffold)

## Complexity
- Backend: M
- Frontend: N/A
- Infra: S

## Risks
- FastMCP API may have breaking changes between versions -- pin to a specific version range
- stdio transport requires careful handling of stdin/stdout to avoid corrupting the MCP protocol with log output (loguru must not write to stdout)
- Provider initialization may be slow (model download) on first use -- need clear user feedback
