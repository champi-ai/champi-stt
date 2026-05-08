"""Tests for VoskWakeWord engine."""

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from champi_stt.assistant.wakeword.base import WakeWordConfig


def _make_config(**kwargs):
    defaults = {
        "keywords": ["hey champi", "stop"],
        "model_path": "/fake/model/path",
        "sample_rate": 16000,
    }
    defaults.update(kwargs)
    return WakeWordConfig(**defaults)


@pytest.fixture
def mock_vosk():
    mock_model = MagicMock()
    mock_recognizer = MagicMock()

    with patch("champi_stt.assistant.wakeword.vosk.VOSK_AVAILABLE", True):
        with patch("champi_stt.assistant.wakeword.vosk.Model", return_value=mock_model):
            with patch(
                "champi_stt.assistant.wakeword.vosk.KaldiRecognizer",
                return_value=mock_recognizer,
            ):
                yield mock_model, mock_recognizer


class TestVoskWakeWordInit:
    def test_raises_without_vosk(self):
        with patch("champi_stt.assistant.wakeword.vosk.VOSK_AVAILABLE", False):
            from champi_stt.assistant.wakeword.vosk import VoskWakeWord
            with pytest.raises(ImportError, match="vosk"):
                VoskWakeWord(_make_config())

    def test_not_initialized_by_default(self, mock_vosk):
        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        assert not engine.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_vosk):
        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        await engine.initialize()
        assert engine.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_requires_model_path(self, mock_vosk):
        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        config = _make_config(model_path=None)
        engine = VoskWakeWord(config)
        with pytest.raises(ValueError, match="model_path"):
            await engine.initialize()

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, mock_vosk):
        _, mock_recognizer = mock_vosk
        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        await engine.initialize()
        await engine.initialize()
        # Model should only be created once
        assert engine.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_failure_raises(self):
        with patch("champi_stt.assistant.wakeword.vosk.VOSK_AVAILABLE", True):
            with patch(
                "champi_stt.assistant.wakeword.vosk.Model",
                side_effect=Exception("model not found"),
            ):
                from champi_stt.assistant.wakeword.vosk import VoskWakeWord
                engine = VoskWakeWord(_make_config())
                with pytest.raises(RuntimeError, match="Vosk initialization failed"):
                    await engine.initialize()


class TestVoskProcessAudio:
    @pytest.mark.asyncio
    async def test_detect_keyword_in_final_result(self, mock_vosk):
        _, mock_recognizer = mock_vosk
        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = json.dumps({"text": "hey champi"})

        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        await engine.initialize()

        audio = np.zeros(512, dtype=np.int16)
        detected, keyword = await engine.process_audio(audio)
        assert detected is True
        assert keyword == "hey champi"

    @pytest.mark.asyncio
    async def test_detect_keyword_in_partial_result(self, mock_vosk):
        _, mock_recognizer = mock_vosk
        mock_recognizer.AcceptWaveform.return_value = False
        mock_recognizer.PartialResult.return_value = json.dumps({"partial": "stop now"})

        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        await engine.initialize()

        audio = np.zeros(512, dtype=np.int16)
        detected, keyword = await engine.process_audio(audio)
        assert detected is True
        assert keyword == "stop"

    @pytest.mark.asyncio
    async def test_no_match_returns_false(self, mock_vosk):
        _, mock_recognizer = mock_vosk
        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = json.dumps({"text": "random other words"})

        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        await engine.initialize()

        audio = np.zeros(512, dtype=np.int16)
        detected, keyword = await engine.process_audio(audio)
        assert detected is False
        assert keyword is None

    @pytest.mark.asyncio
    async def test_empty_text_returns_false(self, mock_vosk):
        _, mock_recognizer = mock_vosk
        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = json.dumps({"text": ""})

        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        await engine.initialize()

        audio = np.zeros(512, dtype=np.int16)
        detected, _ = await engine.process_audio(audio)
        assert detected is False

    @pytest.mark.asyncio
    async def test_unk_returns_false(self, mock_vosk):
        _, mock_recognizer = mock_vosk
        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = json.dumps({"text": "[unk]"})

        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        await engine.initialize()

        audio = np.zeros(512, dtype=np.int16)
        detected, _ = await engine.process_audio(audio)
        assert detected is False

    @pytest.mark.asyncio
    async def test_not_initialized_raises(self, mock_vosk):
        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        with pytest.raises(RuntimeError, match="not initialized"):
            await engine.process_audio(np.zeros(512, dtype=np.int16))

    @pytest.mark.asyncio
    async def test_float32_audio_accepted(self, mock_vosk):
        _, mock_recognizer = mock_vosk
        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = json.dumps({"text": "hey champi"})

        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        await engine.initialize()

        audio = np.zeros(512, dtype=np.float32)
        detected, keyword = await engine.process_audio(audio)
        assert detected is True


class TestVoskShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_clears_state(self, mock_vosk):
        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        engine = VoskWakeWord(_make_config())
        await engine.initialize()
        assert engine.is_initialized
        await engine.shutdown()
        assert not engine.is_initialized
        assert engine._recognizer is None
        assert engine._model is None


class TestToInt16Bytes:
    def test_int16_passthrough(self):
        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        audio = np.array([100, -100, 0], dtype=np.int16)
        result = VoskWakeWord._to_int16_bytes(audio)
        assert isinstance(result, bytes)
        assert len(result) == 6  # 3 samples * 2 bytes

    def test_float32_conversion(self):
        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        audio = np.array([0.5, -0.5], dtype=np.float32)
        result = VoskWakeWord._to_int16_bytes(audio)
        assert isinstance(result, bytes)
        assert len(result) == 4  # 2 samples * 2 bytes

    def test_other_dtype_conversion(self):
        from champi_stt.assistant.wakeword.vosk import VoskWakeWord
        audio = np.array([100, 200], dtype=np.int32)
        result = VoskWakeWord._to_int16_bytes(audio)
        assert isinstance(result, bytes)
