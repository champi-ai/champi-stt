"""Tests for command executor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from champi_stt.assistant.commands.executor import ActionType, CommandAction, CommandExecutor


@pytest.fixture
def executor():
    return CommandExecutor()


class TestExecuteShell:
    @pytest.mark.asyncio
    async def test_successful_command(self, executor):
        with patch("asyncio.create_subprocess_shell") as mock_proc:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"hello\n", b""))
            mock_proc.return_value = mock_process

            result = await executor.execute_shell("echo hello")
            assert result["success"] is True
            assert result["stdout"] == "hello\n"

    @pytest.mark.asyncio
    async def test_failed_command(self, executor):
        with patch("asyncio.create_subprocess_shell") as mock_proc:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b"error\n"))
            mock_proc.return_value = mock_process

            result = await executor.execute_shell("false")
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_command_with_kwargs(self, executor):
        with patch("asyncio.create_subprocess_shell") as mock_proc:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"world\n", b""))
            mock_proc.return_value = mock_process

            result = await executor.execute_shell("echo {message}", message="world")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_exception_handling(self, executor):
        with patch("asyncio.create_subprocess_shell", side_effect=Exception("fail")):
            result = await executor.execute_shell("echo hi")
            assert result["success"] is False
            assert "fail" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_kwarg_raises(self, executor):
        # Providing a kwarg that doesn't match the template key raises KeyError
        with pytest.raises(KeyError):
            await executor.execute_shell("echo {missing_key}", wrong_key="value")


class TestExecutePython:
    @pytest.mark.asyncio
    async def test_async_function(self, executor):
        result = await executor.execute_python("asyncio.sleep", delay=0)
        assert result is None

    @pytest.mark.asyncio
    async def test_sync_function(self, executor):
        import os
        result = await executor.execute_python("os.getcwd")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_invalid_path_raises(self, executor):
        with pytest.raises(Exception):
            await executor.execute_python("nonexistent.module.function")


class TestExecuteAction:
    @pytest.mark.asyncio
    async def test_shell_action(self, executor):
        action = CommandAction(type=ActionType.SHELL, value="echo hi")
        with patch("asyncio.create_subprocess_shell") as mock_proc:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"hi\n", b""))
            mock_proc.return_value = mock_process

            result = await executor.execute_action(action)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_python_action(self, executor):
        action = CommandAction(type=ActionType.PYTHON, value="asyncio.sleep")
        result = await executor.execute_action(action, delay=0)
        assert result is None
