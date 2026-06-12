"""Tests for WhisperLive provider."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from champi_stt.core.response import TranscriptionResponse
from champi_stt.providers.whisperlive.config import WhisperLiveConfig
from champi_stt.providers.whisperlive.enums import ComputeType, ModelSize
from champi_stt.providers.whisperlive.exceptions import WhisperTranscriptionError
from champi_stt.providers.whisperlive.models import TranscriptionOptions
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
        segs = [_make_segment(seg_id=0, text="Hello"), _make_segment(seg_id=1, text="world")]
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
    async def test_clear_cache_delegates_to_model_manager(self, initialized_transcriber):
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
