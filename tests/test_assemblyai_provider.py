"""Tests for the AssemblyAI STT provider."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from champi_stt.core.response import TranscriptionResponse
from champi_stt.providers.assemblyai.config import AssemblyAIConfig
from champi_stt.providers.assemblyai.exceptions import (
    AssemblyAIAuthError,
    AssemblyAIStreamingError,
)
from champi_stt.providers.assemblyai.provider import AssemblyAIProvider

_SAMPLE_COMPLETED = {
    "status": "completed",
    "text": "hello assemblyai",
    "language_code": "en",
    "audio_duration": 2.5,
    "language_confidence": 0.98,
    "words": [
        {"text": "hello", "start": 0, "end": 500},
        {"text": "assemblyai", "start": 600, "end": 1200},
    ],
}


@pytest.fixture
def config():
    return AssemblyAIConfig(api_key="test-key")


@pytest.fixture
def provider(config):
    return AssemblyAIProvider(config)


class TestAssemblyAIConfig:
    def test_defaults(self):
        cfg = AssemblyAIConfig(api_key="k")
        assert cfg.sample_rate == 16000
        assert cfg.encoding == "pcm_s16le"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("ASSEMBLYAI_API_KEY", "env-key")
        cfg = AssemblyAIConfig.from_env()
        assert cfg.api_key == "env-key"


class TestAssemblyAIProvider:
    def test_provider_name(self, provider):
        assert provider.name == "AssemblyAI"
        assert not provider.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_missing_key(self):
        p = AssemblyAIProvider(AssemblyAIConfig(api_key=""))
        with pytest.raises(AssemblyAIAuthError):
            await p.initialize()

    @pytest.mark.asyncio
    async def test_initialize_missing_httpx(self, config):
        p = AssemblyAIProvider(config)
        with patch("champi_stt.providers.assemblyai.provider.HTTPX_AVAILABLE", False):
            with pytest.raises(ImportError):
                await p.initialize()

    @pytest.mark.asyncio
    async def test_initialize_success(self, config):
        mock_httpx = MagicMock()
        mock_client = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_client

        p = AssemblyAIProvider(config)
        with patch("champi_stt.providers.assemblyai.provider.HTTPX_AVAILABLE", True):
            with patch("champi_stt.providers.assemblyai.provider.httpx", mock_httpx):
                await p.initialize()
        assert p.is_initialized

    @pytest.mark.asyncio
    async def test_shutdown(self, config):
        mock_client = AsyncMock()
        p = AssemblyAIProvider(config)
        p._initialized = True
        p._http = mock_client
        await p.shutdown()
        assert not p.is_initialized
        assert p._http is None
        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_bytes(self, config):
        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"upload_url": "https://cdn.assemblyai.com/upload/test"}

        submit_resp = MagicMock()
        submit_resp.raise_for_status = MagicMock()
        submit_resp.json.return_value = {"id": "abc123", "status": "queued"}

        poll_resp = MagicMock()
        poll_resp.raise_for_status = MagicMock()
        poll_resp.json.return_value = _SAMPLE_COMPLETED

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[upload_resp, submit_resp])
        mock_client.get = AsyncMock(return_value=poll_resp)

        p = AssemblyAIProvider(config)
        p._initialized = True
        p._http = mock_client

        result = await p.transcribe(b"\x00" * 100)
        assert isinstance(result, TranscriptionResponse)
        assert result.text == "hello assemblyai"
        assert result.language == "en"
        assert len(result.segments) == 2

    @pytest.mark.asyncio
    async def test_transcribe_file(self, tmp_path, config):
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)

        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"upload_url": "https://cdn.assemblyai.com/upload/test"}

        submit_resp = MagicMock()
        submit_resp.raise_for_status = MagicMock()
        submit_resp.json.return_value = {"id": "abc123", "status": "queued"}

        poll_resp = MagicMock()
        poll_resp.raise_for_status = MagicMock()
        poll_resp.json.return_value = _SAMPLE_COMPLETED

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[upload_resp, submit_resp])
        mock_client.get = AsyncMock(return_value=poll_resp)

        p = AssemblyAIProvider(config)
        p._initialized = True
        p._http = mock_client

        result = await p.transcribe(str(audio_file))
        assert result.text == "hello assemblyai"

    @pytest.mark.asyncio
    async def test_transcribe_error_status(self, config):
        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"upload_url": "https://test"}

        submit_resp = MagicMock()
        submit_resp.raise_for_status = MagicMock()
        submit_resp.json.return_value = {"id": "abc", "status": "queued"}

        error_resp = MagicMock()
        error_resp.raise_for_status = MagicMock()
        error_resp.json.return_value = {"status": "error", "error": "bad audio"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[upload_resp, submit_resp])
        mock_client.get = AsyncMock(return_value=error_resp)

        p = AssemblyAIProvider(config)
        p._initialized = True
        p._http = mock_client

        with pytest.raises(AssemblyAIStreamingError, match="bad audio"):
            await p.transcribe(b"\x00" * 100)

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = AsyncMock()

        with patch("champi_stt.providers.assemblyai.provider.HTTPX_AVAILABLE", True):
            with patch("champi_stt.providers.assemblyai.provider.httpx", mock_httpx):
                async with AssemblyAIProvider(config) as p:
                    assert p.is_initialized
        assert not p.is_initialized

    @pytest.mark.asyncio
    async def test_transcribe_numpy(self, config):
        audio = np.zeros(16000, dtype=np.float32)

        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"upload_url": "https://test"}

        submit_resp = MagicMock()
        submit_resp.raise_for_status = MagicMock()
        submit_resp.json.return_value = {"id": "abc", "status": "queued"}

        poll_resp = MagicMock()
        poll_resp.raise_for_status = MagicMock()
        poll_resp.json.return_value = _SAMPLE_COMPLETED

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[upload_resp, submit_resp])
        mock_client.get = AsyncMock(return_value=poll_resp)

        p = AssemblyAIProvider(config)
        p._initialized = True
        p._http = mock_client

        import soundfile as sf_mod
        with patch("champi_stt.providers.assemblyai.provider.SOUNDFILE_AVAILABLE", True):
            with patch("champi_stt.providers.assemblyai.provider.sf", sf_mod):
                result = await p.transcribe(audio)
        assert isinstance(result, TranscriptionResponse)


class TestParseResponse:
    def test_basic_parse(self, provider):
        result = provider._parse_response(_SAMPLE_COMPLETED)
        assert result.text == "hello assemblyai"
        assert result.language == "en"
        assert result.duration == pytest.approx(2.5)
        assert len(result.segments) == 2

    def test_empty_words(self, provider):
        result = provider._parse_response({"status": "completed", "text": "hi", "words": []})
        assert result.text == "hi"
        assert result.segments == []

    def test_none_text(self, provider):
        result = provider._parse_response({"status": "completed", "text": None, "words": None})
        assert result.text == ""


class TestToInt16Bytes:
    def test_float32(self):
        audio = np.array([0.5, -0.5], dtype=np.float32)
        result = AssemblyAIProvider._to_int16_bytes(audio)
        assert isinstance(result, bytes)
        assert len(result) == 4

    def test_int16_passthrough(self):
        audio = np.array([100, -100], dtype=np.int16)
        result = AssemblyAIProvider._to_int16_bytes(audio)
        assert len(result) == 4
