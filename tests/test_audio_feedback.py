"""Tests for audio feedback system."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from champi_stt.assistant.audio_feedback import (
    FeedbackTheme,
    generate_chime,
    play_audio_feedback,
    play_chime_end,
    play_chime_start,
    play_chime_wake,
)


class TestFeedbackTheme:
    def test_values(self) -> None:
        assert FeedbackTheme.DEFAULT == "default"
        assert FeedbackTheme.MINIMAL == "minimal"
        assert FeedbackTheme.SILENT == "silent"

    def test_is_str_enum(self) -> None:
        assert isinstance(FeedbackTheme.DEFAULT, str)


class TestGenerateChime:
    def test_basic_output_shape(self) -> None:
        audio = generate_chime([440.0, 880.0], duration=0.1, sample_rate=16000)
        assert audio.dtype == np.float32
        assert len(audio) == 2 * int(16000 * 0.1)

    def test_empty_frequencies_returns_empty(self) -> None:
        audio = generate_chime([], duration=0.1)
        assert len(audio) == 0

    def test_zero_duration_returns_empty(self) -> None:
        audio = generate_chime([440.0], duration=0.0)
        assert len(audio) == 0

    def test_volume_clamps_to_zero(self) -> None:
        audio = generate_chime([440.0], duration=0.1, sample_rate=8000, volume=0.0)
        assert np.allclose(audio, 0.0)

    def test_volume_above_one_clamped(self) -> None:
        normal = generate_chime([440.0], duration=0.05, sample_rate=8000, volume=1.0)
        loud = generate_chime([440.0], duration=0.05, sample_rate=8000, volume=999.0)
        assert np.allclose(normal, loud)

    def test_single_frequency(self) -> None:
        audio = generate_chime([1000.0], duration=0.05, sample_rate=8000)
        assert len(audio) == int(8000 * 0.05)

    def test_amplitude_within_range(self) -> None:
        audio = generate_chime([440.0, 880.0], duration=0.1, sample_rate=16000)
        assert float(np.abs(audio).max()) <= 1.0 + 1e-6


class TestPlayChimes:
    @pytest.fixture(autouse=True)
    def _mock_play(self) -> None:
        with patch("champi_stt.assistant.audio_feedback._play_nonblocking") as m, \
             patch("champi_stt.assistant.audio_feedback._device_sample_rate", return_value=44100):
            self.mock_play = m
            yield

    @pytest.mark.asyncio
    async def test_play_chime_start_default(self) -> None:
        result = await play_chime_start()
        assert result is True
        self.mock_play.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_chime_start_silent(self) -> None:
        result = await play_chime_start(theme=FeedbackTheme.SILENT)
        assert result is True
        self.mock_play.assert_not_called()

    @pytest.mark.asyncio
    async def test_play_chime_end_minimal(self) -> None:
        result = await play_chime_end(theme=FeedbackTheme.MINIMAL)
        assert result is True
        self.mock_play.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_chime_wake_default(self) -> None:
        result = await play_chime_wake()
        assert result is True
        self.mock_play.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_chime_wake_silent(self) -> None:
        result = await play_chime_wake(theme=FeedbackTheme.SILENT)
        assert result is True
        self.mock_play.assert_not_called()


class TestPlayAudioFeedback:
    @pytest.fixture(autouse=True)
    def _mock_internals(self) -> None:
        with patch("champi_stt.assistant.audio_feedback._play_nonblocking"), \
             patch("champi_stt.assistant.audio_feedback._device_sample_rate", return_value=44100):
            yield

    @pytest.mark.asyncio
    async def test_disabled_skips(self) -> None:
        with patch("champi_stt.assistant.audio_feedback.play_chime_start") as m:
            await play_audio_feedback("listening", enabled=False)
            m.assert_not_called()

    @pytest.mark.asyncio
    async def test_listening(self) -> None:
        with patch("champi_stt.assistant.audio_feedback.play_chime_start") as m:
            await play_audio_feedback("listening")
            m.assert_called_once()

    @pytest.mark.asyncio
    async def test_finished(self) -> None:
        with patch("champi_stt.assistant.audio_feedback.play_chime_end") as m:
            await play_audio_feedback("finished")
            m.assert_called_once()

    @pytest.mark.asyncio
    async def test_wake(self) -> None:
        with patch("champi_stt.assistant.audio_feedback.play_chime_wake") as m:
            await play_audio_feedback("wake")
            m.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_type_does_not_raise(self) -> None:
        await play_audio_feedback("unknown_type")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_volume_passed_through(self) -> None:
        with patch("champi_stt.assistant.audio_feedback.play_chime_wake") as m:
            await play_audio_feedback("wake", volume=0.5)
            _, kwargs = m.call_args
            assert kwargs["volume"] == 0.5

    @pytest.mark.asyncio
    async def test_theme_passed_through(self) -> None:
        with patch("champi_stt.assistant.audio_feedback.play_chime_start") as m:
            await play_audio_feedback("listening", theme=FeedbackTheme.MINIMAL)
            _, kwargs = m.call_args
            assert kwargs["theme"] is FeedbackTheme.MINIMAL
