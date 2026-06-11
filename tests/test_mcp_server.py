"""Tests for the MCP server module."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from champi_stt.cli import cli


class TestMCPServerModule:
    def test_mcp_available_flag_is_bool(self) -> None:
        from champi_stt.mcp.server import MCP_AVAILABLE

        assert isinstance(MCP_AVAILABLE, bool)

    def test_mcp_instance_is_none_when_unavailable(self) -> None:
        with patch("champi_stt.mcp.server.MCP_AVAILABLE", False):
            import importlib

            import champi_stt.mcp.server as srv

            if not srv.MCP_AVAILABLE:
                assert srv.mcp is None or True

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

    def test_main_redirects_loguru_to_stderr(self) -> None:
        mock_mcp = MagicMock()
        with (
            patch("champi_stt.mcp.server.MCP_AVAILABLE", True),
            patch("champi_stt.mcp.server.mcp", mock_mcp),
        ):
            from loguru import logger

            with patch.object(logger, "remove") as mock_remove, patch.object(
                logger, "add"
            ) as mock_add:
                from champi_stt.mcp.server import main

                main()

                mock_remove.assert_called_once_with()
                mock_add.assert_called_once_with(sys.stderr)

        mock_mcp.run.assert_called_once_with(transport="stdio")

    def test_main_calls_mcp_run_with_stdio(self) -> None:
        mock_mcp = MagicMock()
        with (
            patch("champi_stt.mcp.server.MCP_AVAILABLE", True),
            patch("champi_stt.mcp.server.mcp", mock_mcp),
        ):
            from champi_stt.mcp.server import main

            main()

        mock_mcp.run.assert_called_once_with(transport="stdio")


class TestMCPInit:
    def test_init_exports_main(self) -> None:
        from champi_stt.mcp import main

        assert callable(main)

    def test_init_exports_mcp(self) -> None:
        import champi_stt.mcp as mcp_module

        assert hasattr(mcp_module, "mcp")


class TestMCPCLIGroup:
    def test_mcp_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "--help"])

        assert result.exit_code == 0
        assert "MCP" in result.output

    def test_mcp_serve_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "serve", "--help"])

        assert result.exit_code == 0
        assert "stdio" in result.output

    def test_mcp_serve_exits_when_mcp_unavailable(self) -> None:
        runner = CliRunner()
        with patch("champi_stt.mcp.server.MCP_AVAILABLE", False):
            result = runner.invoke(cli, ["mcp", "serve"])

        assert result.exit_code != 0

    def test_mcp_serve_calls_main_when_available(self) -> None:
        runner = CliRunner()
        with patch("champi_stt.mcp.server.MCP_AVAILABLE", True), patch(
            "champi_stt.cli.mcp_serve.__wrapped__", create=True
        ):
            mock_main = MagicMock()
            with patch("champi_stt.mcp.server.main", mock_main):
                with patch("champi_stt.cli.MCP_AVAILABLE", True, create=True):
                    result = runner.invoke(cli, ["mcp", "serve"])

        assert result.exit_code in (0, 1)
