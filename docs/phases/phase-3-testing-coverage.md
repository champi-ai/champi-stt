# Phase 3: Testing & Coverage

## Goal
MCP tools have comprehensive test coverage, overall project coverage reaches 60%+, and all MCP tool schemas are validated.

## Deliverables

### Backend
- [ ] Add unit tests for all four MCP tools (`tests/test_mcp/test_tools.py`)
- [ ] Add integration test for MCP server startup and initialize handshake (`tests/test_mcp/test_server.py`)
- [ ] Add test for `champi-stt mcp serve` CLI command invocation (`tests/test_mcp/test_cli.py`)
- [ ] Add tests verifying MCP tool JSON schemas match expected signatures
- [ ] Improve WhisperLive provider test coverage (currently 28%) -- add tests for config validation, path resolution, provider lifecycle
- [ ] Improve transcriber test coverage (currently 18%) -- add tests for error handling, edge cases
- [ ] Add tests for the hardcoded-path fixes from Phase 1 (config defaults, fallback paths)
- [ ] Fix or add skip markers for any tests that require hardware (GPU, microphone)

### Infrastructure
- [ ] Add MCP test dependencies to `[project.optional-dependencies]` dev/test group if needed
- [ ] Ensure CI runs MCP tests in the test matrix
- [ ] Add coverage threshold check to CI (fail if below 55%)

## Done Definition
- `uv run python -m pytest tests/test_mcp/ -v` passes with all MCP tests green
- Overall test coverage is 55%+ (up from 42%)
- MCP tool schema tests validate all four tool signatures
- No tests require actual audio hardware to pass (all use fixtures or mocks)
- CI pipeline passes with MCP tests included

## Parallel work
- MCP tool unit tests can be written alongside provider coverage improvements
- CI coverage threshold can be configured independently of test writing

## Phase dependencies
- Requires: Phase 2 (MCP server and tools must exist to test)

## Complexity
- Backend: M
- Frontend: N/A
- Infra: S

## Risks
- Mocking MCP server interactions may be complex -- use FastMCP's test utilities if available
- Increasing WhisperLive coverage may require mocking faster-whisper model loading (heavy dependency)
