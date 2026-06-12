"""Tests for the MCP server — factory, lifespan, tools, and CLI."""

from __future__ import annotations

import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from champi_stt.cli import cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider(
    *,
    model_info: dict | None = None,
    transcribe_result: str | dict = "hello world",
    detect_result: tuple = ("en", 0.99, []),
    initialize_raises: Exception | None = None,
    transcribe_raises: Exception | None = None,
    detect_raises: Exception | None = None,
) -> MagicMock:
    prov = MagicMock()
    prov.initialize = AsyncMock(side_effect=initialize_raises)
    prov.shutdown = AsyncMock()
    prov.transcribe = AsyncMock(
        side_effect=transcribe_raises, return_value=transcribe_result
    )
    prov.detect_language = AsyncMock(
        side_effect=detect_raises, return_value=detect_result
    )
    prov.get_model_info = AsyncMock(
        return_value=model_info or {"status": "loaded", "provider": "mock"}
    )
    return prov


def _raw(call_tool_result: tuple) -> dict:
    """Extract the structured result dict from FastMCP call_tool return value."""
    return call_tool_result[1]


@pytest.fixture()
def server():
    """Fresh FastMCP server instance per test — matches champi-imgui factory pattern."""
    from champi_stt.mcp.server import create_mcp_server

    return create_mcp_server()


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    def test_mcp_available_flag_is_bool(self) -> None:
        from champi_stt.mcp.server import MCP_AVAILABLE

        assert isinstance(MCP_AVAILABLE, bool)

    def test_require_mcp_raises_when_unavailable(self) -> None:
        with patch("champi_stt.mcp.server.MCP_AVAILABLE", False):
            from champi_stt.mcp.server import _require_mcp

            with pytest.raises(ImportError, match="mcp"):
                _require_mcp()

    def test_main_raises_import_error_when_mcp_unavailable(self) -> None:
        with patch("champi_stt.mcp.server.MCP_AVAILABLE", False):
            from champi_stt.mcp.server import main

            with pytest.raises(ImportError, match="mcp"):
                main()


# ---------------------------------------------------------------------------
# Factory and lifespan (champi-imgui pattern)
# ---------------------------------------------------------------------------


class TestCreateMcpServer:
    def test_returns_fastmcp_instance(self, server: MagicMock) -> None:
        from mcp.server.fastmcp import FastMCP

        assert isinstance(server, FastMCP)

    def test_registers_all_four_tools(self, server: MagicMock) -> None:
        tools = list(server._tool_manager._tools.keys())
        assert "list_providers" in tools
        assert "get_provider_status" in tools
        assert "transcribe_audio" in tools
        assert "detect_language" in tools

    def test_exposes_state_for_test_injection(self, server: MagicMock) -> None:
        assert hasattr(server, "_state")
        assert "provider" in server._state

    def test_provider_starts_as_none(self, server: MagicMock) -> None:
        assert server._state["provider"] is None

    @pytest.mark.asyncio
    async def test_lifespan_shuts_down_provider_on_exit(
        self, server: MagicMock
    ) -> None:
        mock_prov = _make_provider()
        server._state["provider"] = mock_prov

        async with server.settings.lifespan(server):
            pass

        mock_prov.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_lifespan_clears_provider_ref_after_shutdown(
        self, server: MagicMock
    ) -> None:
        mock_prov = _make_provider()
        server._state["provider"] = mock_prov

        async with server.settings.lifespan(server):
            pass

        assert server._state["provider"] is None

    @pytest.mark.asyncio
    async def test_lifespan_suppresses_shutdown_errors(self, server: MagicMock) -> None:
        mock_prov = _make_provider()
        mock_prov.shutdown = AsyncMock(side_effect=RuntimeError("GPU gone"))
        server._state["provider"] = mock_prov

        async with server.settings.lifespan(server):
            pass  # should not raise

    @pytest.mark.asyncio
    async def test_lifespan_noop_when_no_provider(self, server: MagicMock) -> None:
        assert server._state["provider"] is None
        async with server.settings.lifespan(server):
            pass  # should not raise


# ---------------------------------------------------------------------------
# Tool: list_providers
# ---------------------------------------------------------------------------


class TestToolListProviders:
    @pytest.mark.asyncio
    async def test_returns_nonempty_list(self, server: MagicMock) -> None:
        result = _raw(await server.call_tool("list_providers", {}))
        assert isinstance(result["result"], list)
        assert len(result["result"]) > 0

    @pytest.mark.asyncio
    async def test_contains_whisperlive(self, server: MagicMock) -> None:
        result = _raw(await server.call_tool("list_providers", {}))
        assert "whisperlive" in result["result"]


# ---------------------------------------------------------------------------
# Tool: get_provider_status
# ---------------------------------------------------------------------------


class TestToolGetProviderStatus:
    @pytest.mark.asyncio
    async def test_returns_model_info(self, server: MagicMock) -> None:
        prov = _make_provider(model_info={"status": "loaded", "provider": "mock"})
        with patch("champi_stt.get_provider", return_value=prov):
            result = _raw(
                await server.call_tool(
                    "get_provider_status", {"provider": "whisperlive"}
                )
            )
        assert result["status"] == "loaded"

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_error_dict(self, server: MagicMock) -> None:
        with patch("champi_stt.get_provider", side_effect=ValueError("unknown")):
            result = _raw(
                await server.call_tool("get_provider_status", {"provider": "bad"})
            )
        assert result["error"] is True


# ---------------------------------------------------------------------------
# Tool: transcribe_audio
# ---------------------------------------------------------------------------


class TestToolTranscribeAudio:
    @pytest.mark.asyncio
    async def test_missing_file_returns_error_string(self, server: MagicMock) -> None:
        result = _raw(
            await server.call_tool(
                "transcribe_audio", {"audio_path": "/no/such/file.wav"}
            )
        )
        assert "error" in result["result"].lower()

    @pytest.mark.asyncio
    async def test_transcribes_existing_file(self, server: MagicMock) -> None:
        prov = _make_provider(transcribe_result="hello world")
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            result = _raw(
                await server.call_tool("transcribe_audio", {"audio_path": f.name})
            )
        assert result["result"] == "hello world"

    @pytest.mark.asyncio
    async def test_provider_not_reinited_on_second_call(
        self, server: MagicMock
    ) -> None:
        prov = _make_provider(transcribe_result="ok")
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            await server.call_tool("transcribe_audio", {"audio_path": f.name})
            await server.call_tool("transcribe_audio", {"audio_path": f.name})
        prov.initialize.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_env_var_selects_provider(
        self, server: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHAMPI_STT_PROVIDER", "openai_whisper")
        prov = _make_provider()
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov) as mock_get,
        ):
            await server.call_tool("transcribe_audio", {"audio_path": f.name})
        mock_get.assert_called_with("openai_whisper")

    @pytest.mark.asyncio
    async def test_explicit_provider_overrides_env_var(
        self, server: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHAMPI_STT_PROVIDER", "openai_whisper")
        prov = _make_provider()
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov) as mock_get,
        ):
            await server.call_tool(
                "transcribe_audio", {"audio_path": f.name, "provider": "whisperlive"}
            )
        mock_get.assert_called_with("whisperlive")


# ---------------------------------------------------------------------------
# Tool: detect_language
# ---------------------------------------------------------------------------


class TestToolDetectLanguage:
    @pytest.mark.asyncio
    async def test_missing_file_returns_error_dict(self, server: MagicMock) -> None:
        result = _raw(
            await server.call_tool(
                "detect_language", {"audio_path": "/no/such/file.wav"}
            )
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_returns_language_and_probability(self, server: MagicMock) -> None:
        prov = _make_provider(detect_result=("fr", 0.87, []))
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            result = _raw(
                await server.call_tool("detect_language", {"audio_path": f.name})
            )
        assert result["language"] == "fr"
        assert result["probability"] == pytest.approx(0.87)


# ---------------------------------------------------------------------------
# main() — transport and loguru redirect
# ---------------------------------------------------------------------------


class TestMain:
    def test_redirects_loguru_to_stderr(self) -> None:
        mock_mcp = MagicMock()
        with patch("champi_stt.mcp.server.mcp", mock_mcp):
            from loguru import logger

            with (
                patch.object(logger, "remove") as mock_remove,
                patch.object(logger, "add") as mock_add,
            ):
                from champi_stt.mcp.server import main

                main()

            mock_remove.assert_called_once_with()
            mock_add.assert_called_once_with(sys.stderr)

    def test_calls_run_with_stdio_default(self) -> None:
        mock_mcp = MagicMock()
        with patch("champi_stt.mcp.server.mcp", mock_mcp):
            from champi_stt.mcp.server import main

            main()
        mock_mcp.run.assert_called_once_with(transport="stdio")

    def test_sets_host_port_for_sse(self) -> None:
        mock_mcp = MagicMock()
        mock_mcp.settings = MagicMock()
        with patch("champi_stt.mcp.server.mcp", mock_mcp):
            from champi_stt.mcp.server import main

            main(transport="sse", host="0.0.0.0", port=9000)
        assert mock_mcp.settings.host == "0.0.0.0"
        assert mock_mcp.settings.port == 9000
        mock_mcp.run.assert_called_once_with(transport="sse")


# ---------------------------------------------------------------------------
# __init__ exports
# ---------------------------------------------------------------------------


class TestMCPInit:
    def test_exports_main(self) -> None:
        from champi_stt.mcp import main

        assert callable(main)

    def test_exports_mcp(self) -> None:
        import champi_stt.mcp as m

        assert hasattr(m, "mcp")

    def test_exports_create_mcp_server(self) -> None:
        from champi_stt.mcp import create_mcp_server

        assert callable(create_mcp_server)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestMCPCLI:
    def test_mcp_help(self) -> None:
        result = CliRunner().invoke(cli, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "MCP" in result.output

    def test_serve_help_shows_transport(self) -> None:
        result = CliRunner().invoke(cli, ["mcp", "serve", "--help"])
        assert result.exit_code == 0
        assert "stdio" in result.output
        assert "sse" in result.output

    def test_serve_help_shows_host_port(self) -> None:
        result = CliRunner().invoke(cli, ["mcp", "serve", "--help"])
        assert "--host" in result.output
        assert "--port" in result.output

    def test_serve_rejects_invalid_transport(self) -> None:
        with patch("champi_stt.mcp.server.MCP_AVAILABLE", True):
            result = CliRunner().invoke(cli, ["mcp", "serve", "--transport", "grpc"])
        assert result.exit_code != 0

    def test_serve_passes_args_to_main(self) -> None:
        mock_main = MagicMock()
        with patch("champi_stt.mcp.server.main", mock_main):
            CliRunner().invoke(
                cli,
                [
                    "mcp",
                    "serve",
                    "--transport",
                    "sse",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "9999",
                ],
            )
        mock_main.assert_called_once_with(transport="sse", host="0.0.0.0", port=9999)
