"""Tests for WhisperLive provider."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from champi_stt.core.response import TranscriptionResponse
from champi_stt.providers.whisperlive.config import WhisperLiveConfig, WhisperPresets
from champi_stt.providers.whisperlive.enums import ComputeType, ModelSize
from champi_stt.providers.whisperlive.exceptions import (
    WhisperInitializationError,
    WhisperTranscriptionError,
)
from champi_stt.providers.whisperlive.models import (
    ModelCacheManager,
    TranscriptionOptions,
)
from champi_stt.providers.whisperlive.provider import WhisperLiveProvider
from champi_stt.providers.whisperlive.transcriber import WhisperLiveTranscriber


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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
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


class TestWhisperLiveConfigValidation:
    """Tests for WhisperLiveConfig field validation in __post_init__."""

    def test_cache_dir_default_is_champi_stt_path(self):
        """Default cache_dir should use the corrected champi-stt path."""
        config = WhisperLiveConfig()
        assert config.cache_dir == "~/.cache/champi-stt/whisper/cache"

    def test_temperature_too_high_resets_to_zero(self):
        """Temperature above 1.0 is coerced to 0.0."""
        config = WhisperLiveConfig(temperature=1.5)
        assert config.temperature == 0.0

    def test_temperature_negative_resets_to_zero(self):
        """Negative temperature is coerced to 0.0."""
        config = WhisperLiveConfig(temperature=-0.1)
        assert config.temperature == 0.0

    def test_temperature_boundary_valid(self):
        """Temperature at exactly 1.0 is accepted."""
        config = WhisperLiveConfig(temperature=1.0)
        assert config.temperature == 1.0

    def test_beam_size_too_small_resets_to_default(self):
        """beam_size < 1 is coerced to the default of 5."""
        config = WhisperLiveConfig(beam_size=0)
        assert config.beam_size == 5

    def test_batch_size_too_small_resets_to_default(self):
        """batch_size < 1 is coerced to the default of 8."""
        config = WhisperLiveConfig(batch_size=0)
        assert config.batch_size == 8

    def test_vad_aggressiveness_too_high_resets(self):
        """vad_aggressiveness above 3.0 is coerced to 2.0."""
        config = WhisperLiveConfig(vad_aggressiveness=5.0)
        assert config.vad_aggressiveness == 2.0

    def test_vad_aggressiveness_negative_resets(self):
        """Negative vad_aggressiveness is coerced to 2.0."""
        config = WhisperLiveConfig(vad_aggressiveness=-1.0)
        assert config.vad_aggressiveness == 2.0

    def test_silence_threshold_too_low_resets(self):
        """silence_threshold_ms below 100 is coerced to 800."""
        config = WhisperLiveConfig(silence_threshold_ms=50)
        assert config.silence_threshold_ms == 800

    def test_min_recording_duration_too_low_resets(self):
        """min_recording_duration below 0.1 is coerced to 0.3."""
        config = WhisperLiveConfig(min_recording_duration=0.05)
        assert config.min_recording_duration == 0.3

    def test_english_only_model_forces_english_language(self):
        """An .en model overrides a non-English language setting."""
        config = WhisperLiveConfig(model_size="base.en", language="es")
        assert config.language == "en"

    def test_invalid_task_resets_to_transcribe(self):
        """An unrecognised task string is coerced to 'transcribe'."""
        config = WhisperLiveConfig(task="synthesize")
        assert config.task == "transcribe"

    def test_unknown_model_size_resets_to_base(self):
        """An unrecognised model size string is coerced to 'base'."""
        config = WhisperLiveConfig(model_size="nonexistent-v99")
        assert config.model_size == "base"

    def test_model_size_enum_normalised_to_value(self):
        """Passing a ModelSize enum instance stores only the string value."""
        config = WhisperLiveConfig(model_size=ModelSize.SMALL)
        assert config.model_size == "small"
        assert isinstance(config.model_size, str)


class TestWhisperLiveConfigSerialization:
    """Tests for WhisperLiveConfig serialisation / deserialisation."""

    def test_to_dict_contains_model_size(self):
        """to_dict() includes the model_size key."""
        config = WhisperLiveConfig(model_size="small", language="fr")
        d = config.to_dict()
        assert d["model_size"] == "small"
        assert d["language"] == "fr"

    def test_to_dict_round_trip_via_from_dict(self):
        """A config survives a to_dict / from_dict round-trip."""
        original = WhisperLiveConfig(model_size="tiny", language="de", beam_size=3)
        restored = WhisperLiveConfig.from_dict(original.to_dict())
        assert restored.model_size == original.model_size
        assert restored.language == original.language
        assert restored.beam_size == original.beam_size

    def test_from_dict_valid_keys(self):
        """from_dict() creates a config from a plain dictionary."""
        config = WhisperLiveConfig.from_dict({"model_size": "tiny", "language": "de"})
        assert config.model_size == "tiny"
        assert config.language == "de"

    def test_from_dict_ignores_unknown_keys(self):
        """from_dict() silently drops keys that are not config fields."""
        config = WhisperLiveConfig.from_dict(
            {"model_size": "tiny", "unknown_field": "value"}
        )
        assert config.model_size == "tiny"
        assert not hasattr(config, "unknown_field")

    def test_from_file_not_found_returns_default(self, tmp_path):
        """from_file() returns a default config when the file does not exist."""
        config = WhisperLiveConfig.from_file(str(tmp_path / "nonexistent.json"))
        assert config.model_size == "base"

    def test_from_file_invalid_json_returns_default(self, tmp_path):
        """from_file() returns a default config when the file contains bad JSON."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {{{")
        config = WhisperLiveConfig.from_file(str(bad_file))
        assert config.model_size == "base"

    def test_from_file_valid_json(self, tmp_path):
        """from_file() loads a well-formed JSON config file."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"model_size": "medium", "language": "en"}))
        config = WhisperLiveConfig.from_file(str(cfg_file))
        assert config.model_size == "medium"
        assert config.language == "en"


class TestWhisperLiveConfigEnvironment:
    """Tests for WhisperLiveConfig.from_env() reading environment variables."""

    def test_from_env_model_override(self, monkeypatch):
        """WHISPERLIVE_MODEL env var sets model_size."""
        monkeypatch.setenv("WHISPERLIVE_MODEL", "tiny")
        config = WhisperLiveConfig.from_env()
        assert config.model_size == "tiny"

    def test_from_env_language_override(self, monkeypatch):
        """WHISPERLIVE_LANGUAGE env var sets language."""
        monkeypatch.setenv("WHISPERLIVE_LANGUAGE", "fr")
        config = WhisperLiveConfig.from_env()
        assert config.language == "fr"

    def test_from_env_beam_size_override(self, monkeypatch):
        """WHISPERLIVE_BEAM_SIZE env var sets beam_size."""
        monkeypatch.setenv("WHISPERLIVE_BEAM_SIZE", "3")
        config = WhisperLiveConfig.from_env()
        assert config.beam_size == 3

    def test_from_env_beam_size_invalid_keeps_default(self, monkeypatch):
        """An invalid WHISPERLIVE_BEAM_SIZE keeps the default value."""
        monkeypatch.setenv("WHISPERLIVE_BEAM_SIZE", "not_a_number")
        config = WhisperLiveConfig.from_env()
        assert config.beam_size == 5

    def test_from_env_cache_dir_override(self, monkeypatch, tmp_path):
        """WHISPERLIVE_CACHE_DIR env var sets cache_dir."""
        custom_dir = str(tmp_path / "custom_cache")
        monkeypatch.setenv("WHISPERLIVE_CACHE_DIR", custom_dir)
        config = WhisperLiveConfig.from_env()
        assert config.cache_dir == custom_dir

    def test_from_env_word_timestamps_true(self, monkeypatch):
        """WHISPERLIVE_WORD_TIMESTAMPS=true enables word timestamps."""
        monkeypatch.setenv("WHISPERLIVE_WORD_TIMESTAMPS", "true")
        config = WhisperLiveConfig.from_env()
        assert config.word_timestamps is True

    def test_from_env_disable_vad(self, monkeypatch):
        """WHISPERLIVE_DISABLE_VAD=true disables VAD filter."""
        monkeypatch.setenv("WHISPERLIVE_DISABLE_VAD", "true")
        config = WhisperLiveConfig.from_env()
        assert config.vad_filter is False


class TestWhisperLiveConfigAudioAndPaths:
    """Tests for audio format validation and path-related helpers."""

    def test_validate_audio_format_wav(self):
        """'wav' is a valid audio format and is returned unchanged."""
        config = WhisperLiveConfig(audio_format="wav")
        assert config.validate_audio_format() == "wav"

    def test_validate_audio_format_mp3(self):
        """'mp3' is a valid audio format and is returned unchanged."""
        config = WhisperLiveConfig(audio_format="mp3")
        assert config.validate_audio_format() == "mp3"

    def test_validate_audio_format_unsupported_falls_back_to_wav(self):
        """An unsupported audio format causes a fallback to 'wav'."""
        config = WhisperLiveConfig(audio_format="xyz_unsupported")
        assert config.validate_audio_format() == "wav"

    def test_get_effective_language_english_only_model(self):
        """English-only models always report 'en' as effective language."""
        config = WhisperLiveConfig(model_size="base.en")
        assert config.get_effective_language() == "en"

    def test_get_effective_language_multilingual_none(self):
        """A multilingual model with no language configured returns None."""
        config = WhisperLiveConfig(model_size="base", language=None)
        assert config.get_effective_language() is None

    def test_get_effective_language_multilingual_set(self):
        """A multilingual model returns the configured language."""
        config = WhisperLiveConfig(model_size="base", language="fr")
        assert config.get_effective_language() == "fr"

    def test_is_english_only_true(self):
        """Model names ending in '.en' are recognised as English-only."""
        config = WhisperLiveConfig(model_size="tiny.en")
        assert config.is_english_only_model() is True

    def test_is_english_only_false(self):
        """Multilingual model names are not considered English-only."""
        config = WhisperLiveConfig(model_size="base")
        assert config.is_english_only_model() is False

    def test_get_device_cpu_explicit(self):
        """When device is explicitly 'cpu', get_device() returns 'cpu'."""
        config = WhisperLiveConfig(device="cpu")
        assert config.get_device() == "cpu"

    def test_get_device_auto_without_torch_returns_cpu(self, mocker):
        """get_device() falls back to 'cpu' when torch is unavailable."""
        config = WhisperLiveConfig(device="auto")
        mocker.patch.dict("sys.modules", {"torch": None})
        result = config.get_device()
        assert result == "cpu"

    def test_validate_directories_creates_cache_dir(self, tmp_path):
        """validate_directories() creates the cache directory on disk."""
        cache_dir = tmp_path / "whisper" / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        config.validate_directories()
        assert cache_dir.exists()

    def test_validate_directories_updates_cache_dir_attribute(self, tmp_path):
        """validate_directories() updates cache_dir to the resolved path."""
        cache_dir = tmp_path / "whisper" / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        config.validate_directories()
        assert config.cache_dir == str(cache_dir)

    def test_supported_audio_formats_includes_wav(self):
        """supported_audio_formats property includes 'wav'."""
        config = WhisperLiveConfig()
        assert "wav" in config.supported_audio_formats

    def test_model_sizes_property(self):
        """model_sizes property returns a non-empty list."""
        config = WhisperLiveConfig()
        assert isinstance(config.model_sizes, list)
        assert len(config.model_sizes) > 0


class TestWhisperPresets:
    """Tests for WhisperPresets factory methods."""

    def test_performance_preset_returns_config(self):
        """performance() returns a WhisperLiveConfig with large-v3-turbo."""
        config = WhisperPresets.performance()
        assert isinstance(config, WhisperLiveConfig)
        assert config.model_size == "large-v3-turbo"
        assert config.beam_size == 1

    def test_quality_preset_enables_word_timestamps(self):
        """quality() enables word_timestamps for detailed output."""
        config = WhisperPresets.quality()
        assert isinstance(config, WhisperLiveConfig)
        assert config.model_size == "large-v3"
        assert config.word_timestamps is True

    def test_cpu_only_preset_targets_cpu(self):
        """cpu_only() targets CPU with int8 compute type."""
        config = WhisperPresets.cpu_only()
        assert isinstance(config, WhisperLiveConfig)
        assert config.device == "cpu"
        assert config.compute_type == "int8"

    def test_minimal_preset_disables_vad(self):
        """minimal() disables VAD to conserve resources."""
        config = WhisperPresets.minimal()
        assert isinstance(config, WhisperLiveConfig)
        assert config.model_size == "base"
        assert config.vad_filter is False


class TestWhisperLiveProviderPaths:
    """Tests for provider path resolution and directory creation."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        WhisperLiveProvider._instance = None
        yield
        WhisperLiveProvider._instance = None

    def test_get_default_cache_dir_resolves_to_champi_stt(self):
        """Default cache dir points to ~/.cache/champi-stt/whisper/cache."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config=config)
        expected = str(Path.home() / ".cache" / "champi-stt" / "whisper" / "cache")
        assert provider.get_default_cache_dir() == expected

    def test_get_default_transcriptions_dir(self):
        """Default transcriptions dir is inside ~/.cache/champi-stt."""
        config = WhisperLiveConfig()
        provider = WhisperLiveProvider(config=config)
        result = provider.get_default_transcriptions_dir()
        assert "champi-stt" in result
        assert "transcriptions" in result

    def test_validate_directories_creates_cache_dir(self, tmp_path):
        """validate_directories() creates the configured cache directory."""
        cache_dir = tmp_path / "champi-stt" / "whisper" / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)
        provider.validate_directories()
        assert cache_dir.exists()

    def test_validate_directories_with_save_transcriptions(self, tmp_path):
        """validate_directories() also creates the transcriptions directory when saving is enabled."""
        cache_dir = tmp_path / "cache"
        trans_dir = tmp_path / "transcriptions"
        config = WhisperLiveConfig(
            cache_dir=str(cache_dir),
            save_transcriptions=True,
            transcriptions_dir=str(trans_dir),
        )
        provider = WhisperLiveProvider(config=config)
        provider.validate_directories()
        assert cache_dir.exists()
        assert trans_dir.exists()


class TestWhisperLiveProviderLifecycle:
    """Tests for provider startup, shutdown, and lifecycle state management."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        WhisperLiveProvider._instance = None
        yield
        WhisperLiveProvider._instance = None

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self, mocker, tmp_path):
        """After initialize(), is_initialized returns True."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)

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

    @pytest.mark.asyncio
    async def test_initialize_is_idempotent(self, mocker, tmp_path):
        """Calling initialize() twice only loads the model once."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)

        mocker.patch.object(provider, "validate_directories")
        mock_transcriber = MagicMock()
        mock_transcriber.initialize = AsyncMock()
        mock_transcriber.is_loaded = True
        mocker.patch(
            "champi_stt.providers.whisperlive.provider.WhisperLiveTranscriber",
            return_value=mock_transcriber,
        )

        await provider.initialize()
        await provider.initialize()

        mock_transcriber.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_raises_whisperinitializationerror_on_failure(
        self, mocker, tmp_path
    ):
        """A transcriber failure during initialize() is wrapped in WhisperInitializationError."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)

        mocker.patch.object(provider, "validate_directories")
        mock_transcriber = MagicMock()
        mock_transcriber.initialize = AsyncMock(
            side_effect=RuntimeError("model download failed")
        )
        mocker.patch(
            "champi_stt.providers.whisperlive.provider.WhisperLiveTranscriber",
            return_value=mock_transcriber,
        )

        with pytest.raises(WhisperInitializationError):
            await provider.initialize()

    @pytest.mark.asyncio
    async def test_shutdown_clears_transcriber_and_flag(self, tmp_path):
        """shutdown() sets transcriber to None and clears the initialized flag."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)

        mock_transcriber = MagicMock()
        mock_transcriber.shutdown = AsyncMock()
        provider.transcriber = mock_transcriber
        provider._initialized = True

        await provider.shutdown()

        assert provider.transcriber is None
        assert not provider.is_initialized
        mock_transcriber.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_on_uninitialised_provider_is_safe(self, tmp_path):
        """shutdown() on a provider that was never initialised does not raise."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)

        await provider.shutdown()

        assert not provider.is_initialized

    def test_is_loaded_false_without_transcriber(self, tmp_path):
        """is_loaded is False when transcriber has not been created."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)
        assert provider.is_loaded is False

    def test_is_loaded_delegates_to_transcriber(self, tmp_path):
        """is_loaded reflects the transcriber's is_loaded state."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)

        mock_transcriber = MagicMock()
        mock_transcriber.is_loaded = True
        provider.transcriber = mock_transcriber

        assert provider.is_loaded is True

    @pytest.mark.asyncio
    async def test_get_model_info_not_initialized(self, tmp_path):
        """get_model_info() returns a 'not_initialized' status before startup."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)

        info = await provider.get_model_info()
        assert info["status"] == "not_initialized"

    @pytest.mark.asyncio
    async def test_transcribe_raises_runtimeerror_without_transcriber(
        self, tmp_path, sample_audio_file: Path
    ):
        """transcribe() raises RuntimeError when the provider has not been initialised."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)

        with pytest.raises(RuntimeError):
            await provider.transcribe(sample_audio_file)

    @pytest.mark.asyncio
    async def test_format_response_with_empty_segments(self, tmp_path):
        """_format_response() handles a result with no segments."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        provider = WhisperLiveProvider(config=config)

        result = provider._format_response(
            {"text": "hello", "language": "en", "segments": []}, "json"
        )

        assert isinstance(result, TranscriptionResponse)
        assert result.text == "hello"
        assert result.segments == []

    @pytest.mark.asyncio
    async def test_get_singleton_returns_same_instance(self, tmp_path):
        """get_instance() always returns the same provider object."""
        cache_dir = tmp_path / "cache"
        config = WhisperLiveConfig(cache_dir=str(cache_dir))
        p1 = await WhisperLiveProvider.get_instance(config=config)
        p2 = await WhisperLiveProvider.get_instance(config=config)
        assert p1 is p2


class TestModelCacheManager:
    """Tests for ModelCacheManager cache operations."""

    def test_creation_creates_cache_directory(self, tmp_path):
        """Instantiating ModelCacheManager creates the cache directory."""
        cache_path = tmp_path / "cache"
        ModelCacheManager(cache_path)
        assert cache_path.exists()

    def test_cache_key_is_deterministic(self, tmp_path):
        """The same config always produces the same cache key."""
        mgr = ModelCacheManager(tmp_path)
        config = WhisperLiveConfig(model_size="tiny", device="cpu", compute_type="int8")
        key1 = mgr._get_cache_key(config)
        key2 = mgr._get_cache_key(config)
        assert key1 == key2

    def test_cache_key_differs_for_different_models(self, tmp_path):
        """Different model configs produce different cache keys."""
        mgr = ModelCacheManager(tmp_path)
        config_tiny = WhisperLiveConfig(model_size="tiny", device="cpu")
        config_base = WhisperLiveConfig(model_size="base", device="cpu")
        assert mgr._get_cache_key(config_tiny) != mgr._get_cache_key(config_base)

    def test_is_model_cached_false_initially(self, tmp_path):
        """A freshly created cache has no entries."""
        mgr = ModelCacheManager(tmp_path)
        config = WhisperLiveConfig()
        key = mgr._get_cache_key(config)
        assert mgr.is_model_cached(key) is False

    @pytest.mark.asyncio
    async def test_save_metadata_marks_model_as_cached(self, tmp_path):
        """After save_cache_metadata(), is_model_cached() returns True."""
        mgr = ModelCacheManager(tmp_path)
        config = WhisperLiveConfig(model_size="tiny")
        key = mgr._get_cache_key(config)
        await mgr.save_cache_metadata(config, key)
        assert mgr.is_model_cached(key) is True

    @pytest.mark.asyncio
    async def test_clear_cache_removes_metadata(self, tmp_path):
        """clear_cache() removes persisted metadata entries."""
        mgr = ModelCacheManager(tmp_path)
        config = WhisperLiveConfig(model_size="tiny")
        key = mgr._get_cache_key(config)
        await mgr.save_cache_metadata(config, key)
        assert mgr.is_model_cached(key) is True

        await mgr.clear_cache()

        assert mgr.is_model_cached(key) is False

    def test_get_cache_info_empty(self, tmp_path):
        """get_cache_info() reports zero entries for an empty cache."""
        mgr = ModelCacheManager(tmp_path)
        info = mgr.get_cache_info()
        assert info["files"] == 0
        assert info["memory_cached"] == 0

    @pytest.mark.asyncio
    async def test_store_and_retrieve_model_from_memory_cache(self, tmp_path):
        """A model stored in memory cache can be retrieved by key."""
        mgr = ModelCacheManager(tmp_path)
        key = "test_key_abc123"
        fake_model = MagicMock()
        await mgr.store_model_in_cache(key, fake_model)
        retrieved = await mgr.get_cached_model(key)
        assert retrieved is fake_model

    @pytest.mark.asyncio
    async def test_get_uncached_model_returns_none(self, tmp_path):
        """Requesting a non-existent key from the memory cache returns None."""
        mgr = ModelCacheManager(tmp_path)
        result = await mgr.get_cached_model("nonexistent_key_xyz")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cache_info_after_save(self, tmp_path):
        """get_cache_info() reflects a saved metadata file."""
        mgr = ModelCacheManager(tmp_path)
        config = WhisperLiveConfig(model_size="tiny")
        key = mgr._get_cache_key(config)
        await mgr.save_cache_metadata(config, key)
        info = mgr.get_cache_info()
        assert info["files"] == 1


class TestDeviceManager:
    """Tests for DeviceManager auto-detection logic."""

    def test_auto_detect_defaults_to_cpu(self):
        """With no CUDA env var set, auto-detection resolves to CPU."""
        from champi_stt.providers.whisperlive.models import DeviceManager

        config = WhisperLiveConfig(device="auto", compute_type="auto")
        device, compute_type = DeviceManager.auto_detect_device_settings(config)
        assert device == "cpu"
        assert compute_type == "int8"

    def test_explicit_cpu_device_is_preserved(self):
        """An explicitly configured 'cpu' device is returned unchanged."""
        from champi_stt.providers.whisperlive.models import DeviceManager

        config = WhisperLiveConfig(device="cpu", compute_type="int8")
        device, _compute_type = DeviceManager.auto_detect_device_settings(config)
        assert device == "cpu"

    def test_auto_compute_type_for_cpu_is_int8(self):
        """When device resolves to CPU, compute_type defaults to 'int8'."""
        from champi_stt.providers.whisperlive.models import DeviceManager

        config = WhisperLiveConfig(device="auto", compute_type="auto")
        device, compute_type = DeviceManager.auto_detect_device_settings(config)
        assert device == "cpu"
        assert compute_type == "int8"


class TestWhisperLiveIntegration:
    """Integration tests for WhisperLive provider."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skip(
        reason="Requires model download - run manually with internet access"
    )
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


# ---------------------------------------------------------------------------
# Helpers for transcriber unit tests
# ---------------------------------------------------------------------------


def _make_info(
    language="en",
    language_probability=0.99,
    duration=1.0,
    duration_after_vad=1.0,
):
    """Return a MagicMock shaped like faster-whisper TranscriptionInfo."""
    info = MagicMock()
    info.language = language
    info.language_probability = language_probability
    info.duration = duration
    info.duration_after_vad = duration_after_vad
    return info


def _make_segment(
    seg_id=0,
    start=0.0,
    end=1.0,
    text="hello",
    avg_logprob=-0.3,
    no_speech_prob=0.1,
    compression_ratio=1.0,
    temperature=0.0,
    tokens=None,
    words=None,
):
    """Return a MagicMock shaped like a faster-whisper Segment."""
    seg = MagicMock()
    seg.id = seg_id
    seg.start = start
    seg.end = end
    seg.text = text
    seg.avg_logprob = avg_logprob
    seg.no_speech_prob = no_speech_prob
    seg.compression_ratio = compression_ratio
    seg.temperature = temperature
    seg.tokens = tokens or []
    seg.words = words
    return seg


def _make_word(start=0.0, end=0.5, word="hello", probability=0.99):
    """Return a MagicMock shaped like a faster-whisper Word."""
    w = MagicMock()
    w.start = start
    w.end = end
    w.word = word
    w.probability = probability
    return w


# ---------------------------------------------------------------------------
# Fixtures for transcriber unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def transcriber(tmp_path):
    """WhisperLiveTranscriber with a temp cache dir, not yet initialized."""
    cfg = WhisperLiveConfig(cache_dir=str(tmp_path / "cache"))
    return WhisperLiveTranscriber(cfg)


@pytest.fixture
def initialized_transcriber(transcriber):
    """Transcriber in the initialized state backed by a mocked WhisperModel."""
    mock_model = MagicMock()
    transcriber.model_manager._model = mock_model
    transcriber._initialized = True
    return transcriber, mock_model


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTranscriberProcessSegments:
    """Unit tests for _process_segments — synchronous, no model needed."""

    def test_empty_iterator_returns_empty_list(self, transcriber):
        """Empty segment iterator produces an empty list."""
        result = transcriber._process_segments(iter([]))
        assert result == []

    def test_single_segment_without_words(self, transcriber):
        """A segment with words=None produces a dict without a 'words' key."""
        seg = _make_segment(seg_id=1, start=0.1, end=0.9, text=" hi", words=None)
        result = transcriber._process_segments([seg])
        assert len(result) == 1
        assert result[0]["text"] == " hi"
        assert "words" not in result[0]

    def test_single_segment_with_words(self, transcriber):
        """A segment with words populates the 'words' list in the output dict."""
        w1 = _make_word(start=0.0, end=0.3, word="hello", probability=0.98)
        w2 = _make_word(start=0.3, end=0.6, word="world", probability=0.97)
        seg = _make_segment(seg_id=0, text="hello world", words=[w1, w2])
        result = transcriber._process_segments([seg])
        assert "words" in result[0]
        assert len(result[0]["words"]) == 2
        assert result[0]["words"][0]["word"] == "hello"
        assert result[0]["words"][1]["probability"] == 0.97

    def test_multiple_segments_all_returned(self, transcriber):
        """Multiple segments produce one dict entry each."""
        segs = [_make_segment(seg_id=i, text=f"seg{i}") for i in range(3)]
        result = transcriber._process_segments(segs)
        assert len(result) == 3
        assert result[2]["id"] == 2


class TestTranscriberTranscribeAudio:
    """Tests for transcribe_audio covering key execution branches."""

    @pytest.mark.asyncio
    async def test_zero_length_audio_yields_empty_text(self, initialized_transcriber):
        """Model returns no segments for zero-length audio → text is empty."""
        transcriber, mock_model = initialized_transcriber
        mock_model.transcribe.return_value = (iter([]), _make_info(duration=0.001))

        result = await transcriber.transcribe_audio(np.zeros(0, dtype=np.float32))

        assert result["text"] == ""
        assert result["segments"] == []
        assert result["language"] == "en"

    @pytest.mark.asyncio
    async def test_no_segments_returns_empty_text_with_correct_language(
        self, initialized_transcriber
    ):
        """Iterator that yields zero segments produces an empty text field."""
        transcriber, mock_model = initialized_transcriber
        info = _make_info(language="fr", language_probability=0.95, duration=2.0)
        mock_model.transcribe.return_value = (iter([]), info)

        result = await transcriber.transcribe_audio(np.zeros(32000, dtype=np.float32))

        assert result["text"] == ""
        assert result["language"] == "fr"
        assert result["language_probability"] == 0.95

    @pytest.mark.asyncio
    async def test_word_timestamps_path_populates_words(self, initialized_transcriber):
        """Segments that carry word data are forwarded into the result dict."""
        transcriber, mock_model = initialized_transcriber
        w = _make_word(start=0.0, end=0.4, word="test", probability=0.99)
        seg = _make_segment(seg_id=0, text="test", words=[w])
        mock_model.transcribe.return_value = (iter([seg]), _make_info(duration=1.0))

        result = await transcriber.transcribe_audio(
            np.zeros(16000, dtype=np.float32), word_timestamps=True
        )

        assert len(result["segments"]) == 1
        assert "words" in result["segments"][0]
        assert result["segments"][0]["words"][0]["word"] == "test"

    @pytest.mark.asyncio
    async def test_model_exception_raises_whispererror(self, initialized_transcriber):
        """RuntimeError from the model is wrapped in WhisperTranscriptionError."""
        transcriber, mock_model = initialized_transcriber
        mock_model.transcribe.side_effect = RuntimeError("model crashed")

        with pytest.raises(WhisperTranscriptionError, match="Transcription failed"):
            await transcriber.transcribe_audio(np.zeros(16000, dtype=np.float32))

    @pytest.mark.asyncio
    async def test_multiple_segments_text_joined_with_spaces(
        self, initialized_transcriber
    ):
        """Text from multiple segments is joined with a single space."""
        transcriber, mock_model = initialized_transcriber
        segs = [
            _make_segment(seg_id=0, text="Hello"),
            _make_segment(seg_id=1, text="world"),
        ]
        mock_model.transcribe.return_value = (iter(segs), _make_info(duration=2.0))

        result = await transcriber.transcribe_audio(np.zeros(32000, dtype=np.float32))

        assert result["text"] == "Hello world"
        assert len(result["segments"]) == 2


class TestTranscriberDetectLanguage:
    """Tests for detect_language result parsing."""

    @pytest.mark.asyncio
    async def test_returns_parsed_language_tuple(self, initialized_transcriber):
        """detect_language correctly unpacks (language, probability, all_probs)."""
        transcriber, mock_model = initialized_transcriber
        all_probs = [("en", 0.95), ("fr", 0.03), ("de", 0.02)]
        mock_model.detect_language.return_value = ("en", 0.95, all_probs)

        result = await transcriber.detect_language(np.zeros(16000, dtype=np.float32))

        language, probability, probs = result
        assert language == "en"
        assert probability == 0.95
        assert probs == all_probs

    @pytest.mark.asyncio
    async def test_model_exception_raises_whispererror(self, initialized_transcriber):
        """RuntimeError during detection is wrapped in WhisperTranscriptionError."""
        transcriber, mock_model = initialized_transcriber
        mock_model.detect_language.side_effect = RuntimeError("detect failed")

        with pytest.raises(
            WhisperTranscriptionError, match="Language detection failed"
        ):
            await transcriber.detect_language(np.zeros(16000, dtype=np.float32))


class TestTranscriberLifecycle:
    """Tests for initialize, shutdown, get_model_info, and clear_cache."""

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self, transcriber):
        """initialize() calls model_manager.initialize and sets _initialized."""
        transcriber.model_manager.initialize = AsyncMock()
        await transcriber.initialize()
        assert transcriber._initialized
        transcriber.model_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_is_idempotent(self, transcriber):
        """Calling initialize() when already initialized is a no-op."""
        transcriber._initialized = True
        transcriber.model_manager.initialize = AsyncMock()
        await transcriber.initialize()
        transcriber.model_manager.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_shutdown_clears_initialized_flag(self, initialized_transcriber):
        """shutdown() unloads the model and clears _initialized."""
        transcriber, _ = initialized_transcriber
        transcriber.model_manager.unload = AsyncMock()
        await transcriber.shutdown()
        assert not transcriber._initialized
        transcriber.model_manager.unload.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_model_info_when_not_initialized(self, transcriber):
        """get_model_info() reports not-initialized status before initialize()."""
        result = await transcriber.get_model_info()
        assert result == {"status": "not_initialized"}

    @pytest.mark.asyncio
    async def test_clear_cache_delegates_to_model_manager(
        self, initialized_transcriber
    ):
        """clear_cache() forwards the call to model_manager.clear_cache()."""
        transcriber, _ = initialized_transcriber
        transcriber.model_manager.clear_cache = AsyncMock()
        await transcriber.clear_cache()
        transcriber.model_manager.clear_cache.assert_called_once()


class TestTranscriberNumpyPath:
    """Tests for transcribe_numpy preprocessing branches."""

    @pytest.mark.asyncio
    async def test_float32_at_16khz_passes_through(self, initialized_transcriber):
        """float32 audio already normalized at 16 kHz is forwarded without modification."""
        transcriber, mock_model = initialized_transcriber
        mock_model.transcribe.return_value = (iter([]), _make_info(duration=1.0))

        result = await transcriber.transcribe_numpy(
            np.zeros(16000, dtype=np.float32), sample_rate=16000
        )

        assert result["text"] == ""
        mock_model.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_int16_audio_is_converted_to_float32(self, initialized_transcriber):
        """int16 input is cast to float32 before transcription."""
        transcriber, mock_model = initialized_transcriber
        mock_model.transcribe.return_value = (iter([]), _make_info(duration=1.0))

        result = await transcriber.transcribe_numpy(
            np.zeros(16000, dtype=np.int16), sample_rate=16000
        )

        assert result["text"] == ""

    @pytest.mark.asyncio
    async def test_audio_above_one_is_normalized(self, initialized_transcriber):
        """Audio whose max value exceeds 1.0 is rescaled before transcription."""
        transcriber, mock_model = initialized_transcriber
        mock_model.transcribe.return_value = (iter([]), _make_info(duration=1.0))

        result = await transcriber.transcribe_numpy(
            np.full(16000, 2.0, dtype=np.float32), sample_rate=16000
        )

        assert result["text"] == ""

    @pytest.mark.asyncio
    async def test_resampling_from_44khz_to_16khz(self, initialized_transcriber):
        """Audio at 44.1 kHz is resampled down to 16 kHz before transcription."""
        transcriber, mock_model = initialized_transcriber
        mock_model.transcribe.return_value = (iter([]), _make_info(duration=0.5))

        result = await transcriber.transcribe_numpy(
            np.zeros(22050, dtype=np.float32), sample_rate=44100
        )

        assert result["text"] == ""
