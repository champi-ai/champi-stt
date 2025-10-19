"""Tests for WhisperLive provider."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from champi_stt.providers.whisperlive.config import WhisperLiveConfig
from champi_stt.providers.whisperlive.enums import ModelSize, ComputeType
from champi_stt.providers.whisperlive.provider import WhisperLiveProvider
from champi_stt.providers.whisperlive.models import TranscriptionOptions
from champi_stt.core.response import TranscriptionResponse


class TestWhisperLiveConfig:
    """Tests for WhisperLive configuration."""

    def test_config_creation(self):
        """Test creating WhisperLive config."""
        config = WhisperLiveConfig(
            model=ModelSize.BASE,
            compute_type=ComputeType.INT8,
            language="en",
        )

        assert config.model == ModelSize.BASE
        assert config.compute_type == ComputeType.INT8
        assert config.language == "en"

    def test_config_default_values(self):
        """Test default configuration values."""
        config = WhisperLiveConfig()

        assert config.model == ModelSize.BASE
        assert config.compute_type == ComputeType.INT8
        assert config.device == "auto"
        assert config.language is None

    def test_config_custom_device(self):
        """Test config with custom device."""
        config = WhisperLiveConfig(device="cuda")

        assert config.device == "cuda"

    def test_config_model_sizes(self):
        """Test different model sizes."""
        for size in [ModelSize.TINY, ModelSize.BASE, ModelSize.SMALL, ModelSize.MEDIUM]:
            config = WhisperLiveConfig(model=size)
            assert config.model == size


class TestTranscriptionOptions:
    """Tests for transcription options."""

    def test_options_creation(self):
        """Test creating transcription options."""
        options = TranscriptionOptions(
            language="en",
            task="transcribe",
            beam_size=5,
            best_of=3,
        )

        assert options.language == "en"
        assert options.task == "transcribe"
        assert options.beam_size == 5
        assert options.best_of == 3

    def test_options_defaults(self):
        """Test default transcription options."""
        options = TranscriptionOptions()

        assert options.language is None
        assert options.task == "transcribe"
        assert options.beam_size == 5
        assert options.temperature == 0.0

    def test_options_vad_settings(self):
        """Test VAD-related options."""
        options = TranscriptionOptions(
            vad_filter=True,
            vad_threshold=0.6,
        )

        assert options.vad_filter is True
        assert options.vad_threshold == 0.6


class TestWhisperLiveProvider:
    """Tests for WhisperLive provider."""

    def test_provider_initialization(self):
        """Test provider initialization."""
        config = WhisperLiveConfig(model=ModelSize.BASE)
        provider = WhisperLiveProvider(config)

        assert provider.config == config
        assert provider.name == "WhisperLive"
        assert not provider.is_initialized

    @pytest.mark.asyncio
    async def test_provider_initialize(self, mocker):
        """Test provider initialization."""
        config = WhisperLiveConfig(model=ModelSize.TINY)
        provider = WhisperLiveProvider(config)

        # Mock the model loading
        mock_model = MagicMock()
        mocker.patch(
            "champi_stt.providers.whisperlive.provider.WhisperModel",
            return_value=mock_model,
        )

        await provider.initialize()

        assert provider.is_initialized
        assert provider._model is not None

    @pytest.mark.asyncio
    async def test_provider_shutdown(self, mocker):
        """Test provider shutdown."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        # Mock initialization
        provider._model = MagicMock()
        provider._initialized = True

        await provider.shutdown()

        assert not provider.is_initialized
        assert provider._model is None

    @pytest.mark.asyncio
    async def test_provider_transcribe_file(
        self, mocker, sample_audio_file: Path, mock_transcription_result: dict
    ):
        """Test transcribing an audio file."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        # Mock the model
        mock_model = MagicMock()
        mock_segments = [
            MagicMock(
                text=" hello world",
                start=0.0,
                end=1.5,
                avg_logprob=-0.3,
                no_speech_prob=0.1,
            )
        ]
        mock_info = MagicMock(language="en", language_probability=0.95)
        mock_model.transcribe.return_value = (mock_segments, mock_info)

        provider._model = mock_model
        provider._initialized = True

        result = await provider.transcribe(sample_audio_file)

        assert isinstance(result, TranscriptionResponse)
        assert result.text == "hello world"
        assert result.language == "en"
        assert len(result.segments) > 0

    @pytest.mark.asyncio
    async def test_provider_transcribe_with_options(
        self, mocker, sample_audio_file: Path
    ):
        """Test transcription with custom options."""
        config = WhisperLiveConfig(language="es")
        provider = WhisperLiveProvider(config)

        mock_model = MagicMock()
        mock_segments = [MagicMock(text=" hola", start=0.0, end=1.0, avg_logprob=-0.2, no_speech_prob=0.1)]
        mock_info = MagicMock(language="es", language_probability=0.98)
        mock_model.transcribe.return_value = (mock_segments, mock_info)

        provider._model = mock_model
        provider._initialized = True

        result = await provider.transcribe(
            sample_audio_file, language="es", beam_size=10
        )

        assert result.language == "es"
        mock_model.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_provider_context_manager(self, mocker):
        """Test provider as context manager."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        mock_model = MagicMock()
        mocker.patch(
            "champi_stt.providers.whisperlive.provider.WhisperModel",
            return_value=mock_model,
        )

        async with provider:
            assert provider.is_initialized

        assert not provider.is_initialized

    def test_provider_model_path(self):
        """Test getting model path."""
        config = WhisperLiveConfig(model=ModelSize.BASE)
        provider = WhisperLiveProvider(config)

        model_path = provider._get_model_path()
        assert "base" in str(model_path).lower()


class TestWhisperLiveIntegration:
    """Integration tests for WhisperLive provider."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_transcription_workflow(self, sample_audio_file: Path):
        """Test complete transcription workflow (requires model download)."""
        config = WhisperLiveConfig(model=ModelSize.TINY)
        provider = WhisperLiveProvider(config)

        try:
            await provider.initialize()
            result = await provider.transcribe(sample_audio_file)

            assert isinstance(result, TranscriptionResponse)
            assert isinstance(result.text, str)
            assert result.language is not None

        finally:
            await provider.shutdown()
