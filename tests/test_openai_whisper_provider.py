"""Tests for the OpenAI Whisper STT provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from champi_stt.core.response import TranscriptionResponse
from champi_stt.providers.openai_whisper.config import OpenAIWhisperConfig
from champi_stt.providers.openai_whisper.exceptions import (
    OpenAIWhisperAuthError,
    OpenAIWhisperFileSizeError,
)
from champi_stt.providers.openai_whisper.provider import OpenAIWhisperProvider


@pytest.fixture
def config():
    return OpenAIWhisperConfig(api_key="test-key", model="whisper-1")


@pytest.fixture
def provider(config):
    return OpenAIWhisperProvider(config)


class TestOpenAIWhisperConfig:
    def test_config_defaults(self):
        cfg = OpenAIWhisperConfig(api_key="k")
        assert cfg.model == "whisper-1"
        assert cfg.temperature == 0.0
        assert cfg.language is None

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        monkeypatch.setenv("OPENAI_WHISPER_MODEL", "whisper-1")
        cfg = OpenAIWhisperConfig.from_env()
        assert cfg.api_key == "env-key"
        assert cfg.model == "whisper-1"


class TestOpenAIWhisperProvider:
    def test_provider_name(self, provider):
        assert provider.name == "OpenAI Whisper"
        assert not provider.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_missing_key(self):
        p = OpenAIWhisperProvider(OpenAIWhisperConfig(api_key=""))
        with pytest.raises(OpenAIWhisperAuthError):
            await p.initialize()

    @pytest.mark.asyncio
    async def test_initialize_missing_openai_package(self, config):
        p = OpenAIWhisperProvider(config)
        with patch(
            "champi_stt.providers.openai_whisper.provider.OPENAI_AVAILABLE", False
        ):
            with pytest.raises(ImportError):
                await p.initialize()

    @pytest.mark.asyncio
    async def test_initialize_success(self, config):
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.AsyncOpenAI.return_value = mock_client

        p = OpenAIWhisperProvider(config)
        with patch("champi_stt.providers.openai_whisper.provider.OPENAI_AVAILABLE", True):
            with patch("champi_stt.providers.openai_whisper.provider.openai", mock_openai):
                await p.initialize()

        assert p.is_initialized
        assert p._client is mock_client

    @pytest.mark.asyncio
    async def test_shutdown(self, config):
        p = OpenAIWhisperProvider(config)
        p._initialized = True
        p._client = MagicMock()
        await p.shutdown()
        assert not p.is_initialized
        assert p._client is None

    @pytest.mark.asyncio
    async def test_transcribe_file(self, tmp_path, config):
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)

        mock_response = MagicMock()
        mock_response.text = "hello world"
        mock_response.language = "en"
        mock_response.duration = 2.5
        mock_response.segments = []

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        p = OpenAIWhisperProvider(config)
        p._initialized = True
        p._client = mock_client

        result = await p.transcribe(str(audio_file))

        assert isinstance(result, TranscriptionResponse)
        assert result.text == "hello world"
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_transcribe_numpy(self, config):
        audio = np.zeros(16000, dtype=np.float32)

        mock_response = MagicMock()
        mock_response.text = "silence"
        mock_response.language = "en"
        mock_response.duration = 1.0
        mock_response.segments = []

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        p = OpenAIWhisperProvider(config)
        p._initialized = True
        p._client = mock_client

        with patch(
            "champi_stt.providers.openai_whisper.provider.SOUNDFILE_AVAILABLE", True
        ):
            import soundfile as sf_mod
            with patch(
                "champi_stt.providers.openai_whisper.provider.sf", sf_mod
            ):
                result = await p.transcribe(audio)

        assert isinstance(result, TranscriptionResponse)
        assert result.text == "silence"

    @pytest.mark.asyncio
    async def test_file_size_limit(self, tmp_path, config):
        big_file = tmp_path / "big.wav"
        big_file.write_bytes(b"\x00" * (26 * 1024 * 1024))

        p = OpenAIWhisperProvider(config)
        p._initialized = True
        p._client = MagicMock()

        with pytest.raises(OpenAIWhisperFileSizeError):
            await p.transcribe(str(big_file))

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        mock_openai = MagicMock()
        mock_openai.AsyncOpenAI.return_value = MagicMock()

        with patch("champi_stt.providers.openai_whisper.provider.OPENAI_AVAILABLE", True):
            with patch("champi_stt.providers.openai_whisper.provider.openai", mock_openai):
                async with OpenAIWhisperProvider(config) as p:
                    assert p.is_initialized
        assert not p.is_initialized
