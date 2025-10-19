"""Tests for core audio functionality."""

import numpy as np
import pytest

from champi_stt.core.audio import (
    AudioCapture,
    AudioFormat,
    resample_audio,
    normalize_audio,
)


class TestAudioFormat:
    """Tests for AudioFormat dataclass."""

    def test_audio_format_creation(self):
        """Test creating an AudioFormat instance."""
        fmt = AudioFormat(sample_rate=16000, channels=1, sample_width=2)
        assert fmt.sample_rate == 16000
        assert fmt.channels == 1
        assert fmt.sample_width == 2

    def test_audio_format_default_values(self):
        """Test AudioFormat default values."""
        fmt = AudioFormat()
        assert fmt.sample_rate == 16000
        assert fmt.channels == 1
        assert fmt.sample_width == 2


class TestAudioProcessing:
    """Tests for audio processing functions."""

    def test_normalize_audio(self, sample_audio_data: np.ndarray):
        """Test audio normalization."""
        # Create audio with known range
        audio = np.array([100, 200, 300, 400, 500], dtype=np.int16)
        normalized = normalize_audio(audio)

        # Check output is float32
        assert normalized.dtype == np.float32
        # Check values are in [-1, 1] range
        assert normalized.min() >= -1.0
        assert normalized.max() <= 1.0

    def test_normalize_audio_zeros(self):
        """Test normalization of zero audio."""
        audio = np.zeros(1000, dtype=np.int16)
        normalized = normalize_audio(audio)

        assert normalized.dtype == np.float32
        assert np.all(normalized == 0.0)

    def test_resample_audio_same_rate(self, sample_audio_data: np.ndarray):
        """Test resampling with same rate (should return original)."""
        result = resample_audio(sample_audio_data, 16000, 16000)
        np.testing.assert_array_equal(result, sample_audio_data)

    def test_resample_audio_upsample(self):
        """Test upsampling audio."""
        audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        result = resample_audio(audio, 8000, 16000)

        # Upsampling should increase sample count
        assert len(result) > len(audio)

    def test_resample_audio_downsample(self, sample_audio_data: np.ndarray):
        """Test downsampling audio."""
        result = resample_audio(sample_audio_data, 16000, 8000)

        # Downsampling should decrease sample count
        assert len(result) == len(sample_audio_data) // 2


class TestAudioCapture:
    """Tests for AudioCapture class."""

    def test_audio_capture_init(self):
        """Test AudioCapture initialization."""
        capture = AudioCapture(sample_rate=16000, channels=1, chunk_size=1024)

        assert capture.sample_rate == 16000
        assert capture.channels == 1
        assert capture.chunk_size == 1024
        assert not capture.is_recording

    def test_audio_capture_default_values(self):
        """Test AudioCapture with default values."""
        capture = AudioCapture()

        assert capture.sample_rate == 16000
        assert capture.channels == 1
        assert capture.chunk_size == 1024

    @pytest.mark.asyncio
    async def test_audio_capture_context_manager(self, mocker):
        """Test AudioCapture as async context manager."""
        capture = AudioCapture()

        # Mock the audio stream
        mocker.patch.object(capture, '_open_stream')
        mocker.patch.object(capture, '_close_stream')

        async with capture:
            assert capture.is_recording

        assert not capture.is_recording

    def test_audio_format_property(self):
        """Test getting audio format from capture."""
        capture = AudioCapture(sample_rate=48000, channels=2)
        fmt = capture.format

        assert isinstance(fmt, AudioFormat)
        assert fmt.sample_rate == 48000
        assert fmt.channels == 2
