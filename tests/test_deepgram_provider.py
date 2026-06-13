"""Tests for the Deepgram STT provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from champi_stt.core.response import TranscriptionResponse
from champi_stt.providers.deepgram.config import DeepgramConfig
from champi_stt.providers.deepgram.exceptions import DeepgramAPIError, DeepgramAuthError
from champi_stt.providers.deepgram.provider import DeepgramProvider

_SAMPLE_RESPONSE = {
    "metadata": {"duration": 3.0},
    "results": {
        "channels": [
            {
                "detected_language": "en",
                "alternatives": [
                    {
                        "transcript": "hello deepgram",
                        "confidence": 0.98,
                        "words": [
                            {
                                "word": "hello",
                                "start": 0.0,
                                "end": 0.5,
                                "confidence": 0.99,
                            },
                            {
                                "word": "deepgram",
                                "start": 0.6,
                                "end": 1.2,
                                "confidence": 0.97,
                            },
                        ],
                    }
                ],
            }
        ]
    },
}


@pytest.fixture
def config():
    return DeepgramConfig(api_key="test-key", model="nova-2")


@pytest.fixture
def provider(config):
    return DeepgramProvider(config)


class TestDeepgramConfig:
    def test_config_defaults(self):
        cfg = DeepgramConfig(api_key="k")
        assert cfg.model == "nova-2"
        assert cfg.smart_format is True
        assert cfg.language is None

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPGRAM_API_KEY", "env-key")
        monkeypatch.setenv("DEEPGRAM_MODEL", "nova-2")
        cfg = DeepgramConfig.from_env()
        assert cfg.api_key == "env-key"
        assert cfg.model == "nova-2"


class TestDeepgramProvider:
    def test_provider_name(self, provider):
        assert provider.name == "Deepgram"
        assert not provider.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_missing_key(self):
        p = DeepgramProvider(DeepgramConfig(api_key=""))
        with pytest.raises(DeepgramAuthError):
            await p.initialize()

    @pytest.mark.asyncio
    async def test_initialize_missing_httpx(self, config):
        p = DeepgramProvider(config)
        with (
            patch("champi_stt.providers.deepgram.provider.HTTPX_AVAILABLE", False),
            pytest.raises(ImportError),
        ):
            await p.initialize()

    @pytest.mark.asyncio
    async def test_initialize_success(self, config):
        mock_httpx = MagicMock()
        mock_client = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_client

        p = DeepgramProvider(config)
        with (
            patch("champi_stt.providers.deepgram.provider.HTTPX_AVAILABLE", True),
            patch("champi_stt.providers.deepgram.provider.httpx", mock_httpx),
        ):
            await p.initialize()

        assert p.is_initialized

    @pytest.mark.asyncio
    async def test_shutdown(self, config):
        mock_client = AsyncMock()
        p = DeepgramProvider(config)
        p._initialized = True
        p._http = mock_client

        await p.shutdown()

        assert not p.is_initialized
        assert p._http is None
        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_bytes(self, config):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _SAMPLE_RESPONSE

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        p = DeepgramProvider(config)
        p._initialized = True
        p._http = mock_client

        result = await p.transcribe(b"\x00" * 100)

        assert isinstance(result, TranscriptionResponse)
        assert result.text == "hello deepgram"
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_transcribe_file(self, tmp_path, config):
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _SAMPLE_RESPONSE

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        p = DeepgramProvider(config)
        p._initialized = True
        p._http = mock_client

        result = await p.transcribe(str(audio_file))
        assert result.text == "hello deepgram"

    @pytest.mark.asyncio
    async def test_transcribe_numpy(self, config):
        audio = np.zeros(16000, dtype=np.float32)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _SAMPLE_RESPONSE

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        p = DeepgramProvider(config)
        p._initialized = True
        p._http = mock_client

        import soundfile as sf_mod

        with (
            patch("champi_stt.providers.deepgram.provider.SOUNDFILE_AVAILABLE", True),
            patch("champi_stt.providers.deepgram.provider.sf", sf_mod),
        ):
            result = await p.transcribe(audio)

        assert isinstance(result, TranscriptionResponse)

    @pytest.mark.asyncio
    async def test_api_error_on_bad_response(self, config):
        p = DeepgramProvider(config)
        p._initialized = True
        with pytest.raises(DeepgramAPIError):
            p._parse_response({})

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        mock_httpx = MagicMock()
        mock_client = AsyncMock()
        mock_httpx.AsyncClient.return_value = mock_client

        with (
            patch("champi_stt.providers.deepgram.provider.HTTPX_AVAILABLE", True),
            patch("champi_stt.providers.deepgram.provider.httpx", mock_httpx),
        ):
            async with DeepgramProvider(config) as p:
                assert p.is_initialized
        assert not p.is_initialized
