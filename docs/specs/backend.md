# champi-stt MCP Server Specification

## Overview
Add an MCP (Model Context Protocol) server to the champi-stt library, exposing speech-to-text capabilities as MCP tools for use by Claude and other LLM clients.

## Architecture
- New module: `src/champi_stt/mcp/` with `server.py`, `tools.py`, `__init__.py`
- Transport: stdio (primary), SSE (optional)
- Dependency: `mcp` (fastmcp) package
- CLI entry point: `champi-stt mcp serve`

## MCP Tools
1. `transcribe_audio(audio_path, language, provider)` -- transcribe a local audio file
2. `list_providers()` -- list available/configured STT providers
3. `get_provider_status(provider)` -- health check a provider
4. `detect_language(audio_path)` -- detect spoken language in audio

## Gaps to Close
- Hardcoded dev path in WhisperLive config (line 62)
- No `mcp` dependency in pyproject.toml
- No MCP module or CLI command
- Test coverage needs improvement (42% overall)
- Open issues #31 (PyPI publish matrix) and #32 (migration guide)

## Non-goals (v1.0)
- Streaming MCP tool (deferred to v1.1)
- Web frontend
- Docker packaging
