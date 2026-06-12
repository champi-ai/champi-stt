"""Tests for WhisperLive provider."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from champi_stt.core.response import TranscriptionResponse
from champi_stt.providers.whisperlive.config import WhisperLiveConfig, WhisperPresets
from champi_stt.providers.whisperlive.enums import ComputeType, ModelSize
from champi_stt.providers.whisperlive.exceptions import WhisperInitializationError
from champi_stt.providers.whisperlive.models import (
    ModelCacheManager,
    TranscriptionOptions,
)
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
        config = WhisperLiveConfig(
            model_size="tiny", device="cpu", compute_type="int8"
        )
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
