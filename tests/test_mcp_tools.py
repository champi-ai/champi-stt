"""Tests for MCP tool definitions in champi_stt.mcp.tools."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
    """Return a mock provider with sensible defaults."""
    prov = MagicMock()
    prov.initialize = AsyncMock(side_effect=initialize_raises)
    prov.shutdown = AsyncMock()
    prov.transcribe = AsyncMock(
        side_effect=transcribe_raises,
        return_value=transcribe_result,
    )
    prov.detect_language = AsyncMock(
        side_effect=detect_raises,
        return_value=detect_result,
    )
    prov.get_model_info = AsyncMock(
        return_value=model_info or {"status": "loaded", "provider": "mock"}
    )
    return prov


# ---------------------------------------------------------------------------
# list_providers
# ---------------------------------------------------------------------------


class TestListProviders:
    @pytest.mark.asyncio
    async def test_returns_list_of_strings(self) -> None:
        from champi_stt.mcp.tools import list_providers

        result = await list_providers()

        assert isinstance(result, list)
        assert all(isinstance(name, str) for name in result)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_contains_whisperlive(self) -> None:
        from champi_stt.mcp.tools import list_providers

        result = await list_providers()

        assert "whisperlive" in result


# ---------------------------------------------------------------------------
# get_provider_status
# ---------------------------------------------------------------------------


class TestGetProviderStatus:
    @pytest.mark.asyncio
    async def test_returns_model_info_dict(self) -> None:
        from champi_stt.mcp.tools import get_provider_status

        prov = _make_provider(model_info={"status": "loaded", "provider": "mock"})
        with patch("champi_stt.get_provider", return_value=prov):
            result = await get_provider_status("whisperlive")

        assert result == {"status": "loaded", "provider": "mock"}

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_error_dict(self) -> None:
        from champi_stt.mcp.tools import get_provider_status

        with patch(
            "champi_stt.get_provider",
            side_effect=ValueError("Unknown provider type: 'bad'"),
        ):
            result = await get_provider_status("bad")

        assert result["error"] is True
        assert "error_type" in result
        assert "error_message" in result
        assert result["provider"] == "bad"

    @pytest.mark.asyncio
    async def test_get_model_info_raises_returns_error_dict(self) -> None:
        from champi_stt.mcp.tools import get_provider_status

        prov = _make_provider()
        prov.get_model_info = AsyncMock(side_effect=RuntimeError("model exploded"))
        with patch("champi_stt.get_provider", return_value=prov):
            result = await get_provider_status("whisperlive")

        assert result["error"] is True
        assert result["error_type"] == "RuntimeError"
        assert "model exploded" in result["error_message"]


# ---------------------------------------------------------------------------
# transcribe_audio
# ---------------------------------------------------------------------------


class TestTranscribeAudio:
    @pytest.mark.asyncio
    async def test_transcribes_existing_file_string_result(self) -> None:
        from champi_stt.mcp.tools import transcribe_audio

        prov = _make_provider(transcribe_result="the quick brown fox")
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                result = await transcribe_audio(f.name)

        assert result == "the quick brown fox"

    @pytest.mark.asyncio
    async def test_transcribes_existing_file_dict_result(self) -> None:
        from champi_stt.mcp.tools import transcribe_audio

        prov = _make_provider(transcribe_result={"text": "hello dict", "language": "en"})
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                result = await transcribe_audio(f.name)

        assert result == "hello dict"

    @pytest.mark.asyncio
    async def test_missing_file_returns_error_string(self) -> None:
        from champi_stt.mcp.tools import transcribe_audio

        result = await transcribe_audio("/tmp/does_not_exist_champi_test.wav")

        assert result.startswith("error:")
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_provider_exception_returns_error_string(self) -> None:
        from champi_stt.mcp.tools import transcribe_audio

        prov = _make_provider(transcribe_raises=RuntimeError("GPU OOM"))
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                result = await transcribe_audio(f.name)

        assert result.startswith("error:")
        assert "GPU OOM" in result

    @pytest.mark.asyncio
    async def test_shutdown_called_even_on_error(self) -> None:
        from champi_stt.mcp.tools import transcribe_audio

        prov = _make_provider(transcribe_raises=RuntimeError("boom"))
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                await transcribe_audio(f.name)

        prov.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_language_to_provider(self) -> None:
        from champi_stt.mcp.tools import transcribe_audio

        prov = _make_provider(transcribe_result="bonjour")
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                await transcribe_audio(f.name, language="fr")

        _call_kwargs = prov.transcribe.call_args
        assert _call_kwargs.kwargs.get("language") == "fr" or (
            len(_call_kwargs.args) >= 2 and _call_kwargs.args[1] == "fr"
        )

    @pytest.mark.asyncio
    async def test_initialize_raises_returns_error_string(self) -> None:
        from champi_stt.mcp.tools import transcribe_audio

        prov = _make_provider(initialize_raises=RuntimeError("init failed"))
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                result = await transcribe_audio(f.name)

        assert result.startswith("error:")
        assert "init failed" in result

    @pytest.mark.asyncio
    async def test_shutdown_called_when_initialize_raises(self) -> None:
        from champi_stt.mcp.tools import transcribe_audio

        prov = _make_provider(initialize_raises=RuntimeError("init failed"))
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                await transcribe_audio(f.name)

        prov.shutdown.assert_awaited_once()


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    @pytest.mark.asyncio
    async def test_returns_language_and_probability(self) -> None:
        from champi_stt.mcp.tools import detect_language

        prov = _make_provider(detect_result=("fr", 0.87, []))
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                result = await detect_language(f.name)

        assert result == {"language": "fr", "probability": 0.87}

    @pytest.mark.asyncio
    async def test_missing_file_returns_error_dict(self) -> None:
        from champi_stt.mcp.tools import detect_language

        result = await detect_language("/tmp/does_not_exist_champi_test.wav")

        assert result["error"] is True
        assert result["error_type"] == "FileNotFoundError"
        assert "not found" in result["error_message"]

    @pytest.mark.asyncio
    async def test_provider_exception_returns_error_dict(self) -> None:
        from champi_stt.mcp.tools import detect_language

        prov = _make_provider(detect_raises=RuntimeError("model error"))
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                result = await detect_language(f.name)

        assert result["error"] is True
        assert result["error_type"] == "RuntimeError"
        assert "model error" in result["error_message"]

    @pytest.mark.asyncio
    async def test_shutdown_called_even_on_error(self) -> None:
        from champi_stt.mcp.tools import detect_language

        prov = _make_provider(detect_raises=RuntimeError("boom"))
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                await detect_language(f.name)

        prov.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_initialize_raises_returns_error_dict(self) -> None:
        from champi_stt.mcp.tools import detect_language

        prov = _make_provider(initialize_raises=RuntimeError("init failed"))
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                result = await detect_language(f.name)

        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_shutdown_called_when_initialize_raises(self) -> None:
        from champi_stt.mcp.tools import detect_language

        prov = _make_provider(initialize_raises=RuntimeError("init failed"))
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with patch("champi_stt.get_provider", return_value=prov):
                await detect_language(f.name)

        prov.shutdown.assert_awaited_once()
