"""
Tests for WhisperLive transcriber module.

Covers error-handling branches, edge cases, and Phase-1 path-fix regression
tests to prevent the hardcoded-path bugs fixed in issue #49 from reappearing.
"""

import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from champi_stt.providers.whisperlive.config import WhisperLiveConfig
from champi_stt.providers.whisperlive.exceptions import (
    WhisperAudioError,
    WhisperTranscriptionError,
)
from champi_stt.providers.whisperlive.transcriber import WhisperLiveTranscriber

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_segment(
    text: str = "hello",
    start: float = 0.0,
    end: float = 1.0,
    *,
    with_words: bool = False,
) -> MagicMock:
    """Build a minimal mock segment as returned by faster-whisper."""
    seg = MagicMock()
    seg.id = 1
    seg.start = start
    seg.end = end
    seg.text = text
    seg.avg_logprob = -0.3
    seg.no_speech_prob = 0.05
    seg.compression_ratio = 1.2
    seg.temperature = 0.0
    seg.tokens = [1, 2, 3]
    if with_words:
        word = MagicMock()
        word.start = start
        word.end = end
        word.word = text
        word.probability = 0.95
        seg.words = [word]
    else:
        seg.words = None
    return seg


def _make_mock_info(
    language: str = "en",
    language_probability: float = 0.95,
    duration: float = 1.5,
) -> MagicMock:
    """Build a minimal mock transcription info object."""
    info = MagicMock()
    info.language = language
    info.language_probability = language_probability
    info.duration = duration
    info.duration_after_vad = duration - 0.1
    return info


def _make_mock_model(
    text: str = "hello",
    language: str = "en",
    lang_prob: float = 0.95,
    duration: float = 1.5,
) -> MagicMock:
    """Build a WhisperModel mock that returns deterministic transcription results."""
    mock_model = MagicMock()
    seg = _make_mock_segment(text=text)
    info = _make_mock_info(language=language, language_probability=lang_prob, duration=duration)
    mock_model.transcribe.return_value = ([seg], info)
    mock_model.detect_language.return_value = (language, lang_prob, [(language, lang_prob)])
    return mock_model


def _make_transcriber(
    tmp_path: Path,
    *,
    initialized: bool = False,
    model: MagicMock | None = None,
) -> WhisperLiveTranscriber:
    """Construct a WhisperLiveTranscriber with isolated cache directory."""
    config = WhisperLiveConfig(cache_dir=str(tmp_path / "cache"))
    transcriber = WhisperLiveTranscriber(config)
    if model is not None:
        transcriber.model_manager._model = model
    if initialized:
        transcriber._initialized = True
    return transcriber


def _mock_result() -> dict:
    return {
        "text": "hello",
        "language": "en",
        "segments": [],
        "duration": 1.0,
        "duration_after_vad": 0.9,
        "language_probability": 0.95,
        "processing_time": 0.05,
    }


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestWhisperLiveTranscriberInit:
    """Tests for WhisperLiveTranscriber construction."""

    def test_init_stores_provided_config(self, tmp_path: Path) -> None:
        config = WhisperLiveConfig(cache_dir=str(tmp_path / "cache"))
        transcriber = WhisperLiveTranscriber(config)
        assert transcriber.config is config

    def test_init_not_initialized_by_default(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        assert transcriber._initialized is False

    def test_model_property_returns_none_before_loading(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        assert transcriber.model is None

    def test_is_loaded_false_before_model_set(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        assert transcriber.is_loaded is False

    def test_is_loaded_true_after_mock_model_set(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path, model=_make_mock_model())
        assert transcriber.is_loaded is True

    def test_model_property_returns_mock_model(self, tmp_path: Path) -> None:
        mock_model = _make_mock_model()
        transcriber = _make_transcriber(tmp_path, model=mock_model)
        assert transcriber.model is mock_model


# ---------------------------------------------------------------------------
# initialize()
# ---------------------------------------------------------------------------


class TestWhisperLiveTranscriberInitialize:
    """Tests for WhisperLiveTranscriber.initialize()."""

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        transcriber.model_manager.initialize = AsyncMock()
        await transcriber.initialize()
        assert transcriber._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_calls_model_manager_initialize(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        mock_init = AsyncMock()
        transcriber.model_manager.initialize = mock_init
        await transcriber.initialize()
        mock_init.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_initialize_is_idempotent(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        mock_init = AsyncMock()
        transcriber.model_manager.initialize = mock_init
        await transcriber.initialize()
        await transcriber.initialize()
        mock_init.assert_awaited_once()


# ---------------------------------------------------------------------------
# _process_segments()
# ---------------------------------------------------------------------------


class TestProcessSegments:
    """Tests for WhisperLiveTranscriber._process_segments()."""

    def test_empty_input_returns_empty_list(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        assert transcriber._process_segments([]) == []

    def test_single_segment_without_words(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        seg = _make_mock_segment(text="hello world", start=0.0, end=1.5, with_words=False)
        result = transcriber._process_segments([seg])

        assert len(result) == 1
        assert result[0]["text"] == "hello world"
        assert result[0]["start"] == pytest.approx(0.0)
        assert result[0]["end"] == pytest.approx(1.5)
        assert "words" not in result[0]

    def test_single_segment_with_words(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        seg = _make_mock_segment(text="hi", start=0.0, end=0.5, with_words=True)
        result = transcriber._process_segments([seg])

        assert "words" in result[0]
        assert len(result[0]["words"]) == 1
        assert result[0]["words"][0]["probability"] == pytest.approx(0.95)

    def test_multiple_segments_preserved_in_order(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        segs = [
            _make_mock_segment(text="hello", start=0.0, end=0.5),
            _make_mock_segment(text="world", start=0.5, end=1.0),
        ]
        result = transcriber._process_segments(segs)

        assert len(result) == 2
        assert result[0]["text"] == "hello"
        assert result[1]["text"] == "world"

    def test_segment_result_contains_all_expected_keys(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        seg = _make_mock_segment()
        result = transcriber._process_segments([seg])

        expected_keys = {
            "id", "start", "end", "text",
            "avg_logprob", "no_speech_prob", "compression_ratio",
            "temperature", "tokens",
        }
        assert expected_keys.issubset(result[0].keys())


# ---------------------------------------------------------------------------
# transcribe_audio()
# ---------------------------------------------------------------------------


class TestTranscribeAudio:
    """Tests for WhisperLiveTranscriber.transcribe_audio()."""

    @pytest.mark.asyncio
    async def test_returns_expected_top_level_keys(self, tmp_path: Path) -> None:
        mock_model = _make_mock_model(text="hello world", language="en", duration=1.5)
        transcriber = _make_transcriber(tmp_path, initialized=True, model=mock_model)
        audio = np.zeros(16000, dtype=np.float32)

        result = await transcriber.transcribe_audio(audio)

        for key in ("text", "language", "segments", "duration", "processing_time"):
            assert key in result

    @pytest.mark.asyncio
    async def test_text_joined_from_segment_text(self, tmp_path: Path) -> None:
        mock_model = _make_mock_model(text="hello world")
        transcriber = _make_transcriber(tmp_path, initialized=True, model=mock_model)

        result = await transcriber.transcribe_audio(np.zeros(16000, dtype=np.float32))
        assert "hello world" in result["text"]

    @pytest.mark.asyncio
    async def test_language_field_matches_model_output(self, tmp_path: Path) -> None:
        mock_model = _make_mock_model(language="fr")
        transcriber = _make_transcriber(tmp_path, initialized=True, model=mock_model)

        result = await transcriber.transcribe_audio(np.zeros(16000, dtype=np.float32))
        assert result["language"] == "fr"

    @pytest.mark.asyncio
    async def test_duration_matches_info_duration(self, tmp_path: Path) -> None:
        mock_model = _make_mock_model(duration=2.5)
        transcriber = _make_transcriber(tmp_path, initialized=True, model=mock_model)

        result = await transcriber.transcribe_audio(np.zeros(16000, dtype=np.float32))
        assert result["duration"] == pytest.approx(2.5)

    @pytest.mark.asyncio
    async def test_language_probability_is_in_valid_range(self, tmp_path: Path) -> None:
        mock_model = _make_mock_model(lang_prob=0.87)
        transcriber = _make_transcriber(tmp_path, initialized=True, model=mock_model)

        result = await transcriber.transcribe_audio(np.zeros(16000, dtype=np.float32))
        assert 0.0 <= result["language_probability"] <= 1.0

    @pytest.mark.asyncio
    async def test_raises_whisper_transcription_error_on_model_failure(
        self, tmp_path: Path
    ) -> None:
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("model failure")
        transcriber = _make_transcriber(tmp_path, initialized=True, model=mock_model)

        with pytest.raises(WhisperTranscriptionError):
            await transcriber.transcribe_audio(np.zeros(16000, dtype=np.float32))

    @pytest.mark.asyncio
    async def test_processing_time_is_nonnegative(self, tmp_path: Path) -> None:
        mock_model = _make_mock_model()
        transcriber = _make_transcriber(tmp_path, initialized=True, model=mock_model)

        result = await transcriber.transcribe_audio(np.zeros(16000, dtype=np.float32))
        assert result["processing_time"] >= 0.0

    @pytest.mark.asyncio
    async def test_accepts_bytesio_audio(self, tmp_path: Path) -> None:
        mock_model = _make_mock_model()
        transcriber = _make_transcriber(tmp_path, initialized=True, model=mock_model)

        audio = io.BytesIO(b"\x00" * 32000)
        result = await transcriber.transcribe_audio(audio)
        assert "text" in result


# ---------------------------------------------------------------------------
# transcribe_numpy()
# ---------------------------------------------------------------------------


class TestTranscribeNumpy:
    """Tests for WhisperLiveTranscriber.transcribe_numpy()."""

    @pytest.mark.asyncio
    async def test_float32_at_16khz_passes_through_unchanged(
        self, tmp_path: Path, mocker
    ) -> None:
        transcriber = _make_transcriber(tmp_path, initialized=True)
        captured: dict = {}

        async def capture(audio, **kwargs):
            captured["dtype"] = audio.dtype
            return _mock_result()

        mocker.patch.object(transcriber, "transcribe_audio", new=capture)
        audio_data = np.zeros(16000, dtype=np.float32)
        await transcriber.transcribe_numpy(audio_data, sample_rate=16000)

        assert captured["dtype"] == np.float32

    @pytest.mark.asyncio
    async def test_int16_audio_is_converted_to_float32(
        self, tmp_path: Path, mocker
    ) -> None:
        transcriber = _make_transcriber(tmp_path, initialized=True)
        captured: dict = {}

        async def capture(audio, **kwargs):
            captured["dtype"] = audio.dtype
            return _mock_result()

        mocker.patch.object(transcriber, "transcribe_audio", new=capture)
        audio_data = np.zeros(16000, dtype=np.int16)
        await transcriber.transcribe_numpy(audio_data, sample_rate=16000)

        assert captured["dtype"] == np.float32

    @pytest.mark.asyncio
    async def test_amplitude_above_1_is_normalised(
        self, tmp_path: Path, mocker
    ) -> None:
        transcriber = _make_transcriber(tmp_path, initialized=True)
        captured: dict = {}

        async def capture(audio, **kwargs):
            captured["max"] = float(np.max(np.abs(audio)))
            return _mock_result()

        mocker.patch.object(transcriber, "transcribe_audio", new=capture)
        audio_data = np.ones(16000, dtype=np.float32) * 3.0
        await transcriber.transcribe_numpy(audio_data, sample_rate=16000)

        assert captured["max"] <= 1.0

    @pytest.mark.asyncio
    async def test_non_16khz_audio_is_resampled(
        self, tmp_path: Path, mocker
    ) -> None:
        transcriber = _make_transcriber(tmp_path, initialized=True)
        mock_transcribe = AsyncMock(return_value=_mock_result())
        mocker.patch.object(transcriber, "transcribe_audio", new=mock_transcribe)

        # 1 second at 44 100 Hz → should be resampled to 16 000 samples
        audio_data = np.zeros(44100, dtype=np.float32)
        await transcriber.transcribe_numpy(audio_data, sample_rate=44100)

        passed_audio = mock_transcribe.call_args[0][0]
        assert len(passed_audio) == pytest.approx(16000, rel=0.05)


# ---------------------------------------------------------------------------
# detect_language()
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    """Tests for WhisperLiveTranscriber.detect_language()."""

    @pytest.mark.asyncio
    async def test_auto_initializes_when_not_ready(
        self, tmp_path: Path, mocker
    ) -> None:
        mock_model = _make_mock_model(language="de", lang_prob=0.80)
        transcriber = _make_transcriber(tmp_path, model=mock_model)

        async def fake_init():
            transcriber._initialized = True

        mock_init = AsyncMock(side_effect=fake_init)
        mocker.patch.object(transcriber, "initialize", new=mock_init)

        await transcriber.detect_language(np.zeros(16000, dtype=np.float32))
        mock_init.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_language_probability_and_probs_list(
        self, tmp_path: Path
    ) -> None:
        mock_model = _make_mock_model(language="fr", lang_prob=0.88)
        transcriber = _make_transcriber(tmp_path, initialized=True, model=mock_model)

        language, prob, all_probs = await transcriber.detect_language(
            np.zeros(16000, dtype=np.float32)
        )

        assert language == "fr"
        assert prob == pytest.approx(0.88)
        assert isinstance(all_probs, list)

    @pytest.mark.asyncio
    async def test_raises_whisper_transcription_error_on_failure(
        self, tmp_path: Path
    ) -> None:
        mock_model = MagicMock()
        mock_model.detect_language.side_effect = RuntimeError("detection failed")
        transcriber = _make_transcriber(tmp_path, initialized=True, model=mock_model)

        with pytest.raises(WhisperTranscriptionError):
            await transcriber.detect_language(np.zeros(16000, dtype=np.float32))


# ---------------------------------------------------------------------------
# get_model_info()
# ---------------------------------------------------------------------------


class TestGetModelInfo:
    """Tests for WhisperLiveTranscriber.get_model_info()."""

    @pytest.mark.asyncio
    async def test_returns_not_initialized_status_before_init(
        self, tmp_path: Path
    ) -> None:
        transcriber = _make_transcriber(tmp_path)
        info = await transcriber.get_model_info()
        assert info == {"status": "not_initialized"}

    @pytest.mark.asyncio
    async def test_delegates_to_model_manager_after_init(
        self, tmp_path: Path
    ) -> None:
        transcriber = _make_transcriber(tmp_path, initialized=True)
        expected = {"status": "loaded", "model_size": "base"}
        transcriber.model_manager.get_model_info = AsyncMock(return_value=expected)

        result = await transcriber.get_model_info()

        assert result == expected
        transcriber.model_manager.get_model_info.assert_awaited_once()


# ---------------------------------------------------------------------------
# clear_cache()
# ---------------------------------------------------------------------------


class TestClearCache:
    """Tests for WhisperLiveTranscriber.clear_cache()."""

    @pytest.mark.asyncio
    async def test_delegates_to_model_manager_clear_cache(
        self, tmp_path: Path
    ) -> None:
        transcriber = _make_transcriber(tmp_path)
        transcriber.model_manager.clear_cache = AsyncMock()
        await transcriber.clear_cache()
        transcriber.model_manager.clear_cache.assert_awaited_once()


# ---------------------------------------------------------------------------
# save_transcription()
# ---------------------------------------------------------------------------


class TestSaveTranscription:
    """Tests for WhisperLiveTranscriber.save_transcription()."""

    @pytest.mark.asyncio
    async def test_returns_none_when_saving_disabled(self, tmp_path: Path) -> None:
        config = WhisperLiveConfig(
            save_transcriptions=False,
            cache_dir=str(tmp_path / "cache"),
        )
        transcriber = WhisperLiveTranscriber(config)
        result = await transcriber.save_transcription("hello world")
        assert result is None

    @pytest.mark.asyncio
    async def test_creates_file_with_transcription_text(self, tmp_path: Path) -> None:
        trans_dir = tmp_path / "transcriptions"
        config = WhisperLiveConfig(
            save_transcriptions=True,
            transcriptions_dir=str(trans_dir),
            cache_dir=str(tmp_path / "cache"),
        )
        transcriber = WhisperLiveTranscriber(config)

        result = await transcriber.save_transcription("hello world")

        assert result is not None
        saved = Path(result)
        assert saved.exists()
        assert "hello world" in saved.read_text()

    @pytest.mark.asyncio
    async def test_returned_filename_starts_with_custom_prefix(
        self, tmp_path: Path
    ) -> None:
        trans_dir = tmp_path / "transcriptions"
        config = WhisperLiveConfig(
            save_transcriptions=True,
            transcriptions_dir=str(trans_dir),
            cache_dir=str(tmp_path / "cache"),
        )
        transcriber = WhisperLiveTranscriber(config)

        result = await transcriber.save_transcription("hello", prefix="mytest")

        assert result is not None
        assert Path(result).name.startswith("mytest_")

    @pytest.mark.asyncio
    async def test_metadata_header_written_when_provided(self, tmp_path: Path) -> None:
        trans_dir = tmp_path / "transcriptions"
        config = WhisperLiveConfig(
            save_transcriptions=True,
            transcriptions_dir=str(trans_dir),
            cache_dir=str(tmp_path / "cache"),
        )
        transcriber = WhisperLiveTranscriber(config)

        result = await transcriber.save_transcription(
            "test text",
            metadata={"language": "en", "model": "base"},
        )

        assert result is not None
        content = Path(result).read_text()
        assert "TRANSCRIPTION METADATA" in content
        assert "language" in content
        assert "model" in content

    @pytest.mark.asyncio
    async def test_raises_whisper_audio_error_on_write_failure(
        self, tmp_path: Path, mocker
    ) -> None:
        trans_dir = tmp_path / "transcriptions"
        config = WhisperLiveConfig(
            save_transcriptions=True,
            transcriptions_dir=str(trans_dir),
            cache_dir=str(tmp_path / "cache"),
        )
        transcriber = WhisperLiveTranscriber(config)

        mocker.patch("pathlib.Path.write_text", side_effect=OSError("disk full"))

        with pytest.raises(WhisperAudioError):
            await transcriber.save_transcription("hello")


# ---------------------------------------------------------------------------
# shutdown()
# ---------------------------------------------------------------------------


class TestShutdown:
    """Tests for WhisperLiveTranscriber.shutdown()."""

    @pytest.mark.asyncio
    async def test_clears_initialized_flag(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path, initialized=True)
        transcriber.model_manager.unload = AsyncMock()
        await transcriber.shutdown()
        assert transcriber._initialized is False

    @pytest.mark.asyncio
    async def test_calls_model_manager_unload(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path, initialized=True)
        mock_unload = AsyncMock()
        transcriber.model_manager.unload = mock_unload
        await transcriber.shutdown()
        mock_unload.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_safe_when_not_initialized(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        transcriber.model_manager.unload = AsyncMock()
        await transcriber.shutdown()
        assert transcriber._initialized is False


# ---------------------------------------------------------------------------
# _load_audio_data()
# ---------------------------------------------------------------------------


class TestLoadAudioData:
    """Tests for WhisperLiveTranscriber._load_audio_data()."""

    @pytest.mark.asyncio
    async def test_numpy_array_returned_unchanged(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        audio = np.zeros(16000, dtype=np.float32)
        result = await transcriber._load_audio_data(audio, 16000)
        assert result is audio

    @pytest.mark.asyncio
    async def test_unknown_type_returns_none(self, tmp_path: Path) -> None:
        transcriber = _make_transcriber(tmp_path)
        result = await transcriber._load_audio_data(42, 16000)
        assert result is None


# ---------------------------------------------------------------------------
# play_audio() and _play_audio_data()
# ---------------------------------------------------------------------------


class TestPlayAudio:
    """Tests for WhisperLiveTranscriber.play_audio()."""

    @pytest.mark.asyncio
    async def test_raises_whisper_audio_error_when_load_returns_none(
        self, tmp_path: Path, mocker
    ) -> None:
        transcriber = _make_transcriber(tmp_path)
        mocker.patch.object(
            transcriber, "_load_audio_data", new=AsyncMock(return_value=None)
        )

        with pytest.raises(WhisperAudioError):
            await transcriber.play_audio(np.zeros(16000, dtype=np.float32))

    @pytest.mark.asyncio
    async def test_raises_whisper_audio_error_when_load_raises(
        self, tmp_path: Path, mocker
    ) -> None:
        transcriber = _make_transcriber(tmp_path)
        mocker.patch.object(
            transcriber,
            "_load_audio_data",
            new=AsyncMock(side_effect=OSError("file not found")),
        )

        with pytest.raises(WhisperAudioError):
            await transcriber.play_audio("nonexistent_file.wav")


class TestPlayAudioData:
    """Tests for WhisperLiveTranscriber._play_audio_data()."""

    @pytest.mark.asyncio
    async def test_raises_whisper_audio_error_when_sounddevice_unavailable(
        self, tmp_path: Path, mocker
    ) -> None:
        transcriber = _make_transcriber(tmp_path)
        mocker.patch(
            "champi_stt.providers.whisperlive.transcriber.sd", None
        )

        audio_data = np.zeros(100, dtype=np.float32)
        with pytest.raises(WhisperAudioError):
            await transcriber._play_audio_data(audio_data, 16000)


# ---------------------------------------------------------------------------
# Phase-1 path-fix regression tests (issue #49)
# ---------------------------------------------------------------------------


class TestPhase1PathRegressions:
    """
    Regression tests for the hardcoded-path bugs fixed in issue #49.

    These tests ensure that default config paths remain correctly set to
    champi-stt namespaced directories, and that no legacy identifiers
    (mcp-champi, mcp_champi, /mnt/raid_0_drive) creep back into source.
    """

    # --- WhisperLiveConfig defaults -----------------------------------------

    def test_whisperlive_config_cache_dir_contains_champi_stt(self) -> None:
        config = WhisperLiveConfig()
        assert "champi-stt" in config.cache_dir

    def test_whisperlive_config_cache_dir_not_mcp_champi(self) -> None:
        config = WhisperLiveConfig()
        assert "mcp-champi" not in config.cache_dir
        assert "mcp_champi" not in config.cache_dir

    def test_whisperlive_config_cache_dir_not_raid_path(self) -> None:
        config = WhisperLiveConfig()
        assert "/mnt/raid_0_drive" not in config.cache_dir

    def test_whisperlive_config_transcriptions_dir_contains_champi_stt(self) -> None:
        config = WhisperLiveConfig()
        assert "champi-stt" in config.transcriptions_dir

    def test_whisperlive_config_transcriptions_dir_not_mcp_champi(self) -> None:
        config = WhisperLiveConfig()
        assert "mcp-champi" not in config.transcriptions_dir
        assert "mcp_champi" not in config.transcriptions_dir

    def test_whisperlive_config_transcriptions_dir_not_raid_path(self) -> None:
        config = WhisperLiveConfig()
        assert "/mnt/raid_0_drive" not in config.transcriptions_dir

    # --- BaseSTTConfig defaults ---------------------------------------------

    def test_base_config_cache_dir_default_contains_champi_stt(self) -> None:
        from champi_stt.core.base_config import BaseSTTConfig

        default = BaseSTTConfig.__dataclass_fields__["cache_dir"].default
        assert "champi-stt" in default

    def test_base_config_cache_dir_default_not_mcp_champi(self) -> None:
        from champi_stt.core.base_config import BaseSTTConfig

        default = BaseSTTConfig.__dataclass_fields__["cache_dir"].default
        assert "mcp-champi" not in default
        assert "mcp_champi" not in default

    def test_base_config_cache_dir_default_not_raid_path(self) -> None:
        from champi_stt.core.base_config import BaseSTTConfig

        default = BaseSTTConfig.__dataclass_fields__["cache_dir"].default
        assert "/mnt/raid_0_drive" not in default

    def test_base_config_transcriptions_dir_default_contains_champi_stt(self) -> None:
        from champi_stt.core.base_config import BaseSTTConfig

        default = BaseSTTConfig.__dataclass_fields__["transcriptions_dir"].default
        assert "champi-stt" in default

    # --- Source code scan ---------------------------------------------------

    def test_no_source_file_contains_mcp_champi_identifier(self) -> None:
        """No .py file under src/champi_stt may contain legacy mcp-champi strings."""
        src_root = Path(__file__).parent.parent / "src" / "champi_stt"
        banned = ["mcp-champi", "mcp_champi"]
        violations: list[str] = []
        for py_file in src_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for token in banned:
                if token in text:
                    violations.append(f"{py_file.relative_to(src_root.parent.parent)}: '{token}'")
        assert not violations, "Legacy path identifiers found:\n" + "\n".join(violations)

    def test_no_source_file_contains_raid_path(self) -> None:
        """No .py file under src/champi_stt may reference /mnt/raid_0_drive."""
        src_root = Path(__file__).parent.parent / "src" / "champi_stt"
        violations: list[str] = []
        for py_file in src_root.rglob("*.py"):
            if "/mnt/raid_0_drive" in py_file.read_text(encoding="utf-8"):
                violations.append(str(py_file.relative_to(src_root.parent.parent)))
        assert not violations, "Legacy raid path found in:\n" + "\n".join(violations)
