"""Integration test: verify the MCP server startup and JSON-RPC initialize handshake.

Uses the official ``mcp`` client library (``stdio_client`` + ``ClientSession``) to
spawn ``champi-stt-mcp`` as a child process, perform the full MCP initialize
handshake, and assert the expected response fields.

Why ``stdio_client`` instead of raw ``subprocess.Popen``?
The MCP stdio transport is built on ``anyio`` async streams (``anyio.open_process``).
Using the MCP client library guarantees the same framing and session lifecycle that
real MCP hosts use, making the test a true end-to-end integration check.

Performance note: tests are grouped so that the server is spawned only twice for
the full module — once for handshake assertions and once for tool assertions.
``anyio.fail_after`` is used inside each individual test (not in fixtures) to avoid
cancel-scope task-crossing errors with pytest-asyncio.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import InitializeResult, ListToolsResult

# Per-session connection timeout in seconds.
_TIMEOUT = 30


def _server_params() -> StdioServerParameters:
    """Return ``StdioServerParameters`` pointing at the installed entry-point.

    Prefers ``champi-stt-mcp`` in the same ``bin/`` directory as the running
    interpreter so the test always picks up the virtualenv's copy of the server.
    """
    entry = Path(sys.executable).parent / "champi-stt-mcp"
    if entry.exists():
        return StdioServerParameters(command=str(entry), args=[])
    return StdioServerParameters(command="champi-stt-mcp", args=[])


# ---------------------------------------------------------------------------
# Module-level data holders — populated by the class-scope setup tests.
# ---------------------------------------------------------------------------


class _SharedData:
    """Container for data collected during the integration run."""

    init_result: InitializeResult | None = None
    tools_result: ListToolsResult | None = None


_data = _SharedData()


# ---------------------------------------------------------------------------
# Handshake tests — single subprocess, assertions run after context exits.
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMCPServerHandshake:
    """Verify the MCP initialize handshake via a real server subprocess."""

    @pytest.fixture(autouse=True, scope="class")
    def _run_handshake(self) -> None:
        """Spawn the server once for all handshake tests and capture the result."""
        import asyncio

        async def _connect() -> InitializeResult:
            async with (
                stdio_client(_server_params()) as (rs, ws),
                ClientSession(rs, ws) as session,
            ):
                return await session.initialize()

        # Run the connection in a fresh event loop so it is isolated from
        # pytest-asyncio's loop and anyio cancel scopes don't cross tasks.
        loop = asyncio.new_event_loop()
        try:
            _data.init_result = loop.run_until_complete(
                asyncio.wait_for(_connect(), timeout=_TIMEOUT)
            )
        finally:
            loop.close()

    def test_initialize_returns_result(self) -> None:
        """``session.initialize()`` returns a non-None result."""
        assert _data.init_result is not None

    def test_server_info_name_is_champi_stt(self) -> None:
        """``serverInfo.name`` identifies the server as ``"champi-stt"``."""
        assert _data.init_result is not None
        assert _data.init_result.serverInfo.name == "champi-stt"

    def test_server_info_version_is_non_empty(self) -> None:
        """``serverInfo.version`` is a non-empty string."""
        assert _data.init_result is not None
        assert _data.init_result.serverInfo.version
        assert isinstance(_data.init_result.serverInfo.version, str)

    def test_protocol_version_is_non_empty(self) -> None:
        """``protocolVersion`` is reported by the server."""
        assert _data.init_result is not None
        assert _data.init_result.protocolVersion
        assert isinstance(_data.init_result.protocolVersion, str)

    def test_capabilities_present_in_result(self) -> None:
        """``capabilities`` field is present in the initialize result."""
        assert _data.init_result is not None
        assert _data.init_result.capabilities is not None


# ---------------------------------------------------------------------------
# Tool-registration tests — second subprocess, assertions run synchronously.
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMCPServerTools:
    """Verify the four tools are registered and visible after initialization."""

    @pytest.fixture(autouse=True, scope="class")
    def _run_list_tools(self) -> None:
        """Spawn the server once for all tool tests and capture the tools list."""
        import asyncio

        async def _connect() -> ListToolsResult:
            async with (
                stdio_client(_server_params()) as (rs, ws),
                ClientSession(rs, ws) as session,
            ):
                await session.initialize()
                return await session.list_tools()

        loop = asyncio.new_event_loop()
        try:
            _data.tools_result = loop.run_until_complete(
                asyncio.wait_for(_connect(), timeout=_TIMEOUT)
            )
        finally:
            loop.close()

    def _tool_names(self) -> set[str]:
        assert _data.tools_result is not None
        return {t.name for t in _data.tools_result.tools}

    def test_list_tools_returns_results(self) -> None:
        """``list_tools()`` returns at least one tool."""
        assert _data.tools_result is not None
        assert len(_data.tools_result.tools) > 0

    def test_list_providers_tool_registered(self) -> None:
        """The ``list_providers`` tool is registered on the server."""
        assert "list_providers" in self._tool_names()

    def test_transcribe_audio_tool_registered(self) -> None:
        """The ``transcribe_audio`` tool is registered on the server."""
        assert "transcribe_audio" in self._tool_names()

    def test_detect_language_tool_registered(self) -> None:
        """The ``detect_language`` tool is registered on the server."""
        assert "detect_language" in self._tool_names()

    def test_get_provider_status_tool_registered(self) -> None:
        """The ``get_provider_status`` tool is registered on the server."""
        assert "get_provider_status" in self._tool_names()

    def test_listen_once_tool_registered(self) -> None:
        """The ``listen_once_tool`` tool is registered on the server."""
        assert "listen_once_tool" in self._tool_names()

    def test_exactly_five_tools_registered(self) -> None:
        """Exactly the five expected tools are registered (no extras, no missing)."""
        assert self._tool_names() == {
            "list_providers",
            "get_provider_status",
            "transcribe_audio",
            "detect_language",
            "listen_once_tool",
        }
