"""Tests for the Kokoro STT provider."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from champi_stt.core.response import TranscriptionResponse
from champi_stt.providers.kokoro.config import KokoroConfig
from champi_stt.providers.kokoro.exceptions import (
    KokoroNotInstalledError,
    KokoroTranscriptionError,
)
from champi_stt.providers.kokoro.provider import KokoroSTTProvider


@pytest.fixture
def config():
    return KokoroConfig(lang_code="a", device="cpu", model_id="hexgrad/Kokoro-82M")


@pytest.fixture
def provider(config):
    return KokoroSTTProvider(config)


# ---------------------------------------------------------------------------
# Config


class TestKokoroConfig:
    def test_defaults(self):
        cfg = KokoroConfig()
        assert cfg.model_id == "hexgrad/Kokoro-82M"
        assert cfg.lang_code == "a"
        assert cfg.device == "cpu"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("KOKORO_MODEL_ID", "hexgrad/Kokoro-Small")
        monkeypatch.setenv("KOKORO_LANG_CODE", "b")
        monkeypatch.setenv("KOKORO_DEVICE", "cuda")
        cfg = KokoroConfig.from_env()
        assert cfg.model_id == "hexgrad/Kokoro-Small"
        assert cfg.lang_code == "b"
        assert cfg.device == "cuda"

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("KOKORO_MODEL_ID", raising=False)
        monkeypatch.delenv("KOKORO_LANG_CODE", raising=False)
        monkeypatch.delenv("KOKORO_DEVICE", raising=False)
        cfg = KokoroConfig.from_env()
        assert cfg.model_id == "hexgrad/Kokoro-82M"
        assert cfg.lang_code == "a"
        assert cfg.device == "cpu"


# ---------------------------------------------------------------------------
# Provider initialisation


class TestKokoroSTTProviderInit:
    def test_name(self, provider):
        assert provider.name == "Kokoro"

    def test_not_initialized_at_construction(self, provider):
        assert not provider.is_initialized
        assert not provider.is_loaded

    @pytest.mark.asyncio
    async def test_initialize_raises_when_kokoro_missing(self, config):
        p = KokoroSTTProvider(config)
        with (
            patch("champi_stt.providers.kokoro.provider.KOKORO_AVAILABLE", False),
            pytest.raises(KokoroNotInstalledError, match="kokoro package is required"),
        ):
            await p.initialize()

    @pytest.mark.asyncio
    async def test_initialize_success(self, config):
        mock_pipeline = MagicMock()
        mock_kpipeline_cls = MagicMock(return_value=mock_pipeline)

        p = KokoroSTTProvider(config)
        with (
            patch("champi_stt.providers.kokoro.provider.KOKORO_AVAILABLE", True),
            patch("champi_stt.providers.kokoro.provider.KPipeline", mock_kpipeline_cls),
        ):
            await p.initialize()

        assert p.is_initialized
        mock_kpipeline_cls.assert_called_once_with(
            lang_code="a",
            device="cpu",
            repo_id="hexgrad/Kokoro-82M",
        )

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, config):
        mock_pipeline = MagicMock()
        mock_kpipeline_cls = MagicMock(return_value=mock_pipeline)

        p = KokoroSTTProvider(config)
        with (
            patch("champi_stt.providers.kokoro.provider.KOKORO_AVAILABLE", True),
            patch("champi_stt.providers.kokoro.provider.KPipeline", mock_kpipeline_cls),
        ):
            await p.initialize()
            await p.initialize()

        assert mock_kpipeline_cls.call_count == 1

    @pytest.mark.asyncio
    async def test_shutdown(self, config):
        mock_pipeline = MagicMock()
        mock_kpipeline_cls = MagicMock(return_value=mock_pipeline)

        p = KokoroSTTProvider(config)
        with (
            patch("champi_stt.providers.kokoro.provider.KOKORO_AVAILABLE", True),
            patch("champi_stt.providers.kokoro.provider.KPipeline", mock_kpipeline_cls),
        ):
            await p.initialize()
        assert p.is_initialized

        await p.shutdown()
        assert not p.is_initialized
        assert p._pipeline is None


# ---------------------------------------------------------------------------
# Transcription


class TestKokoroSTTProviderTranscribe:
    def _make_initialized_provider(self, config):
        p = KokoroSTTProvider(config)
        mock_pipeline = MagicMock()
        mock_pipeline.recognize.return_value = "hello kokoro"
        p._pipeline = mock_pipeline
        p._initialized = True
        return p

    @pytest.mark.asyncio
    async def test_transcribe_not_initialized_raises(self, config):
        p = KokoroSTTProvider(config)
        with pytest.raises(RuntimeError, match="not initialized"):
            await p.transcribe(b"\x00" * 100)

    @pytest.mark.asyncio
    async def test_transcribe_bytes(self, config):
        p = self._make_initialized_provider(config)
        result = await p.transcribe(b"\x00" * 100)
        assert isinstance(result, TranscriptionResponse)
        assert result.text == "hello kokoro"
        assert result.language == "a"

    @pytest.mark.asyncio
    async def test_transcribe_bytes_language_override(self, config):
        p = self._make_initialized_provider(config)
        result = await p.transcribe(b"\x00" * 100, language="en")
        assert result.language == "en"
        p._pipeline.recognize.assert_called_with(b"\x00" * 100, lang="en")

    @pytest.mark.asyncio
    async def test_transcribe_file_path_str(self, tmp_path, config):
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")

        p = self._make_initialized_provider(config)
        result = await p.transcribe(str(audio_file))
        assert isinstance(result, TranscriptionResponse)
        assert result.text == "hello kokoro"

    @pytest.mark.asyncio
    async def test_transcribe_file_path_object(self, tmp_path, config):
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")

        p = self._make_initialized_provider(config)
        result = await p.transcribe(audio_file)
        assert isinstance(result, TranscriptionResponse)

    @pytest.mark.asyncio
    async def test_transcribe_numpy_float32(self, config):
        import soundfile as sf_mod

        audio = np.zeros(16000, dtype=np.float32)
        p = self._make_initialized_provider(config)
        with (
            patch("champi_stt.providers.kokoro.provider.SOUNDFILE_AVAILABLE", True),
            patch("champi_stt.providers.kokoro.provider.sf", sf_mod),
        ):
            result = await p.transcribe(audio)
        assert isinstance(result, TranscriptionResponse)

    @pytest.mark.asyncio
    async def test_transcribe_numpy_int16(self, config):
        import soundfile as sf_mod

        audio = np.zeros(16000, dtype=np.int16)
        p = self._make_initialized_provider(config)
        with (
            patch("champi_stt.providers.kokoro.provider.SOUNDFILE_AVAILABLE", True),
            patch("champi_stt.providers.kokoro.provider.sf", sf_mod),
        ):
            result = await p.transcribe(audio)
        assert isinstance(result, TranscriptionResponse)

    @pytest.mark.asyncio
    async def test_transcribe_numpy_no_soundfile(self, config):
        audio = np.zeros(16000, dtype=np.float32)
        p = self._make_initialized_provider(config)
        with (
            patch("champi_stt.providers.kokoro.provider.SOUNDFILE_AVAILABLE", False),
            pytest.raises(ImportError, match="soundfile is required"),
        ):
            await p.transcribe(audio)

    @pytest.mark.asyncio
    async def test_transcribe_unsupported_type(self, config):
        p = self._make_initialized_provider(config)
        with pytest.raises(TypeError, match="Unsupported audio type"):
            await p.transcribe(12345)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_transcribe_pipeline_error_raises_kokoro_error(self, config):
        p = self._make_initialized_provider(config)
        p._pipeline.recognize.side_effect = RuntimeError("model crash")
        with pytest.raises(KokoroTranscriptionError, match="model crash"):
            await p.transcribe(b"\x00" * 100)

    @pytest.mark.asyncio
    async def test_transcribe_strips_whitespace(self, config):
        p = self._make_initialized_provider(config)
        p._pipeline.recognize.return_value = "  hello world  "
        result = await p.transcribe(b"\x00" * 100)
        assert result.text == "hello world"

    @pytest.mark.asyncio
    async def test_transcribe_processing_time_positive(self, config):
        p = self._make_initialized_provider(config)
        result = await p.transcribe(b"\x00" * 100)
        assert result.processing_time >= 0.0


# ---------------------------------------------------------------------------
# Context manager


class TestKokoroSTTProviderContextManager:
    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        mock_pipeline = MagicMock()
        mock_kpipeline_cls = MagicMock(return_value=mock_pipeline)

        with (
            patch("champi_stt.providers.kokoro.provider.KOKORO_AVAILABLE", True),
            patch("champi_stt.providers.kokoro.provider.KPipeline", mock_kpipeline_cls),
        ):
            async with KokoroSTTProvider(config) as p:
                assert p.is_initialized
        assert not p.is_initialized


# ---------------------------------------------------------------------------
# Model info


class TestKokoroSTTProviderModelInfo:
    @pytest.mark.asyncio
    async def test_get_model_info_not_initialized(self, provider):
        info = await provider.get_model_info()
        assert info["status"] == "not_initialized"
        assert info["provider"] == "kokoro"
        assert info["model_id"] == "hexgrad/Kokoro-82M"

    @pytest.mark.asyncio
    async def test_get_model_info_initialized(self, config):
        mock_pipeline = MagicMock()
        mock_kpipeline_cls = MagicMock(return_value=mock_pipeline)

        p = KokoroSTTProvider(config)
        with (
            patch("champi_stt.providers.kokoro.provider.KOKORO_AVAILABLE", True),
            patch("champi_stt.providers.kokoro.provider.KPipeline", mock_kpipeline_cls),
        ):
            await p.initialize()

        info = await p.get_model_info()
        assert info["status"] == "loaded"
        assert info["device"] == "cpu"
        assert info["lang_code"] == "a"


# ---------------------------------------------------------------------------
# Factory integration


class TestKokoroFactory:
    def test_list_providers_includes_kokoro(self):
        from champi_stt.factory import list_providers

        assert "kokoro" in list_providers()

    def test_get_provider_kokoro_returns_provider(self):
        from champi_stt.factory import get_provider

        p = get_provider("kokoro")
        assert isinstance(p, KokoroSTTProvider)
        assert not p.is_initialized

    def test_get_provider_kokoro_with_kwargs(self):
        from champi_stt.factory import get_provider

        p = get_provider("kokoro", lang_code="b", device="cuda")
        assert isinstance(p, KokoroSTTProvider)
        assert p.config.lang_code == "b"
        assert p.config.device == "cuda"

    def test_get_provider_kokoro_with_config(self, config):
        from champi_stt.factory import get_provider

        p = get_provider("kokoro", config=config)
        assert isinstance(p, KokoroSTTProvider)
        assert p.config is config
