"""Tests for built-in voice commands."""

from unittest.mock import patch

import pytest

from champi_stt.assistant.commands.builtin import (
    open_application,
    open_url,
    play_pause_media,
    register_builtin_commands,
    restart_assistant,
    say_date,
    say_goodbye,
    say_hello,
    say_thanks,
    say_time,
    set_volume,
    shutdown_assistant,
    web_search,
)
from champi_stt.assistant.commands.registry import CommandRegistry


class TestTimeCommands:
    @pytest.mark.asyncio
    async def test_say_time_returns_string(self):
        result = await say_time()
        assert isinstance(result, str)
        assert "time" in result.lower() or ":" in result

    @pytest.mark.asyncio
    async def test_say_date_returns_string(self):
        result = await say_date()
        assert isinstance(result, str)
        assert len(result) > 5


class TestSystemCommands:
    @pytest.mark.asyncio
    async def test_shutdown_returns_dict(self):
        result = await shutdown_assistant()
        assert result["action"] == "shutdown"

    @pytest.mark.asyncio
    async def test_restart_returns_dict(self):
        result = await restart_assistant()
        assert result["action"] == "restart"


class TestGreetings:
    @pytest.mark.asyncio
    async def test_say_hello(self):
        result = await say_hello()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_say_goodbye(self):
        result = await say_goodbye()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_say_thanks(self):
        result = await say_thanks()
        assert isinstance(result, str)


class TestWebCommands:
    @pytest.mark.asyncio
    async def test_web_search_opens_browser(self):
        with patch("webbrowser.open") as mock_open:
            result = await web_search("python asyncio")
            mock_open.assert_called_once()
            assert "python asyncio" in result

    @pytest.mark.asyncio
    async def test_open_url(self):
        with patch("webbrowser.open") as mock_open:
            result = await open_url("https://example.com")
            mock_open.assert_called_once_with("https://example.com")
            assert isinstance(result, str)


class TestVolumeControl:
    @pytest.mark.asyncio
    async def test_set_volume_out_of_range(self):
        result = await set_volume("150")
        assert "0" in result or "100" in result

    @pytest.mark.asyncio
    async def test_set_volume_linux(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run") as mock_run,
        ):
            result = await set_volume("50")
            mock_run.assert_called_once()
            assert "50" in result

    @pytest.mark.asyncio
    async def test_set_volume_darwin(self):
        with (
            patch("platform.system", return_value="Darwin"),
            patch("subprocess.run") as mock_run,
        ):
            await set_volume("75")
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_volume_error_handling(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run", side_effect=Exception("fail")),
        ):
            result = await set_volume("50")
            assert isinstance(result, str)


class TestApplicationCommands:
    @pytest.mark.asyncio
    async def test_open_application_linux(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch("subprocess.Popen") as mock_popen,
        ):
            result = await open_application("firefox")
            mock_popen.assert_called_once()
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_open_application_error(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch("subprocess.Popen", side_effect=Exception("not found")),
        ):
            result = await open_application("nonexistent_app")
            assert "could not" in result.lower()


class TestMediaControl:
    @pytest.mark.asyncio
    async def test_play_pause_linux(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run") as mock_run,
        ):
            result = await play_pause_media()
            mock_run.assert_called_once()
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_play_pause_error(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run", side_effect=Exception("fail")),
        ):
            result = await play_pause_media()
            assert isinstance(result, str)


class TestRegisterBuiltinCommands:
    def test_registers_commands(self):
        registry = CommandRegistry()
        register_builtin_commands(registry)
        assert len(registry) > 5

    @pytest.mark.asyncio
    async def test_registered_commands_work(self):
        registry = CommandRegistry()
        register_builtin_commands(registry)
        result = await registry.execute("hello")
        assert result is not None
