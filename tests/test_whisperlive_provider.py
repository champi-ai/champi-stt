"""Tests for WhisperLive provider."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from champi_stt.core.response import TranscriptionResponse
from champi_stt.providers.whisperlive.config import WhisperLiveConfig
from champi_stt.providers.whisperlive.enums import ComputeType, ModelSize
from champi_stt.providers.whisperlive.models import TranscriptionOptions
from champi_stt.providers.whisperlive.provider import WhisperLiveProvider


class TestWhisperLiveConfig:
    """Tests for WhisperLive configuration."""

    def test_config_creation(self):
        """Test creating WhisperLive config."""
        config = WhisperLiveConfig(
            model_size=ModelSize.BASE,
            compute_type=ComputeType.INT8,
            language="en",
        )

        assert config.model_size == ModelSize.BASE.value
        assert config.compute_type == ComputeType.INT8.value
        assert config.language == "en"

    def test_config_default_values(self):
        """Test default configuration values."""
        config = WhisperLiveConfig()

        assert config.model_size == ModelSize.BASE.value
        assert config.compute_type == ComputeType.INT8.value
        assert config.device == "auto"
        assert config.language is None

    def test_config_custom_device(self):
        """Test config with custom device."""
        config = WhisperLiveConfig(device="cuda")

        assert config.device == "cuda"

    def test_config_model_sizes(self):
        """Test different model sizes."""
        for size in [ModelSize.TINY, ModelSize.BASE, ModelSize.SMALL, ModelSize.MEDIUM]:
            config = WhisperLiveConfig(model_size=size)
            assert config.model_size == size.value

    def test_cache_dir_default(self):
        """Test that cache_dir default resolves to the expected tilde-prefixed path."""
        config = WhisperLiveConfig()
        assert config.cache_dir == "~/.cache/champi-stt/whisper/cache"

    def test_transcriptions_dir_default(self):
        """Test that transcriptions_dir default resolves to the expected tilde-prefixed path."""
        config = WhisperLiveConfig()
        assert config.transcriptions_dir == "~/.cache/champi-stt/transcriptions"

    def test_post_init_normalizes_model_size_enum(self):
        """Test that __post_init__ converts a ModelSize enum instance to its string value."""
        config = WhisperLiveConfig(model_size=ModelSize.TINY)
        assert config.model_size == "tiny"
        assert isinstance(config.model_size, str)

    def test_post_init_normalizes_compute_type_enum(self):
        """Test that __post_init__ converts a ComputeType enum instance to its string value."""
        config = WhisperLiveConfig(compute_type=ComputeType.FLOAT16)
        assert config.compute_type == "float16"
        assert isinstance(config.compute_type, str)

    def test_invalid_model_size_falls_back_to_base(self):
        """Test that an unrecognised model_size string is reset to 'base' by __post_init__."""
        config = WhisperLiveConfig(model_size="definitely-not-a-real-model")
        assert config.model_size == ModelSize.BASE.value

    def test_post_init_temperature_out_of_range_resets(self):
        """Test that temperature outside [0.0, 1.0] is reset to 0.0."""
        config = WhisperLiveConfig(temperature=2.5)
        assert config.temperature == 0.0

    def test_post_init_beam_size_below_one_resets(self):
        """Test that beam_size < 1 is reset to 5."""
        config = WhisperLiveConfig(beam_size=0)
        assert config.beam_size == 5

    def test_post_init_batch_size_below_one_resets(self):
        """Test that batch_size < 1 is reset to 8."""
        config = WhisperLiveConfig(batch_size=0)
        assert config.batch_size == 8

    def test_post_init_vad_aggressiveness_out_of_range_resets(self):
        """Test that vad_aggressiveness outside [0.0, 3.0] is reset to 2.0."""
        config = WhisperLiveConfig(vad_aggressiveness=5.0)
        assert config.vad_aggressiveness == 2.0

    def test_post_init_silence_threshold_too_low_resets(self):
        """Test that silence_threshold_ms below 100 is reset to 800."""
        config = WhisperLiveConfig(silence_threshold_ms=50)
        assert config.silence_threshold_ms == 800

    def test_post_init_min_recording_duration_too_low_resets(self):
        """Test that min_recording_duration below 0.1 is reset to 0.3."""
        config = WhisperLiveConfig(min_recording_duration=0.05)
        assert config.min_recording_duration == 0.3

    def test_post_init_english_only_model_forces_english_language(self):
        """Test that an English-only model overrides a non-English language setting."""
        config = WhisperLiveConfig(model_size=ModelSize.BASE_EN, language="fr")
        assert config.language == "en"

    def test_post_init_invalid_task_resets_to_transcribe(self):
        """Test that an invalid task string is reset to 'transcribe'."""
        config = WhisperLiveConfig(task="summarise")
        assert config.task == "transcribe"

    def test_from_env_reads_model_size(self, monkeypatch):
        """Test that from_env() reads WHISPERLIVE_MODEL from the environment."""
        monkeypatch.setenv("WHISPERLIVE_MODEL", "small")
        config = WhisperLiveConfig.from_env()
        assert config.model_size == "small"

    def test_from_env_reads_language(self, monkeypatch):
        """Test that from_env() reads WHISPERLIVE_LANGUAGE from the environment."""
        monkeypatch.setenv("WHISPERLIVE_LANGUAGE", "es")
        config = WhisperLiveConfig.from_env()
        assert config.language == "es"

    def test_from_env_reads_device(self, monkeypatch):
        """Test that from_env() reads WHISPERLIVE_DEVICE from the environment."""
        monkeypatch.setenv("WHISPERLIVE_DEVICE", "cpu")
        config = WhisperLiveConfig.from_env()
        assert config.device == "cpu"

    def test_from_env_reads_beam_size(self, monkeypatch):
        """Test that from_env() reads WHISPERLIVE_BEAM_SIZE and converts it to int."""
        monkeypatch.setenv("WHISPERLIVE_BEAM_SIZE", "3")
        config = WhisperLiveConfig.from_env()
        assert config.beam_size == 3

    def test_from_env_reads_save_transcriptions(self, monkeypatch):
        """Test that from_env() reads WHISPERLIVE_SAVE_TRANSCRIPTIONS as a boolean flag."""
        monkeypatch.setenv("WHISPERLIVE_SAVE_TRANSCRIPTIONS", "true")
        config = WhisperLiveConfig.from_env()
        assert config.save_transcriptions is True

    def test_from_env_reads_cache_dir(self, monkeypatch):
        """Test that from_env() reads WHISPERLIVE_CACHE_DIR."""
        monkeypatch.setenv("WHISPERLIVE_CACHE_DIR", "/tmp/test-cache")
        config = WhisperLiveConfig.from_env()
        assert config.cache_dir == "/tmp/test-cache"

    def test_from_env_uses_defaults_when_vars_absent(self, monkeypatch):
        """Test that from_env() uses defaults when relevant env vars are absent."""
        monkeypatch.delenv("WHISPERLIVE_MODEL", raising=False)
        monkeypatch.delenv("WHISPERLIVE_LANGUAGE", raising=False)
        config = WhisperLiveConfig.from_env()
        assert config.model_size == ModelSize.BASE.value
        assert config.language is None

    def test_from_dict(self):
        """Test creating a config from a plain dictionary."""
        data = {"model_size": "tiny", "language": "de", "beam_size": 3}
        config = WhisperLiveConfig.from_dict(data)
        assert config.model_size == "tiny"
        assert config.language == "de"
        assert config.beam_size == 3

    def test_from_dict_ignores_unknown_keys(self):
        """Test that from_dict silently drops keys not defined in the dataclass."""
        data = {"model_size": "tiny", "unknown_future_field": "ignored"}
        config = WhisperLiveConfig.from_dict(data)
        assert config.model_size == "tiny"
        assert not hasattr(config, "unknown_future_field")

    def test_to_dict(self):
        """Test converting a config instance to a plain dictionary."""
        config = WhisperLiveConfig(model_size=ModelSize.TINY, language="ja")
        result = config.to_dict()
        assert isinstance(result, dict)
        assert result["model_size"] == "tiny"
        assert result["language"] == "ja"

    def test_from_file_not_found_returns_default(self):
        """Test that from_file() returns a default config when the file is missing."""
        config = WhisperLiveConfig.from_file("/nonexistent/path/config.json")
        assert isinstance(config, WhisperLiveConfig)
        assert config.model_size == ModelSize.BASE.value

    def test_from_file_invalid_json_returns_default(self):
        """Test that from_file() returns a default config when the JSON is malformed."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            tmp.write("{ not valid json }")
            tmp_path = tmp.name

        try:
            config = WhisperLiveConfig.from_file(tmp_path)
            assert isinstance(config, WhisperLiveConfig)
            assert config.model_size == ModelSize.BASE.value
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_from_file_valid_json(self):
        """Test that from_file() correctly loads a valid JSON config file."""
        data = {"model_size": "small", "language": "pt", "beam_size": 4}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(data, tmp)
            tmp_path = tmp.name

        try:
            config = WhisperLiveConfig.from_file(tmp_path)
            assert config.model_size == "small"
            assert config.language == "pt"
            assert config.beam_size == 4
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_get_effective_language_english_only_model(self):
        """Test that get_effective_language returns 'en' for English-only models."""
        config = WhisperLiveConfig(model_size=ModelSize.BASE_EN)
        assert config.get_effective_language() == "en"

    def test_get_effective_language_multilingual_with_language(self):
        """Test that get_effective_language returns the configured language for multilingual models."""
        config = WhisperLiveConfig(model_size=ModelSize.BASE, language="fr")
        assert config.get_effective_language() == "fr"

    def test_get_effective_language_multilingual_no_language(self):
        """Test that get_effective_language returns None when no language is set on a multilingual model."""
        config = WhisperLiveConfig(model_size=ModelSize.BASE, language=None)
        assert config.get_effective_language() is None

    def test_validate_audio_format_supported(self):
        """Test that validate_audio_format returns the format unchanged when it is supported."""
        config = WhisperLiveConfig(audio_format="wav")
        assert config.validate_audio_format() == "wav"

    def test_validate_audio_format_unsupported_falls_back_to_wav(self):
        """Test that validate_audio_format falls back to 'wav' for unsupported formats."""
        config = WhisperLiveConfig(audio_format="aiff")
        assert config.validate_audio_format() == "wav"


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

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test to ensure clean state."""
        WhisperLiveProvider._instance = None
        yield
        WhisperLiveProvider._instance = None

    def test_provider_initialization(self):
        """Test provider initialization."""
        config = WhisperLiveConfig(model_size=ModelSize.BASE)
        provider = WhisperLiveProvider(config)

        assert provider.config == config
        assert provider.name == "WhisperLive"
        assert not provider.is_initialized

    @pytest.mark.asyncio
    async def test_provider_initialize(self, mocker):
        """Test provider initialization."""
        config = WhisperLiveConfig(model_size=ModelSize.TINY)
        provider = WhisperLiveProvider(config)

        # Mock directory validation and transcriber to avoid I/O
        mocker.patch.object(provider, "validate_directories")
        mock_transcriber = MagicMock()
        mock_transcriber.initialize = AsyncMock()
        mock_transcriber.is_loaded = True
        mocker.patch(
            "champi_stt.providers.whisperlive.provider.WhisperLiveTranscriber",
            return_value=mock_transcriber,
        )

        await provider.initialize()

        assert provider.is_initialized
        assert provider.transcriber is not None

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_true(self, mocker):
        """Test that initialize() sets _initialized to True."""
        config = WhisperLiveConfig(model_size=ModelSize.TINY)
        provider = WhisperLiveProvider(config)

        assert not provider._initialized

        mocker.patch.object(provider, "validate_directories")
        mock_transcriber = MagicMock()
        mock_transcriber.initialize = AsyncMock()
        mock_transcriber.is_loaded = True
        mocker.patch(
            "champi_stt.providers.whisperlive.provider.WhisperLiveTranscriber",
            return_value=mock_transcriber,
        )

        await provider.initialize()

        assert provider._initialized is True

    @pytest.mark.asyncio
    async def test_provider_shutdown(self, mocker):
        """Test provider shutdown."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        # Mock initialization state
        mock_transcriber = MagicMock()
        mock_transcriber.shutdown = AsyncMock()
        provider.transcriber = mock_transcriber
        provider._initialized = True

        await provider.shutdown()

        assert not provider.is_initialized
        assert provider.transcriber is None

    @pytest.mark.asyncio
    async def test_shutdown_sets_initialized_false(self):
        """Test that shutdown() sets _initialized to False."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        mock_transcriber = MagicMock()
        mock_transcriber.shutdown = AsyncMock()
        provider.transcriber = mock_transcriber
        provider._initialized = True

        await provider.shutdown()

        assert provider._initialized is False

    def test_is_loaded_false_when_no_transcriber(self):
        """Test that is_loaded returns False when transcriber is None."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        assert provider.transcriber is None
        assert provider.is_loaded is False

    def test_is_loaded_true_when_transcriber_reports_loaded(self):
        """Test that is_loaded returns True when the transcriber says it is loaded."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        mock_transcriber = MagicMock()
        mock_transcriber.is_loaded = True
        provider.transcriber = mock_transcriber

        assert provider.is_loaded is True

    def test_is_loaded_false_when_transcriber_not_loaded(self):
        """Test that is_loaded returns False when transcriber exists but is not loaded."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        mock_transcriber = MagicMock()
        mock_transcriber.is_loaded = False
        provider.transcriber = mock_transcriber

        assert provider.is_loaded is False

    @pytest.mark.asyncio
    async def test_get_model_info_when_not_initialized(self):
        """Test that get_model_info returns a dict with status key when not initialized."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        result = await provider.get_model_info()

        assert isinstance(result, dict)
        assert result.get("status") == "not_initialized"

    @pytest.mark.asyncio
    async def test_get_model_info_delegates_to_transcriber(self):
        """Test that get_model_info delegates to the transcriber and returns its result."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        expected = {"provider": "whisperlive", "model_size": "base", "status": "loaded"}
        mock_transcriber = MagicMock()
        mock_transcriber.get_model_info = AsyncMock(return_value=expected)
        provider.transcriber = mock_transcriber
        provider._initialized = True

        result = await provider.get_model_info()

        assert isinstance(result, dict)
        assert result["provider"] == "whisperlive"
        mock_transcriber.get_model_info.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_model_info_no_transcriber_when_initialized(self):
        """Test that get_model_info handles initialized state with no transcriber."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)
        provider._initialized = True
        provider.transcriber = None

        result = await provider.get_model_info()

        assert isinstance(result, dict)
        assert result.get("status") == "no_transcriber"

    @pytest.mark.asyncio
    async def test_provider_transcribe_file(
        self, mocker, sample_audio_file: Path, mock_transcription_result: dict
    ):
        """Test transcribing an audio file."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe_audio = AsyncMock(
            return_value={
                "text": "hello world",
                "language": "en",
                "language_probability": 0.95,
                "duration": 1.5,
                "segments": [
                    {
                        "text": "hello world",
                        "start": 0.0,
                        "end": 1.5,
                        "avg_logprob": -0.3,
                        "no_speech_prob": 0.1,
                    }
                ],
            }
        )
        mock_transcriber.is_loaded = True
        provider.transcriber = mock_transcriber
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

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe_audio = AsyncMock(
            return_value={
                "text": "hola",
                "language": "es",
                "language_probability": 0.98,
                "duration": 1.0,
                "segments": [],
            }
        )
        mock_transcriber.is_loaded = True
        provider.transcriber = mock_transcriber
        provider._initialized = True

        result = await provider.transcribe(
            sample_audio_file, language="es", beam_size=10
        )

        assert result.language == "es"
        mock_transcriber.transcribe_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_provider_context_manager(self, mocker):
        """Test provider as context manager."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config)
        mocker.patch.object(provider, "validate_directories")

        mock_transcriber = MagicMock()
        mock_transcriber.initialize = AsyncMock()
        mock_transcriber.shutdown = AsyncMock()
        mock_transcriber.is_loaded = True
        mocker.patch(
            "champi_stt.providers.whisperlive.provider.WhisperLiveTranscriber",
            return_value=mock_transcriber,
        )

        async with provider:
            assert provider.is_initialized

        assert not provider.is_initialized

    def test_provider_model_path(self):
        """Test getting model path."""
        config = WhisperLiveConfig(model_size=ModelSize.BASE)
        provider = WhisperLiveProvider(config)

        model_path = provider._get_model_path()
        assert "base" in str(model_path).lower()


class TestWhisperLiveIntegration:
    """Integration tests for WhisperLive provider."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires model download - run manually with internet access")
    async def test_full_transcription_workflow(self, sample_audio_file: Path):
        """Test complete transcription workflow (requires model download)."""
        config = WhisperLiveConfig(model_size=ModelSize.TINY)
        provider = WhisperLiveProvider(config)

        try:
            await provider.initialize()
            result = await provider.transcribe(sample_audio_file)

            assert isinstance(result, TranscriptionResponse)
            assert isinstance(result.text, str)
            assert result.language is not None

        finally:
            await provider.shutdown()
