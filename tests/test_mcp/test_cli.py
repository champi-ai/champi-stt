"""Tests for the ``champi-stt mcp serve`` CLI entry point.

Uses Click's ``CliRunner`` to exercise the ``mcp serve`` subcommand without
starting a real server loop or requiring audio hardware.  The underlying
``main()`` function is mocked in all tests that would otherwise block on
stdin.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner, Result

from champi_stt.cli import cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke(*args: str) -> Result:
    """Invoke the top-level ``cli`` with *args* and return the result."""
    return CliRunner().invoke(cli, list(args))


# ---------------------------------------------------------------------------
# Help / discovery
# ---------------------------------------------------------------------------


class TestMCPServeHelp:
    """The ``mcp serve`` command is discoverable and self-documenting."""

    def test_mcp_group_exits_zero_on_help(self) -> None:
        result = _invoke("mcp", "--help")
        assert result.exit_code == 0

    def test_mcp_group_help_mentions_mcp(self) -> None:
        result = _invoke("mcp", "--help")
        assert "mcp" in result.output.lower()

    def test_serve_subcommand_visible_in_mcp_help(self) -> None:
        result = _invoke("mcp", "--help")
        assert "serve" in result.output

    def test_serve_help_exits_zero(self) -> None:
        result = _invoke("mcp", "serve", "--help")
        assert result.exit_code == 0

    def test_serve_help_lists_transport_option(self) -> None:
        result = _invoke("mcp", "serve", "--help")
        assert "--transport" in result.output

    def test_serve_help_shows_stdio_choice(self) -> None:
        result = _invoke("mcp", "serve", "--help")
        assert "stdio" in result.output

    def test_serve_help_shows_sse_choice(self) -> None:
        result = _invoke("mcp", "serve", "--help")
        assert "sse" in result.output

    def test_serve_help_lists_host_option(self) -> None:
        result = _invoke("mcp", "serve", "--help")
        assert "--host" in result.output

    def test_serve_help_lists_port_option(self) -> None:
        result = _invoke("mcp", "serve", "--help")
        assert "--port" in result.output


# ---------------------------------------------------------------------------
# Argument forwarding
# ---------------------------------------------------------------------------


class TestMCPServeArguments:
    """CLI arguments are correctly forwarded to ``champi_stt.mcp.server.main``."""

    def test_default_transport_is_stdio(self) -> None:
        mock_main = MagicMock()
        with patch("champi_stt.mcp.server.main", mock_main):
            _invoke("mcp", "serve")
        mock_main.assert_called_once_with(
            transport="stdio", host="localhost", port=8765
        )

    def test_explicit_stdio_transport(self) -> None:
        mock_main = MagicMock()
        with patch("champi_stt.mcp.server.main", mock_main):
            _invoke("mcp", "serve", "--transport", "stdio")
        mock_main.assert_called_once_with(
            transport="stdio", host="localhost", port=8765
        )

    def test_sse_transport_forwarded(self) -> None:
        mock_main = MagicMock()
        with patch("champi_stt.mcp.server.main", mock_main):
            _invoke("mcp", "serve", "--transport", "sse")
        mock_main.assert_called_once_with(transport="sse", host="localhost", port=8765)

    def test_custom_host_forwarded(self) -> None:
        mock_main = MagicMock()
        with patch("champi_stt.mcp.server.main", mock_main):
            _invoke("mcp", "serve", "--host", "0.0.0.0")
        _, kwargs = mock_main.call_args
        assert kwargs["host"] == "0.0.0.0"

    def test_custom_port_forwarded(self) -> None:
        mock_main = MagicMock()
        with patch("champi_stt.mcp.server.main", mock_main):
            _invoke("mcp", "serve", "--port", "9999")
        _, kwargs = mock_main.call_args
        assert kwargs["port"] == 9999

    def test_all_options_forwarded_together(self) -> None:
        mock_main = MagicMock()
        with patch("champi_stt.mcp.server.main", mock_main):
            _invoke(
                "mcp",
                "serve",
                "--transport",
                "sse",
                "--host",
                "192.168.1.1",
                "--port",
                "12345",
            )
        mock_main.assert_called_once_with(
            transport="sse", host="192.168.1.1", port=12345
        )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestMCPServeValidation:
    """CLI rejects invalid argument values before reaching ``main``."""

    def test_invalid_transport_is_rejected(self) -> None:
        result = _invoke("mcp", "serve", "--transport", "grpc")
        assert result.exit_code != 0

    def test_non_integer_port_is_rejected(self) -> None:
        result = _invoke("mcp", "serve", "--port", "notanumber")
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# MCP package not installed
# ---------------------------------------------------------------------------


class TestMCPServeWhenMCPUnavailable:
    """CLI exits with a clear error when the ``mcp`` package is absent."""

    def test_exits_nonzero_when_mcp_unavailable(self) -> None:
        with patch("champi_stt.mcp.server.MCP_AVAILABLE", False):
            result = _invoke("mcp", "serve")
        assert result.exit_code != 0

    def test_error_message_mentions_mcp_package(self) -> None:
        with patch("champi_stt.mcp.server.MCP_AVAILABLE", False):
            result = _invoke("mcp", "serve")
        # Output includes both stdout and stderr via mix_stderr default
        combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "mcp" in combined.lower()

    def test_error_message_mentions_install(self) -> None:
        with patch("champi_stt.mcp.server.MCP_AVAILABLE", False):
            result = _invoke("mcp", "serve")
        # Error guidance appears in the combined output
        assert "install" in result.output.lower()


# ---------------------------------------------------------------------------
# Clean startup (mocked main)
# ---------------------------------------------------------------------------


class TestMCPServeStartup:
    """Verify that a well-behaved main() results in a zero exit code."""

    def test_serve_exits_zero_when_main_returns(self) -> None:
        with patch("champi_stt.mcp.server.main", return_value=None):
            result = _invoke("mcp", "serve")
        assert result.exit_code == 0

    def test_serve_stdio_exits_zero_when_main_returns(self) -> None:
        with patch("champi_stt.mcp.server.main", return_value=None):
            result = _invoke("mcp", "serve", "--transport", "stdio")
        assert result.exit_code == 0

    @pytest.mark.parametrize("transport", ["stdio", "sse"])
    def test_serve_exits_zero_for_each_transport(self, transport: str) -> None:
        with patch("champi_stt.mcp.server.main", return_value=None):
            result = _invoke("mcp", "serve", "--transport", transport)
        assert result.exit_code == 0
